"""
Floating Launcher for J.A.R.V.I.S.
A system-wide Spotlight / Raycast style floating command bar.
Summoned anywhere in macOS via Option+Space.
Designed for 50ms access, instant text-first answers, and zero workflow disruption.
"""

import sys
import markdown
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QTextEdit,
    QLabel, QPushButton, QFrame, QGraphicsDropShadowEffect, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint, QSize
from PyQt6.QtGui import QColor, QFont, QCursor, QIcon, QPainter, QBrush, QPen


def _configure_macos_window_spaces(window_title_match="Jarvis-Launcher"):
    """
    Ensure the floating launcher appears instantly on whichever macOS Space
    or full-screen app is currently active.
    """
    if sys.platform != "darwin":
        return
    try:
        from AppKit import NSApp
        # Behaviors: Move to active space, join all spaces, auxiliary window
        behavior = (1 << 0) | (1 << 1) | (1 << 8)
        NSStatusWindowLevel = 25

        for window in NSApp.windows():
            title = window.title() or ""
            if window_title_match in title or "Launcher" in title:
                window.setCollectionBehavior_(behavior)
                window.setLevel_(NSStatusWindowLevel)
                window.setHidesOnDeactivate_(False)
                break
    except Exception:
        pass


class MiniReactorIcon(QWidget):
    """Sleek glowing Arc Reactor indicator icon."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(28, 28)
        self._glow_phase = 0
        self._is_pulsing = False
        
        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self._pulse_step)

    def set_pulsing(self, pulsing: bool):
        self._is_pulsing = pulsing
        if pulsing:
            self.pulse_timer.start(50)
        else:
            self.pulse_timer.stop()
            self._glow_phase = 0
            self.update()

    def _pulse_step(self):
        self._glow_phase = (self._glow_phase + 1) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Outer ring
        center = 14
        if self._is_pulsing:
            import math
            pulse = (math.sin(math.radians(self._glow_phase * 4)) + 1) / 2
            alpha = int(140 + pulse * 115)
            color = QColor(0, 255, 255, alpha)
        else:
            color = QColor(0, 255, 255, 200)

        painter.setPen(QPen(color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(3, 3, 22, 22)

        # Inner core
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(9, 9, 10, 10)
        painter.end()


class FloatingLauncherWindow(QWidget):
    """
    Spotlight / Raycast style floating assistant bar.
    Summoned via Option + Space.
    """
    submitted = pyqtSignal(str, bool)       # query, silent (True = no blocking TTS)
    open_dashboard_requested = pyqtSignal()
    speak_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Jarvis-Launcher")
        
        # Window attributes: Frameless, Always on Top, Translucent
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.fixed_width = 720
        self.compact_height = 70
        self.expanded_height = 460
        self.setFixedWidth(self.fixed_width)
        self.setFixedHeight(self.compact_height)
        
        self.current_response_raw = ""
        self._build_ui()
        self._center_on_screen()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(0)

        # Container Frame (Glassmorphism card)
        self.container = QFrame()
        self.container.setObjectName("LauncherContainer")
        self.container.setStyleSheet("""
            QFrame#LauncherContainer {
                background-color: rgba(10, 15, 24, 0.95);
                border: 1.5px solid rgba(0, 255, 255, 0.5);
                border-radius: 16px;
            }
        """)

        # Drop shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(35)
        shadow.setColor(QColor(0, 255, 255, 60))
        shadow.setOffset(0, 8)
        self.container.setGraphicsEffect(shadow)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(16, 12, 16, 12)
        container_layout.setSpacing(10)

        # ── Input Row ──
        input_row = QHBoxLayout()
        input_row.setSpacing(12)

        # Mini Reactor
        self.reactor_icon = MiniReactorIcon()
        input_row.addWidget(self.reactor_icon)

        # Search / Command Input Field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask Jarvis, paste an error, or type a command... (Esc to dismiss)")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #FFFFFF;
                font-family: 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif;
                font-size: 16px;
                selection-background-color: #00FFFF;
                selection-color: #0A0F14;
            }
        """)
        self.input_field.returnPressed.connect(self._on_submit)
        input_row.addWidget(self.input_field, 1)

        # Badges (Esc & Hotkey info)
        badges_layout = QHBoxLayout()
        badges_layout.setSpacing(6)

        hotkey_badge = QLabel("⌥Space / ⌘⇧J")
        hotkey_badge.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.08);
            color: #8899A6;
            border-radius: 4px;
            padding: 3px 6px;
            font-size: 11px;
            font-family: 'Menlo', monospace;
        """)
        badges_layout.addWidget(hotkey_badge)

        esc_badge = QLabel("Esc")
        esc_badge.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.08);
            color: #8899A6;
            border-radius: 4px;
            padding: 3px 6px;
            font-size: 11px;
            font-family: 'Menlo', monospace;
        """)
        badges_layout.addWidget(esc_badge)

        input_row.addLayout(badges_layout)
        container_layout.addLayout(input_row)

        # ── Clipboard Action Chip (Optional Context) ──
        self.clipboard_chip = QPushButton("💡 Copied Error Detected — Click to Fix with Jarvis")
        self.clipboard_chip.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.clipboard_chip.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 255, 255, 0.12);
                color: #00FFFF;
                border: 1px dashed rgba(0, 255, 255, 0.5);
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 12px;
                font-family: 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif;
                text-align: left;
            }
            QPushButton:hover {
                background-color: rgba(0, 255, 255, 0.22);
            }
        """)
        self.clipboard_chip.clicked.connect(self._use_clipboard_context)
        self.clipboard_chip.hide()
        container_layout.addWidget(self.clipboard_chip)

        # ── Status / Thinking Bar ──
        self.status_label = QLabel("Analyzing...")
        self.status_label.setStyleSheet("""
            color: #00FFFF;
            font-size: 13px;
            font-style: italic;
            padding-left: 40px;
        """)
        self.status_label.hide()
        container_layout.addWidget(self.status_label)

        # ── Response Display (Markdown View) ──
        self.response_display = QTextEdit()
        self.response_display.setReadOnly(True)
        self.response_display.setStyleSheet("""
            QTextEdit {
                background-color: rgba(5, 8, 14, 0.85);
                color: #E6EDF3;
                border: 1px solid rgba(0, 255, 255, 0.2);
                border-radius: 10px;
                padding: 12px;
                font-family: 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif;
                font-size: 13px;
                line-height: 1.5;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
            }
            QScrollBar::handle:vertical {
                background: rgba(0, 255, 255, 0.3);
                border-radius: 3px;
            }
        """)
        self.response_display.hide()
        container_layout.addWidget(self.response_display, 1)

        # ── Action Toolbar ──
        self.action_bar = QWidget()
        action_layout = QHBoxLayout(self.action_bar)
        action_layout.setContentsMargins(0, 4, 0, 0)
        action_layout.setSpacing(8)

        self.copy_btn = QPushButton("📋 Copy")
        self.copy_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.copy_btn.setStyleSheet(self._action_btn_style())
        self.copy_btn.clicked.connect(self._copy_response)
        action_layout.addWidget(self.copy_btn)

        self.speak_btn = QPushButton("🔊 Read Aloud")
        self.speak_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.speak_btn.setStyleSheet(self._action_btn_style())
        self.speak_btn.clicked.connect(self._speak_current_response)
        action_layout.addWidget(self.speak_btn)

        self.full_chat_btn = QPushButton("💬 Open Workspace")
        self.full_chat_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.full_chat_btn.setStyleSheet(self._action_btn_style())
        self.full_chat_btn.clicked.connect(self._open_full_dashboard)
        action_layout.addWidget(self.full_chat_btn)

        action_layout.addStretch()

        self.clear_btn = QPushButton("🧹 Clear")
        self.clear_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.clear_btn.setStyleSheet(self._action_btn_style())
        self.clear_btn.clicked.connect(self.clear)
        action_layout.addWidget(self.clear_btn)

        self.action_bar.hide()
        container_layout.addWidget(self.action_bar)

        main_layout.addWidget(self.container)

    def _action_btn_style(self):
        return """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.07);
                color: #CCCCCC;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(0, 255, 255, 0.2);
                color: #00FFFF;
                border-color: rgba(0, 255, 255, 0.4);
            }
        """

    def _center_on_screen(self):
        """Position horizontally centered, upper third of the active screen."""
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.geometry()
            x = (geom.width() - self.fixed_width) // 2
            y = int(geom.height() * 0.16)
            self.move(x, y)

    def toggle_visibility(self):
        """Toggle between showing and hiding the launcher."""
        if self.isVisible():
            self.hide()
        else:
            self.summon()

    def summon(self):
        """Summon the launcher, move to active space, and focus input."""
        _configure_macos_window_spaces("Jarvis-Launcher")
        self._center_on_screen()
        self._check_clipboard_for_context()
        self.show()
        self.raise_()
        self.activateWindow()
        self.input_field.setFocus()
        self.input_field.selectAll()

    def _check_clipboard_for_context(self):
        """Inspect system clipboard for programming errors or questions to offer 1-click help."""
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        
        # Check if clipboard looks like an error, stack trace, or code snippet
        triggers = ["error", "exception", "traceback", "failed", "warning", "fatal", "syntaxerror", "typeerror", "nullpointer"]
        is_error = any(t in text.lower() for t in triggers)
        
        if text and is_error and len(text) > 20:
            preview = text.split('\n')[0][:45]
            self.clipboard_chip.setText(f"💡 Fix Error: \"{preview}...\" (Click to ask)")
            self.clipboard_chip.show()
            if not self.response_display.isVisible():
                self.setFixedHeight(self.compact_height + 40)
        else:
            self.clipboard_chip.hide()
            if not self.response_display.isVisible():
                self.setFixedHeight(self.compact_height)

    def _use_clipboard_context(self):
        """Inject clipboard text into the prompt as an error diagnosis request."""
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if text:
            self.input_field.setText(f"Explain and fix this error:\n```\n{text}\n```")
            self.clipboard_chip.hide()
            self._on_submit()

    def _on_submit(self):
        """Handle submission from the search bar."""
        query = self.input_field.text().strip()
        if not query:
            return

        self.set_thinking(True)
        self.clipboard_chip.hide()
        # By default, floating launcher runs silently (no blocking TTS)
        self.submitted.emit(query, True)

    def set_thinking(self, is_thinking: bool):
        """Toggle thinking state."""
        self.reactor_icon.set_pulsing(is_thinking)
        if is_thinking:
            self.status_label.setText("⚡ J.A.R.V.I.S. is processing...")
            self.status_label.show()
            self.response_display.hide()
            self.action_bar.hide()
            self.setFixedHeight(self.compact_height + 45)
        else:
            self.status_label.hide()

    def set_response(self, text: str):
        """Render response from AI in rich Markdown and expand window."""
        self.set_thinking(False)
        self.current_response_raw = text

        # Format markdown with extensions
        html = markdown.markdown(
            text,
            extensions=['fenced_code', 'tables', 'nl2br']
        )
        
        # Enhanced CSS for code snippets and readability
        styled_html = f"""
        <style>
            body {{ color: #E6EDF3; font-family: 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif; font-size: 13px; }}
            pre {{ background-color: #101620; color: #00FFFF; border: 1px solid #1A2536; border-radius: 6px; padding: 8px; font-family: 'Menlo', monospace; }}
            code {{ color: #FFaa00; background-color: #101620; font-family: 'Menlo', monospace; }}
            a {{ color: #00FFFF; text-decoration: none; }}
            p {{ margin-bottom: 8px; }}
        </style>
        {html}
        """

        self.response_display.setHtml(styled_html)
        self.response_display.show()
        self.action_bar.show()
        self.setFixedHeight(self.expanded_height)
        self.response_display.moveCursor(self.response_display.textCursor().MoveOperation.Start)

    def _copy_response(self):
        """Copy current response text to clipboard."""
        if self.current_response_raw:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.current_response_raw)
            self.copy_btn.setText("✅ Copied!")
            QTimer.singleShot(1500, lambda: self.copy_btn.setText("📋 Copy"))

    def _speak_current_response(self):
        """Trigger TTS reading of the response on demand."""
        if self.current_response_raw:
            self.speak_requested.emit(self.current_response_raw)

    def _open_full_dashboard(self):
        """Summon the full workspace dashboard."""
        self.hide()
        self.open_dashboard_requested.emit()

    def clear(self):
        """Reset launcher state."""
        self.input_field.clear()
        self.response_display.clear()
        self.current_response_raw = ""
        self.response_display.hide()
        self.action_bar.hide()
        self.status_label.hide()
        self.clipboard_chip.hide()
        self.setFixedHeight(self.compact_height)
        self.input_field.setFocus()

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts."""
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            event.accept()
        else:
            super().keyPressEvent(event)
