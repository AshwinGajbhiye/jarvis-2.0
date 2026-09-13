import os
import sys
import threading
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTextEdit, QLineEdit, QPushButton, QLabel, QFrame,
    QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon, QTextCursor, QPixmap, QPainter, QBrush, QPen, QAction

from gui.floating_reactor import FloatingReactorWindow
from gui.floating_launcher import FloatingLauncherWindow
from gui.stealth_hud import StealthHUDWindow
from utils.hotkey_manager import HotkeyManager
from utils.autostart import is_autostart_enabled, toggle_autostart, enable_autostart, disable_autostart
from skills.meeting_recorder import get_meeting_recorder
from skills.meeting_analyzer import analyze_meeting_audio
from skills.stealth_copilot import StealthQuestionWorker
from utils.screen_snipper import ScreenSnipperWorker

from config import Config
from brain import Brain
from voice.tts import speak, stop_speaking
from voice.stt import listen, is_mic_available
from voice.wakeword import WakeWordDetector
from utils.helpers import get_greeting
from skills.leetcode_tracker import sync_daily_dsa_task, sync_neetcode_tasks

# ── Custom Signals for Thread Safety ──────────────────────────
class WorkerSignals(QObject):
    update_chat = pyqtSignal(str, str, str)  # role (User/Jarvis), text, color
    update_status = pyqtSignal(str, str)     # status text, color
    update_quota = pyqtSignal(str)           # quota text
    update_avatar = pyqtSignal(str)          # avatar animation state
    update_tasks = pyqtSignal()              # refresh the task panel
    ready_for_input = pyqtSignal()
    shutdown_app = pyqtSignal()
    show_reactor = pyqtSignal()
    hide_reactor = pyqtSignal()
    launcher_response = pyqtSignal(str)      # send response to floating launcher
    toggle_launcher = pyqtSignal()           # hotkey trigger to toggle launcher
    toggle_stealth = pyqtSignal()            # trigger stealth HUD
    trigger_stealth_answer = pyqtSignal()    # trigger stealth answer
    trigger_stealth_snip = pyqtSignal()      # trigger screen snippet OCR

# ── Worker Thread for Jarvis Logic ────────────────────────────
class JarvisWorker(QThread):
    def __init__(self, brain, signals):
        super().__init__()
        self.brain = brain
        self.brain.signals = signals
        self.signals = signals
        self.mic_available = is_mic_available()
        self.brain_ok = False
        self.silent_mode = False  # If True, text-only (no blocking TTS audio)
        
        # We use a queue to pass manual text input from the GUI to the worker thread
        import queue
        self.input_queue = queue.Queue()
        
        # Setup Wake Word Detector
        self.wakeword = WakeWordDetector(self.on_wakeword_detected)
        self.wakeword_triggered = False
        
        import time
        self.last_nudge_time = time.time()

    def on_wakeword_detected(self):
        """Callback when 'Hey Jarvis' is heard."""
        self.wakeword_triggered = True

    def run(self):
        """Main event loop running in the background thread."""
        self.signals.update_status.emit("Booting...", "#00FFFF")
        self.signals.update_avatar.emit("booting")
        
        # Initialize Brain
        if Config.GEMINI_API_KEY:
            self.signals.update_status.emit("Connecting to Brain...", "#00FFFF")
            self.brain_ok = self.brain.initialize()
            
        if self.brain_ok:
            self.signals.update_status.emit("Online", "#00FF00")
            self.signals.update_quota.emit(self.brain.get_quota_string())
            
            import datetime
            import os
            
            login_file = os.path.join(Config.HISTORY_DIR, "last_login.txt")
            os.makedirs(Config.HISTORY_DIR, exist_ok=True)
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            
            is_first_run = False
            if os.path.exists(login_file):
                with open(login_file, "r") as f:
                    last_login = f.read().strip()
                    if last_login != today:
                        is_first_run = True
            else:
                is_first_run = True
                
            with open(login_file, "w") as f:
                f.write(today)
                
            if is_first_run:
                greeting = f"{get_greeting()}, {Config.USER_NAME}. I noticed it's our first session today. Would you like a summary of the important emails from your personal and college accounts?"
            else:
                greeting = f"{get_greeting()}, {Config.USER_NAME}. I am {Config.JARVIS_NAME}. How may I help you?"
                
            self.signals.update_chat.emit(Config.JARVIS_NAME, greeting, "#00FFFF")
            self.signals.update_avatar.emit("speaking")
            if not self.silent_mode:
                speak(greeting, block=True)
            self.signals.update_avatar.emit("idle")
            
            # Seed the brain's memory with the greeting so it understands context if the user says "yes"
            self.brain.memory.add("model", greeting)
        else:
            self.signals.update_status.emit("Brain Offline", "#FF0000")
            self.signals.update_avatar.emit("error")
            self.signals.update_chat.emit("System", "Warning: GEMINI_API_KEY not set. Cannot connect to brain.", "#FF0000")

        # Start wake word engine
        if self.mic_available:
            self.wakeword.start()

        # Sync LeetCode daily and NeetCode roadmap tasks in the background
        import threading
        def sync_all_tasks():
            sync_daily_dsa_task()
            sync_neetcode_tasks()
        
        threading.Thread(target=sync_all_tasks, daemon=True).start()

        self.signals.ready_for_input.emit()
        self.signals.update_status.emit("Listening for 'Hey Jarvis'...", "#888888")
        self.signals.update_avatar.emit("idle")
        self.signals.update_tasks.emit()  # Load tasks on boot

        while True:
            user_text = None
            
            # Check if wake word was triggered
            if self.wakeword_triggered:
                self.wakeword_triggered = False
                
                # Stop any current speech
                stop_speaking()
                
                # Show the floating reactor
                self.signals.show_reactor.emit()
                
                # Acknowledge
                self.signals.update_status.emit("Listening...", "#00FF00")
                self.signals.update_avatar.emit("listening")
                
                # Actually listen for the command
                voice_text = listen()
                
                if voice_text:
                    user_text = voice_text
                else:
                    self.signals.update_status.emit("Didn't catch that", "#FFaa00")
                    self.signals.hide_reactor.emit()
                    self.wakeword.resume()
                    continue
                    
            # Check for manual text input
            silent = False
            if not self.input_queue.empty():
                item = self.input_queue.get()
                if isinstance(item, tuple):
                    user_text, silent = item
                else:
                    user_text = item
                    silent = False
                
            if not user_text:
                self.msleep(100) # Sleep briefly to prevent CPU hogging
                continue

            # Pause wake word while processing
            self.wakeword.pause()
            self.signals.update_chat.emit("You", user_text, "#00FF00")

            # Clean text for command matching
            clean_cmd = user_text.lower().strip().strip('.?!')
            if clean_cmd.startswith("jarvis"):
                clean_cmd = clean_cmd[6:].strip()

            if clean_cmd in ["quit", "exit", "shutdown", "shut down", "power off", "sleep"]:
                self.signals.update_chat.emit(Config.JARVIS_NAME, "Powering down systems. Goodbye, Sir.", "#00FFFF")
                speak("Powering down systems. Goodbye, Sir.", block=True)
                self.signals.shutdown_app.emit()
                break
                
            if clean_cmd in ["reset", "clear"]:
                self.brain.reset_conversation()
                self.signals.update_chat.emit("System", "Conversation memory cleared.", "#888888")
                self.wakeword.resume()
                self.signals.update_status.emit("Listening for 'Hey Jarvis'...", "#888888")
                continue

            # --- Proactive DSA Nudge ---
            import time
            current_time = time.time()
            if current_time - self.last_nudge_time > 7200:  # 2 hours
                self.last_nudge_time = current_time
                if self.brain_ok and Config.LEETCODE_USERNAME:
                    from skills.leetcode_tracker import check_leetcode_progress
                    progress = check_leetcode_progress(Config.LEETCODE_USERNAME)
                    if "No recent accepted submissions found" in progress:
                        nudge_msg = f"Excuse me, Sir. It has been a while since your last LeetCode submission. I highly recommend spending some time on Data Structures and Algorithms to maintain your consistency."
                        self.signals.update_chat.emit(Config.JARVIS_NAME, nudge_msg, "#00FFFF")
                        if not self.silent_mode:
                            speak(nudge_msg, block=True)
            # ---------------------------

            # Process with AI
            if self.brain_ok:
                self.signals.update_status.emit("Thinking...", "#00FFFF")
                self.signals.update_avatar.emit("thinking")
                response = self.brain.think(user_text)
                
                # Update quota after response
                self.signals.update_quota.emit(self.brain.get_quota_string())
                
                self.signals.update_chat.emit(Config.JARVIS_NAME, response, "#00FFFF")
                self.signals.launcher_response.emit(response)
                
                # Speak response only if not silent!
                if not silent and not self.silent_mode:
                    self.signals.update_status.emit("Speaking...", "#00FFFF")
                    self.signals.update_avatar.emit("speaking")
                    speak(response, block=True)
                else:
                    self.signals.update_status.emit("Ready", "#00FF00")
                    self.signals.update_avatar.emit("idle")
            else:
                self.signals.update_chat.emit("System", "Cannot process command without AI brain.", "#FF0000")
                self.signals.launcher_response.emit("⚠️ Cannot process command: AI brain is offline.")
                self.signals.update_avatar.emit("error")

            # Refresh task panel after every response (task might have been added/completed)
            self.signals.update_tasks.emit()

            # Hide reactor and resume wake word
            self.signals.hide_reactor.emit()
            self.wakeword.resume()
            self.signals.update_status.emit("Listening for 'Hey Jarvis'...", "#888888")
            self.signals.update_avatar.emit("idle")


# ── Main Application Window ───────────────────────────────────
class JarvisApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("J.A.R.V.I.S.")
        self.resize(650, 900)
        
        # Set dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0A0F14;
            }
            QTextEdit {
                background-color: #05080A;
                color: #FFFFFF;
                border: 1px solid #1A2530;
                border-radius: 5px;
                padding: 10px;
                font-family: 'Menlo', 'Consolas', monospace;
                font-size: 13px;
            }
            /* Basic markdown element styling supported by QTextEdit */
            QTextEdit pre {
                background-color: #111820;
                color: #00FFFF;
                padding: 5px;
                border: 1px solid #1A2530;
            }
            QTextEdit code {
                color: #FFaa00;
                background-color: #111820;
            }
            QLineEdit {
                background-color: #1A2530;
                color: #00FFFF;
                border: 1px solid #00FFFF;
                border-radius: 15px;
                padding: 8px 15px;
                font-family: 'Menlo', 'Consolas', monospace;
                font-size: 14px;
            }
            QLabel#StatusLabel {
                color: #888888;
                font-family: 'Menlo', 'Consolas', monospace;
                font-size: 12px;
                font-weight: bold;
            }
            QLabel#QuotaLabel {
                color: #FFaa00;
                font-family: 'Menlo', 'Consolas', monospace;
                font-size: 11px;
                background-color: #1A2530;
                padding: 4px 8px;
                border-radius: 4px;
            }
            QFrame#TaskPanel {
                background-color: #0D1520;
                border: 1px solid #1A2530;
                border-radius: 8px;
                padding: 8px;
            }
            QLabel#TaskTitle {
                color: #FFaa00;
                font-family: 'Menlo', 'Consolas', monospace;
                font-size: 13px;
                font-weight: bold;
            }
            QLabel#TaskItem {
                color: #CCCCCC;
                font-family: 'Menlo', 'Consolas', monospace;
                font-size: 12px;
                padding: 2px 0px;
            }
            QLabel#TaskEmpty {
                color: #555555;
                font-family: 'Menlo', 'Consolas', monospace;
                font-size: 11px;
                font-style: italic;
            }
            QLabel#TitleLabel {
                color: #00FFFF;
                font-family: 'Menlo', 'Consolas', monospace;
                font-size: 24px;
                font-weight: bold;
                letter-spacing: 2px;
            }
        """)

        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()
        self.title_label = QLabel("J.A.R.V.I.S.")
        self.title_label.setObjectName("TitleLabel")
        
        self.quota_label = QLabel("Quota: 1500")
        self.quota_label.setObjectName("QuotaLabel")
        self.quota_label.setVisible(False)
        
        self.status_label = QLabel("Initializing...")
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.quota_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_label)
        main_layout.addLayout(header_layout)

        # Chat Log
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        main_layout.addWidget(self.chat_display)

        # Input Area
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type a command or say 'Hey Jarvis'...")
        self.input_field.returnPressed.connect(self.send_text_command)
        self.input_field.setEnabled(False) # Disabled until boot finishes
        
        input_layout.addWidget(self.input_field)
        main_layout.addLayout(input_layout)

        # Task Panel (collapsible, between chat and input)
        self.task_panel = QFrame()
        self.task_panel.setObjectName("TaskPanel")
        self.task_panel_layout = QVBoxLayout(self.task_panel)
        self.task_panel_layout.setContentsMargins(10, 8, 10, 8)
        self.task_panel_layout.setSpacing(4)

        task_header = QLabel("📋 Today's Tasks")
        task_header.setObjectName("TaskTitle")
        self.task_panel_layout.addWidget(task_header)

        self.task_items_layout = QVBoxLayout()
        self.task_items_layout.setSpacing(2)
        self.task_panel_layout.addLayout(self.task_items_layout)

        self.task_empty_label = QLabel("No tasks yet. Tell Jarvis to add one!")
        self.task_empty_label.setObjectName("TaskEmpty")
        self.task_items_layout.addWidget(self.task_empty_label)

        main_layout.addWidget(self.task_panel)

        # Floating Arc Reactor Overlay (always on top, follows user)
        self.floating_reactor = FloatingReactorWindow()
        self.floating_reactor.hide()  # Hidden by default
        self.floating_reactor.clicked.connect(self._toggle_chat_window)

        # Floating Command Launcher (Spotlight / Raycast style)
        self.launcher = FloatingLauncherWindow()
        self.launcher.hide()

        # Setup Worker
        self.brain = Brain()
        self.signals = WorkerSignals()
        
        self.signals.update_chat.connect(self.append_chat)
        self.signals.update_status.connect(self.set_status)
        self.signals.update_quota.connect(self.set_quota)
        self.signals.update_avatar.connect(self.floating_reactor.set_state)
        self.signals.update_tasks.connect(self.refresh_tasks)
        self.signals.ready_for_input.connect(lambda: self.input_field.setEnabled(True))
        self.signals.shutdown_app.connect(self._quit_application)
        
        # Launcher signals
        self.signals.launcher_response.connect(self.launcher.set_response)
        self.signals.toggle_launcher.connect(self.launcher.toggle_visibility)
        self.launcher.submitted.connect(self._handle_launcher_submission)
        self.launcher.open_dashboard_requested.connect(self._force_show_chat)
        self.launcher.speak_requested.connect(self._speak_text_async)

        # Reactor visibility signals
        self.signals.show_reactor.connect(self._show_floating_reactor)
        self.signals.hide_reactor.connect(self.floating_reactor.hide)
        
        self.worker = JarvisWorker(self.brain, self.signals)
        self.worker.start()

        # Setup System Tray Icon & Global Hotkeys
        self._setup_tray_icon()
        self._setup_hotkeys()

        # Stealth Teleprompter HUD (Screen-Share Invisible — Google Meet Copilot)
        self.stealth_hud = StealthHUDWindow()
        self.stealth_worker = StealthQuestionWorker(self)
        self.stealth_worker.listening_started.connect(self._on_stealth_listening_started)
        self.stealth_worker.question_transcribed.connect(self._on_stealth_question_transcribed)
        self.stealth_worker.answer_ready.connect(self._on_stealth_answer_ready)
        self.stealth_worker.partial_answer_ready.connect(self._on_stealth_partial_answer)
        self.stealth_worker.answer_source.connect(self._on_stealth_answer_source)
        self.stealth_worker.audio_device_info.connect(self._on_stealth_audio_device)
        self.stealth_worker.error_occurred.connect(self._on_stealth_error)
        self.stealth_hud.answer_requested.connect(self._trigger_stealth_answer)
        self.stealth_hud.text_question_submitted.connect(self._handle_stealth_text_question)
        self.stealth_hud.snip_requested.connect(self._trigger_stealth_snip)
        self.signals.toggle_stealth.connect(self._toggle_stealth_hud)
        self.signals.trigger_stealth_answer.connect(self._trigger_stealth_answer)
        self.signals.trigger_stealth_snip.connect(self._trigger_stealth_snip)

        # Screen Snipper Worker (Req 4: Crop Friend 1's screen questions)
        self.screen_snipper = ScreenSnipperWorker(self)
        self.screen_snipper.snippet_captured.connect(self._on_snippet_captured)
        self.screen_snipper.snippet_cancelled.connect(self._on_snippet_cancelled)
        self.screen_snipper.snippet_error.connect(self._on_stealth_error)

        # Meeting Recording Timer for live tray status
        self.meeting_timer = QTimer(self)
        self.meeting_timer.timeout.connect(self._update_meeting_tray_timer)

        # Apply screen-share invisibility to the MAIN Jarvis window
        # This makes the chat window invisible to Google Meet / Zoom screen sharing
        # but still visible to the user on their physical screen.
        QTimer.singleShot(500, self._apply_stealth_to_main_window)

        # Start Mobile API Server
        try:
            from server.api import start_api_server
            start_api_server(self.brain, self.signals)
        except Exception as e:
            print(f"⚠️ Failed to start Mobile API server: {e}")

    def _setup_hotkeys(self):
        """Initialize global system-wide hotkeys (Option+Space, Option+R, Option+S, Option+A, Option+O)."""
        self.hotkey_mgr = HotkeyManager(self)
        self.hotkey_mgr.hotkey_triggered.connect(self.signals.toggle_launcher.emit)
        self.hotkey_mgr.meeting_hotkey_triggered.connect(self._toggle_meeting_recording_from_tray)
        self.hotkey_mgr.stealth_toggle_triggered.connect(self._toggle_stealth_hud)
        self.hotkey_mgr.stealth_answer_triggered.connect(self._trigger_stealth_answer)
        self.hotkey_mgr.stealth_snip_triggered.connect(self._trigger_stealth_snip)
        self.hotkey_mgr.start()

    def _handle_launcher_submission(self, query: str, silent: bool = True):
        """Forward query from floating launcher to worker queue in silent/fast mode."""
        self.worker.input_queue.put((query, silent))

    def _speak_text_async(self, text: str):
        """Speak text on demand in a background thread so UI never freezes."""
        threading.Thread(target=speak, args=(text,), daemon=True).start()

    def _create_tray_pixmap(self, recording: bool = False) -> QPixmap:
        """Create high-DPI macOS menu bar tray icon (Cyan Arc Reactor or Bright Red Recording Dot)."""
        pixmap = QPixmap(44, 44)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if recording:
            # Bright Red Recording Indicator
            painter.setPen(QPen(QColor('#FF2D55'), 4))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(4, 4, 36, 36)
            
            painter.setBrush(QBrush(QColor('#FF2D55')))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(12, 12, 20, 20)
        else:
            # Cyan Arc Reactor
            painter.setPen(QPen(QColor('#00FFFF'), 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(4, 4, 36, 36)
            
            painter.setBrush(QBrush(QColor('#00FFFF')))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(14, 14, 16, 16)
        painter.end()
        return pixmap

    def _setup_tray_icon(self):
        """Create and configure the macOS menu bar icon with rich controls."""
        # Initialize tray icon with Arc Reactor
        self.tray_icon = QSystemTrayIcon(QIcon(self._create_tray_pixmap(recording=False)))
        self.tray_icon.setToolTip("J.A.R.V.I.S. Personal AI Assistant")
        self.tray_icon.activated.connect(self._on_tray_icon_activated)
        
        # Create context menu with rich cyberpunk styling
        self.tray_menu = QMenu()
        self.tray_menu.setStyleSheet("""
            QMenu {
                background-color: #0D1520;
                color: #E6EDF3;
                border: 1px solid #1A2536;
                padding: 4px;
                font-family: 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 20px 6px 12px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #00FFFF;
                color: #0A0F14;
            }
            QMenu::separator {
                height: 1px;
                background-color: #1A2536;
                margin: 4px 0px;
            }
        """)
        
        # Status & Backend Display
        self.status_action = QAction("🤖 J.A.R.V.I.S. (Antigravity Engine Active)", self)
        self.status_action.setEnabled(False)
        self.tray_menu.addAction(self.status_action)
        
        self.tray_menu.addSeparator()

        # Meeting & Class Auto-Notes Action (PROMINENT AT TOP!)
        self.meeting_action = QAction("🎙️ Start Meeting / Class Auto-Notes (⌥R)", self)
        self.meeting_action.triggered.connect(self._toggle_meeting_recording_from_tray)
        self.tray_menu.addAction(self.meeting_action)

        # Stealth Teleprompter Copilot (Screen-Share Invisible)
        self.stealth_action = QAction("🕵️ Stealth Copilot (Screen-Invisible) [⌥S]", self)
        self.stealth_action.triggered.connect(self._toggle_stealth_hud)
        self.tray_menu.addAction(self.stealth_action)

        self.stealth_answer_action = QAction("⚡ Quick Answer Friend's Question [⌥A]", self)
        self.stealth_answer_action.triggered.connect(self._trigger_stealth_answer)
        self.tray_menu.addAction(self.stealth_answer_action)

        self.stealth_snip_action = QAction("✂️ Screen Snippet Question Solver [⌥O]", self)
        self.stealth_snip_action.triggered.connect(self._trigger_stealth_snip)
        self.tray_menu.addAction(self.stealth_snip_action)
        
        self.tray_menu.addSeparator()
        
        # Quick Launcher (Option+Space or Cmd+Shift+J)
        self.launcher_action = QAction("⚡ Quick Launcher (⌥Space or ⌘⇧J)", self)
        self.launcher_action.triggered.connect(self.launcher.summon)
        self.tray_menu.addAction(self.launcher_action)
        
        # Open Full Chat
        self.open_action = QAction("💬 Open Full Workspace", self)
        self.open_action.triggered.connect(self._force_show_chat)
        self.tray_menu.addAction(self.open_action)
        
        self.tray_menu.addSeparator()
        
        # Silent Mode Toggle (Text-First)
        self.silent_action = QAction("🔇 Silent Mode (No Voice Audio)", self)
        self.silent_action.setCheckable(True)
        self.silent_action.setChecked(self.worker.silent_mode)
        self.silent_action.triggered.connect(self._toggle_silent_mode)
        self.tray_menu.addAction(self.silent_action)
        
        # Wake Word Toggle
        self.wakeword_action = QAction("🎤 Wake Word ('Hey Jarvis')", self)
        self.wakeword_action.setCheckable(True)
        self.wakeword_action.setChecked(True)
        self.wakeword_action.triggered.connect(self._toggle_wakeword)
        self.tray_menu.addAction(self.wakeword_action)
        
        self.tray_menu.addSeparator()
        
        # Refresh Tasks
        self.tasks_action = QAction("📋 Refresh Tasks & DSA", self)
        self.tasks_action.triggered.connect(self.refresh_tasks)
        self.tray_menu.addAction(self.tasks_action)
        
        # Auto-start on macOS Login
        self.autostart_action = QAction("🚀 Launch on Mac Startup", self)
        self.autostart_action.setCheckable(True)
        self.autostart_action.setChecked(is_autostart_enabled())
        self.autostart_action.triggered.connect(self._toggle_autostart)
        self.tray_menu.addAction(self.autostart_action)
        
        self.tray_menu.addSeparator()
        
        # Clean Quit
        self.quit_action = QAction("❌ Quit J.A.R.V.I.S.", self)
        self.quit_action.triggered.connect(self._quit_application)
        self.tray_menu.addAction(self.quit_action)
        
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.show()

    def _toggle_silent_mode(self, checked: bool):
        """Toggle silent text-first mode on worker."""
        self.worker.silent_mode = checked
        state_text = "enabled (Text only)" if checked else "disabled (Voice on)"
        if hasattr(self, 'tray_icon'):
            self.tray_icon.showMessage(
                "J.A.R.V.I.S.",
                f"Silent mode {state_text}.",
                QSystemTrayIcon.MessageIcon.Information,
                1500
            )

    def _toggle_wakeword(self, checked: bool):
        """Toggle wake word detection."""
        if checked:
            self.worker.wakeword.resume()
        else:
            self.worker.wakeword.pause()

    def _toggle_autostart(self, checked: bool):
        """Toggle launch at login."""
        if checked:
            ok, msg = enable_autostart()
        else:
            ok, msg = disable_autostart()
        if hasattr(self, 'tray_icon'):
            self.tray_icon.showMessage(
                "J.A.R.V.I.S.",
                msg,
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
        self.autostart_action.setChecked(checked if ok else not checked)

    def _on_tray_icon_activated(self, reason):
        """Handle direct clicks on the menu bar tray icon."""
        rec = get_meeting_recorder()
        # If recording is actively in progress, clicking tray icon stops & summarizes
        if rec.is_recording():
            self._toggle_meeting_recording_from_tray()

    def _toggle_meeting_recording_from_tray(self):
        """Start or stop meeting recording from the macOS menu bar or ⌥R hotkey."""
        rec = get_meeting_recorder()
        if not rec.is_recording():
            ok, msg = rec.start("Class / Meeting")
            if ok:
                # 1. Update visual icon immediately to BRIGHT RED RECORDING DOT
                self.tray_icon.setIcon(QIcon(self._create_tray_pixmap(recording=True)))
                self.tray_icon.setToolTip("🔴 J.A.R.V.I.S. — RECORDING CLASS NOTES (Click icon or ⌥R to Stop)")
                
                # 2. Play subtle macOS audio chime
                try:
                    subprocess.Popen(["afplay", "/System/Library/Sounds/Tink.aiff"])
                except Exception:
                    pass

                # 3. Update tray action text & start timer
                self.meeting_action.setText("🔴 STOP Recording (00:00) & Extract Notes (⌥R)")
                self.meeting_timer.start(1000)

                # 4. System notification banner
                if hasattr(self, 'tray_icon'):
                    self.tray_icon.showMessage(
                        "J.A.R.V.I.S. Auto-Notes Started",
                        "🎙️ Recording active! J.A.R.V.I.S. is capturing class concepts & assignments in the background.",
                        QSystemTrayIcon.MessageIcon.Information,
                        3000
                    )
                self.signals.update_status.emit("🔴 Recording Class / Meeting...", "#FF2D55")
            else:
                try:
                    subprocess.Popen(["afplay", "/System/Library/Sounds/Basso.aiff"])
                except Exception:
                    pass
                if hasattr(self, 'tray_icon'):
                    self.tray_icon.showMessage("J.A.R.V.I.S. Recording Error", msg, QSystemTrayIcon.MessageIcon.Warning, 3000)
        else:
            # Stop recording & trigger Antigravity analysis
            self.meeting_timer.stop()
            
            # Reset icon back to Cyan Arc Reactor immediately
            self.tray_icon.setIcon(QIcon(self._create_tray_pixmap(recording=False)))
            self.tray_icon.setToolTip("J.A.R.V.I.S. — Analyzing Class Notes (Antigravity Engine)...")
            
            try:
                subprocess.Popen(["afplay", "/System/Library/Sounds/Glass.aiff"])
            except Exception:
                pass

            self.meeting_action.setText("⏳ Analyzing with Antigravity Engine...")
            self.meeting_action.setEnabled(False)
            self.signals.update_status.emit("Analyzing Notes (Antigravity Engine)...", "#00FFFF")

            def process_meeting_async():
                out_path, duration, title = rec.stop()
                if not out_path or duration < 1.0:
                    self._reset_meeting_action()
                    return

                result = analyze_meeting_audio(out_path, title=title)
                self._reset_meeting_action()

                if result.get("success"):
                    try:
                        subprocess.Popen(["afplay", "/System/Library/Sounds/Hero.aiff"])
                    except Exception:
                        pass

                    md = result.get("markdown", "")
                    num_tasks = len(result.get("action_items_added", []))
                    
                    self.signals.update_chat.emit(Config.JARVIS_NAME, md, "#00FFFF")
                    self.signals.launcher_response.emit(md)
                    self.signals.update_tasks.emit()  # Refresh dashboard task panel!
                    self.signals.update_status.emit(f"Class Notes Ready ({num_tasks} tasks added)", "#00FF00")
                    
                    # Auto summon the floating launcher so user sees notes immediately
                    self.signals.toggle_launcher.emit()
                    
                    if hasattr(self, 'tray_icon'):
                        self.tray_icon.showMessage(
                            "J.A.R.V.I.S. Class Notes Ready",
                            f"✅ Meeting notes ready! {num_tasks} assignments synced to your dashboard tasks.",
                            QSystemTrayIcon.MessageIcon.Information,
                            4000
                        )
                else:
                    err = result.get("error", "Unknown error")
                    self.signals.update_status.emit("Meeting analysis failed", "#FF0000")
                    self.signals.update_chat.emit("System", f"⚠️ Meeting analysis failed: {err}", "#FF0000")

            threading.Thread(target=process_meeting_async, daemon=True).start()

    def _update_meeting_tray_timer(self):
        """Update the menu bar item text with live recording elapsed time."""
        rec = get_meeting_recorder()
        if rec.is_recording():
            elapsed = rec.get_elapsed_seconds()
            mins = elapsed // 60
            secs = elapsed % 60
            self.meeting_action.setText(f"🔴 STOP Recording ({mins:02d}:{secs:02d}) & Extract Notes (⌥R)")
        else:
            self._reset_meeting_action()

    def _reset_meeting_action(self):
        """Reset meeting action back to default ready state."""
        self.meeting_timer.stop()
        self.meeting_action.setText("🎙️ Start Meeting / Class Auto-Notes (⌥R)")
        self.meeting_action.setEnabled(True)
        self.tray_icon.setIcon(QIcon(self._create_tray_pixmap(recording=False)))
        self.tray_icon.setToolTip("J.A.R.V.I.S. Personal AI Assistant")

    def _toggle_stealth_hud(self):
        """Toggle the screen-share-invisible teleprompter HUD."""
        self.stealth_hud.toggle_hud()
        if hasattr(self, "stealth_action"):
            if self.stealth_hud.isVisible():
                self.stealth_action.setText("🟢 Hide Stealth Copilot [⌥S]")
            else:
                self.stealth_action.setText("🕵️ Stealth Copilot (Screen-Invisible) [⌥S]")

    def _trigger_stealth_answer(self):
        """Trigger question listening and immediate answering for the Stealth HUD."""
        if not self.stealth_hud.isVisible():
            self._toggle_stealth_hud()

        # Temporarily pause wakeword detector so microphone is exclusively available
        # Stop any active TTS speaking so audio never leaks to meeting
        stop_speaking()

        self.stealth_hud.set_listening_state(True)
        if not self.stealth_worker.isRunning():
            self.stealth_worker.start()

    def _trigger_stealth_snip(self):
        """Trigger interactive screen snippet question capture (Req 4)."""
        if not self.stealth_hud.isVisible():
            self._toggle_stealth_hud()

        # Stop any active TTS speaking
        stop_speaking()

        # Temporarily pause wakeword detector
        if hasattr(self, "worker") and hasattr(self.worker, "wakeword") and self.worker.wakeword:
            self.worker.wakeword.pause()

        self.stealth_hud.set_listening_state(True, "✂️ Drag crosshairs over question on screen (Esc to cancel)...")
        if not self.screen_snipper.isRunning():
            self.screen_snipper.start()

    def _on_snippet_captured(self, image_path: str):
        """Handle snippet image captured from screen."""
        self.stealth_hud.set_listening_state(True, "🔍 Solving question from screen snippet...")
        self.stealth_worker.ask_image_question(image_path)

    def _on_snippet_cancelled(self):
        """Handle user cancelling snippet selection."""
        self.stealth_hud.set_listening_state(False)
        self.stealth_hud.question_box.setText("Snippet cancelled. Press ⌥O to retry.")
        if hasattr(self, "worker") and hasattr(self.worker, "wakeword") and self.worker.wakeword:
            self.worker.wakeword.resume()

    def _handle_stealth_text_question(self, question: str):
        """Directly synthesize answer for user-typed question in Stealth HUD."""
        if not question.strip():
            return
        self.stealth_hud.set_listening_state(True, f"Synthesizing answer for: {question}...")
        self.stealth_worker.ask_text_question(question)

    def _on_stealth_listening_started(self, text: str):
        self.stealth_hud.set_listening_state(True, text)

    def _on_stealth_question_transcribed(self, q: str):
        self.stealth_hud.question_box.setText(f"Q: {q}")
        self.stealth_hud.question_box.setStyleSheet("""
            color: #00FFFF;
            font-size: 12px;
            font-weight: bold;
            background: rgba(0, 255, 255, 0.08);
            border: 1px solid rgba(0, 255, 255, 0.3);
            border-radius: 6px;
            padding: 6px 10px;
        """)

    def _on_stealth_answer_ready(self, question: str, direct_answer: str, key_points: list):
        self.stealth_hud.display_answer(question, direct_answer, key_points)
        # Safely resume wakeword detector
        if hasattr(self, "worker") and hasattr(self.worker, "wakeword") and self.worker.wakeword:
            self.worker.wakeword.resume()

    def _on_stealth_error(self, err: str):
        self.stealth_hud.set_listening_state(False)
        self.stealth_hud.question_box.setText(f"⚠️ {err}")
        self.stealth_hud.question_box.setStyleSheet("""
            color: #FF2D55;
            font-size: 12px;
            font-weight: bold;
            background: rgba(255, 45, 85, 0.08);
            border: 1px solid rgba(255, 45, 85, 0.3);
            border-radius: 6px;
            padding: 6px 10px;
        """)
        # Safely resume wakeword detector
        if hasattr(self, "worker") and hasattr(self.worker, "wakeword") and self.worker.wakeword:
            self.worker.wakeword.resume()

    def _on_stealth_partial_answer(self, question: str, direct_answer: str, key_points: list):
        """Display quick flash answer from local KB while full CLI/SDK answer loads."""
        self.stealth_hud.display_partial_answer(question, direct_answer, key_points)

    def _on_stealth_answer_source(self, source: str):
        """Update the answer source badge on the HUD."""
        self.stealth_hud.set_answer_source(source)

    def _on_stealth_audio_device(self, device_text: str):
        """Update the audio source badge on the HUD."""
        self.stealth_hud.set_audio_source(device_text)

    def _force_show_chat(self):
        """Force the chat window to open so the user can interact manually."""
        self._move_to_active_space()
        self.show()
        self.raise_()
        self.activateWindow()
        self.input_field.setFocus()

    def _show_floating_reactor(self):
        """Show the floating reactor and ensure it configures correctly."""
        self.floating_reactor.show()
        self.floating_reactor.raise_()
        self.floating_reactor.activateWindow()

    def append_chat(self, role: str, text: str, color: str):
        """Add a message to the chat display."""
        import markdown
        
        # Format the text with Markdown
        html_text = markdown.markdown(text, extensions=['fenced_code', 'tables', 'nl2br'])
        
        # Apply CSS for QTextEdit support
        html = f"""
        <div style="margin-bottom: 12px; margin-top: 5px;">
            <span style="color: {color}; font-weight: bold; font-size: 14px;">{role}:</span>
            <div style="color: #EEEEEE; font-size: 13px; margin-top: 4px;">
                {html_text}
            </div>
        </div>
        <hr style="background-color: #1A2530; height: 1px; border: none; margin-bottom: 8px;">
        """
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)
        self.chat_display.insertHtml(html)
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)

    def set_status(self, text: str, color: str):
        """Update the status indicator."""
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};")
        
        # Also update the system tray icon status
        if hasattr(self, 'status_action'):
            self.status_action.setText(f"Status: {text}")
        if hasattr(self, 'tray_icon'):
            self.tray_icon.setToolTip(f"J.A.R.V.I.S. — {text}")
        
    def set_quota(self, text: str):
        """Update the quota indicator."""
        self.quota_label.setText(text)
        self.quota_label.setVisible(True)
        
        # Change color based on remaining amount (heuristic: check if number is < 50)
        import re
        match = re.search(r'\b(\d+)\b', text)
        if match:
            remaining = int(match.group(1))
            if remaining < 50:
                self.quota_label.setStyleSheet("color: #FF0000; background-color: #330000;")
            elif remaining < 200:
                self.quota_label.setStyleSheet("color: #FFaa00; background-color: #332200;")
            else:
                self.quota_label.setStyleSheet("color: #00FF00; background-color: #003300;")

    def refresh_tasks(self):
        """Reload today's tasks from disk and rebuild the task panel."""
        from skills.task_manager import get_today_tasks_for_panel

        # Clear existing task items
        while self.task_items_layout.count():
            item = self.task_items_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        tasks = get_today_tasks_for_panel()
        
        if not tasks:
            empty_label = QLabel("No tasks yet. Tell Jarvis to add one!")
            empty_label.setObjectName("TaskEmpty")
            self.task_items_layout.addWidget(empty_label)
        else:
            for t in tasks:
                status = "✅" if t.get("completed") else "⬜"
                priority_icon = {"high": "🔴", "normal": "🟡", "low": "🟢"}.get(t.get("priority", "normal"), "🟡")
                task_label = QLabel(f"  {status} #{t['id']} {priority_icon} {t['task']}")
                task_label.setObjectName("TaskItem")
                if t.get("completed"):
                    task_label.setStyleSheet("color: #555555; text-decoration: line-through;")
                self.task_items_layout.addWidget(task_label)

    def send_text_command(self):
        """Handle manual text input from the user."""
        text = self.input_field.text().strip()
        if text:
            self.input_field.clear()
            self.worker.input_queue.put(text)

    def _toggle_chat_window(self):
        """Toggle the main chat window visibility. Moves it to the current Space."""
        if self.isVisible():
            self.hide()
        else:
            # Move the chat window to whichever Space the user is currently on
            self._move_to_active_space()
            self.show()
            self.raise_()
            self.activateWindow()

    def _apply_stealth_to_main_window(self):
        """Apply NSWindowSharingNone to the main Jarvis chat window.
        
        This makes the entire Jarvis app invisible to screen sharing,
        screen recording, and screenshots — but still visible to the user
        on their physical display. People in Google Meet / Zoom CANNOT
        see the Jarvis window when you share your screen.
        """
        import sys
        if sys.platform != "darwin":
            return
        try:
            from AppKit import NSApp

            for window in NSApp.windows():
                title = window.title() or ""
                if "J.A.R.V.I.S." in title:
                    # NSWindowSharingNone = 0 → invisible to screen capture/sharing
                    window.setSharingType_(0)
                    print(f"  🛡️ Main window stealth: NSWindowSharingNone applied (sharingType={window.sharingType()})")
                    print(f"      → Jarvis is INVISIBLE to Google Meet screen sharing")
                    print(f"      → Jarvis is VISIBLE to you on your physical screen")
                    break
        except Exception as e:
            print(f"  ⚠️  Could not apply stealth to main window: {e}")

    def _move_to_active_space(self):
        """Move all Jarvis windows to the currently active macOS Space.
        
        Uses a combination of:
        - MoveToActiveSpace (1 << 1) = teleport window to the user's current Space
        - CanJoinAllSpaces (1 << 0) = temporarily allow the window on all Spaces
        
        This ensures Jarvis opens on the SAME desktop where Google Meet is,
        not on a different Space.
        """
        import sys
        if sys.platform != "darwin":
            return
        try:
            from AppKit import NSApp

            # NSWindowCollectionBehaviorMoveToActiveSpace = 1 << 1 = 2
            MoveToActiveSpace = 1 << 1

            jarvis_titles = {"J.A.R.V.I.S.", "JarvisStealthHUD"}

            for window in NSApp.windows():
                title = window.title() or ""
                if any(t in title for t in jarvis_titles):
                    # Set MoveToActiveSpace so it teleports to the current desktop
                    window.setCollectionBehavior_(MoveToActiveSpace)
                    # Force the window to the front on the active Space
                    window.orderFrontRegardless()
        except Exception as e:
            print(f"  ⚠️  Could not move chat to active space: {e}")

    def closeEvent(self, event):
        """Minimize to menu bar tray instead of killing the application."""
        event.ignore()
        self.hide()
        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                "J.A.R.V.I.S.",
                "Running in menu bar. Press Option+Space anytime to summon.",
                QSystemTrayIcon.MessageIcon.Information,
                1500
            )

    def _quit_application(self):
        """Clean shutdown of background hotkeys, threads, and process."""
        if hasattr(self, 'hotkey_mgr'):
            self.hotkey_mgr.stop()
        self.set_status("Shutting down...", "#FF0000")
        stop_speaking()
        import os
        os._exit(0)

def run_gui(minimized: bool = False):
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep app running in background
    window = JarvisApp()
    
    if not minimized:
        # Show the chat window initially upon launch
        window._move_to_active_space()
        window.show()
        window.raise_()
        window.activateWindow()
        
        # Show the floating reactor globe initially upon launch
        window._show_floating_reactor()
    else:
        window.worker.silent_mode = True
        if hasattr(window, 'silent_action'):
            window.silent_action.setChecked(True)
        print("  ✨ J.A.R.V.I.S. running in the macOS menu bar. Press Option+Space (⌥Space) anytime to summon.\n")
    
    sys.exit(app.exec())