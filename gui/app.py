import os
import sys
import threading
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTextEdit, QLineEdit, QPushButton, QLabel, QFrame,
    QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon, QTextCursor, QPixmap, QPainter, QBrush, QAction

from gui.floating_reactor import FloatingReactorWindow

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

# ── Worker Thread for Jarvis Logic ────────────────────────────
class JarvisWorker(QThread):
    def __init__(self, brain, signals):
        super().__init__()
        self.brain = brain
        self.signals = signals
        self.mic_available = is_mic_available()
        self.brain_ok = False
        
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
            if not self.input_queue.empty():
                user_text = self.input_queue.get()
                
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
                self.signals.update_status.emit("Speaking...", "#00FFFF")
                self.signals.update_avatar.emit("speaking")
                
                # Speak response
                speak(response, block=True)
            else:
                self.signals.update_chat.emit("System", "Cannot process command without AI brain.", "#FF0000")
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

        # Setup System Tray Icon
        self._setup_tray_icon()

        # Floating Arc Reactor Overlay (always on top, follows user)
        self.floating_reactor = FloatingReactorWindow()
        self.floating_reactor.hide()  # Hidden by default
        self.floating_reactor.clicked.connect(self._toggle_chat_window)

        # Setup Worker
        self.brain = Brain()
        self.signals = WorkerSignals()
        
        self.signals.update_chat.connect(self.append_chat)
        self.signals.update_status.connect(self.set_status)
        self.signals.update_quota.connect(self.set_quota)
        self.signals.update_avatar.connect(self.floating_reactor.set_state)
        self.signals.update_tasks.connect(self.refresh_tasks)
        self.signals.ready_for_input.connect(lambda: self.input_field.setEnabled(True))
        self.signals.shutdown_app.connect(self.close)
        
        # Reactor visibility signals
        self.signals.show_reactor.connect(self._show_floating_reactor)
        self.signals.hide_reactor.connect(self.floating_reactor.hide)
        
        self.worker = JarvisWorker(self.brain, self.signals)
        self.worker.start()

        # Start Mobile API Server
        try:
            from server.api import start_api_server
            start_api_server(self.brain, self.signals)
        except Exception as e:
            print(f"⚠️ Failed to start Mobile API server: {e}")

    def _setup_tray_icon(self):
        """Create and configure the macOS menu bar icon."""
        # Create a simple glowing blue circle icon
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QBrush(QColor('#00FFFF')))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(16, 16, 32, 32)
        painter.end()

        # Do not pass 'self' as parent, to avoid inheriting the hidden state of the main window
        self.tray_icon = QSystemTrayIcon(QIcon(pixmap))
        
        # Create context menu
        self.tray_menu = QMenu()
        
        self.status_action = QAction("Status: Initializing...", self)
        self.status_action.setEnabled(False)
        self.tray_menu.addAction(self.status_action)
        
        self.tray_menu.addSeparator()
        
        self.open_action = QAction("Open Jarvis Chat", self)
        self.open_action.triggered.connect(self._force_show_chat)
        self.tray_menu.addAction(self.open_action)
        
        self.tray_menu.addSeparator()
        
        self.quit_action = QAction("Quit J.A.R.V.I.S.", self)
        self.quit_action.triggered.connect(self.close)
        self.tray_menu.addAction(self.quit_action)
        
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.show()

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

    def _move_to_active_space(self):
        """Use PyObjC to move the chat window to the currently active macOS Space."""
        import sys
        if sys.platform != "darwin":
            return
        try:
            from AppKit import NSApp

            # NSWindowCollectionBehaviorMoveToActiveSpace = 1 << 1 = 2
            MoveToActiveSpace = 1 << 1

            for window in NSApp.windows():
                title = window.title() or ""
                if "J.A.R.V.I.S." in title:
                    window.setCollectionBehavior_(MoveToActiveSpace)
                    break
        except Exception as e:
            print(f"  ⚠️  Could not move chat to active space: {e}")

    def closeEvent(self, event):
        """Handle application shutdown."""
        self.set_status("Shutting down...", "#FF0000")
        stop_speaking()
        # Force a hard exit to prevent hanging on blocking background C/C++ threads (like PyAudio)
        import os
        os._exit(0)

def run_gui():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep app running in background
    window = JarvisApp()
    
    # Show the chat window initially upon launch
    window._move_to_active_space()
    window.show()
    window.raise_()
    window.activateWindow()
    
    # Show the floating reactor globe initially upon launch
    window._show_floating_reactor()
    
    sys.exit(app.exec())