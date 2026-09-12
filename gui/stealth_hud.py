"""
Stealth Teleprompter HUD for J.A.R.V.I.S. (Screen-Share Invisible)
Inspired by Cluely / Interview Copilot.

Uses macOS Cocoa AppKit's NSWindowSharingNone (sharingType = 0) to ensure the
HUD is 100% visible on the user's physical screen, but COMPLETELY INVISIBLE
to screen sharing (Google Meet, Zoom, Microsoft Teams, Discord, etc.)
and screen recording / screenshots.
"""

import sys
import os
import threading
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QFrame, QGraphicsDropShadowEffect, QSizePolicy,
    QApplication, QLineEdit
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette, QCursor, QPainter, QBrush, QPen

from config import Config


def _apply_stealth_to_window(qt_widget: QWidget) -> bool:
    """
    Apply macOS NSWindowSharingNone (sharingType = 0) to make the window
    completely invisible to screen capture, screen sharing, and recording.
    Also ensures visibility across all Spaces and fullscreen apps.
    """
    if sys.platform != "darwin":
        return False

    try:
        import objc
        from AppKit import NSApp

        qt_widget.setWindowTitle("JarvisStealthHUD")

        ns_window = None

        # 1. Direct retrieval via Qt winId
        try:
            view_ptr = int(qt_widget.winId())
            ns_view = objc.objc_object(c_void_p=view_ptr)
            ns_window = ns_view.window()
        except Exception:
            pass

        # 2. Fallback search through NSApp windows
        if not ns_window and NSApp:
            for win in NSApp.windows():
                if win.title() == "JarvisStealthHUD" or (
                    abs(win.frame().size.width - qt_widget.width()) < 10
                    and abs(win.frame().size.height - qt_widget.height()) < 10
                ):
                    ns_window = win
                    break

        if not ns_window:
            print("  ⚠️ Could not retrieve NSWindow for Stealth HUD.")
            return False

        # NSWindowSharingNone = 0 (Window is omitted from screen capture / screen sharing)
        ns_window.setSharingType_(0)

        # NSWindowCollectionBehaviorCanJoinAllSpaces = 1 << 0 (1)
        # NSWindowCollectionBehaviorStationary = 1 << 4 (16)
        # NSWindowCollectionBehaviorFullScreenAuxiliary = 1 << 8 (256)
        collection_behavior = (1 << 0) | (1 << 4) | (1 << 8)
        ns_window.setCollectionBehavior_(collection_behavior)

        # NSStatusWindowLevel = 25 (Floats above fullscreen apps & video call overlays)
        ns_window.setLevel_(25)
        ns_window.setHidesOnDeactivate_(False)
        ns_window.orderFrontRegardless()

        print(f"  🛡️ Stealth mode active: NSWindowSharingNone (sharingType={ns_window.sharingType()}) on all Spaces")
        return True

    except Exception as e:
        print(f"  ⚠️ Error configuring screen-share invisibility: {e}")
        return False


class StealthHUDWindow(QWidget):
    """
    A frameless, screen-share-invisible teleprompter HUD that floats on top
    of all windows (positioned just beneath the user's webcam).
    """

    answer_requested = pyqtSignal()          # Signal to trigger microphone listening & answering
    text_question_submitted = pyqtSignal(str) # Signal to trigger answering for typed question

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.drag_position = QPoint()
        self._is_stealth_configured = False
        self.setWindowTitle("JarvisStealthHUD")

        # Frameless + Always on top + Transparent background
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.setMinimumSize(480, 290)
        self.resize(520, 310)

        self._build_ui()
        self._position_below_webcam()

    def _build_ui(self):
        """Construct the sleek dark cyberpunk teleprompter card."""
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)

        # Main background container card
        self.card = QFrame(self)
        self.card.setStyleSheet("""
            QFrame {
                background-color: rgba(10, 15, 23, 0.96);
                border: 1px solid rgba(0, 255, 255, 0.4);
                border-radius: 12px;
            }
        """)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(14, 12, 14, 14)
        card_layout.setSpacing(8)

        # ── Top Status Bar ────────────────────────────────────────
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)

        # Stealth status badge
        self.badge_label = QLabel("🟢 STEALTH ACTIVE — INVISIBLE TO SCREEN SHARE", self)
        self.badge_label.setStyleSheet("""
            color: #00FF88;
            font-size: 11px;
            font-weight: bold;
            font-family: 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif;
            letter-spacing: 0.5px;
            border: none;
            background: transparent;
        """)
        top_bar.addWidget(self.badge_label)
        top_bar.addStretch()

        # Listen / Answer Button
        self.answer_btn = QPushButton("⚡ Answer (⌥A)", self)
        self.answer_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.answer_btn.setStyleSheet("""
            QPushButton {
                background-color: #00FFFF;
                color: #0A0F14;
                font-weight: bold;
                font-size: 11px;
                padding: 4px 10px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #33FFFF;
            }
            QPushButton:pressed {
                background-color: #00CCCC;
            }
        """)
        self.answer_btn.clicked.connect(self.answer_requested.emit)
        top_bar.addWidget(self.answer_btn)

        # Close / Hide button
        self.hide_btn = QPushButton("✕", self)
        self.hide_btn.setFixedSize(20, 20)
        self.hide_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.hide_btn.setStyleSheet("""
            QPushButton {
                color: #8B949E;
                font-size: 13px;
                font-weight: bold;
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                color: #FF2D55;
            }
        """)
        self.hide_btn.clicked.connect(self.hide)
        top_bar.addWidget(self.hide_btn)

        card_layout.addLayout(top_bar)

        # ── Silent Text Question Input ────────────────────────────
        self.question_input = QLineEdit(self)
        self.question_input.setPlaceholderText("💬 Type/paste question & press Enter, or click ⚡ Answer...")
        self.question_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.05);
                color: #00FFFF;
                font-size: 12px;
                font-family: 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif;
                border: 1px solid rgba(0, 255, 255, 0.25);
                border-radius: 6px;
                padding: 5px 8px;
            }
            QLineEdit:focus {
                border: 1px solid #00FFFF;
                background-color: rgba(0, 255, 255, 0.08);
            }
        """)
        self.question_input.returnPressed.connect(self._on_text_submitted)
        card_layout.addWidget(self.question_input)

        # ── Question Section ──────────────────────────────────────
        self.question_box = QLabel("Waiting for teacher's question... (Press ⌥A or click Answer)", self)
        self.question_box.setWordWrap(True)
        self.question_box.setStyleSheet("""
            color: #8B949E;
            font-size: 12px;
            font-style: italic;
            font-family: 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 6px;
            padding: 6px 10px;
        """)
        card_layout.addWidget(self.question_box)

        # ── Direct Flash Answer (For speaking immediately) ────────
        self.direct_answer_label = QLabel("Say This Aloud:", self)
        self.direct_answer_label.setStyleSheet("""
            color: #00FFFF;
            font-size: 11px;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            border: none;
            background: transparent;
            margin-top: 4px;
        """)
        card_layout.addWidget(self.direct_answer_label)

        self.answer_display = QTextEdit(self)
        self.answer_display.setReadOnly(True)
        self.answer_display.setStyleSheet("""
            QTextEdit {
                background-color: rgba(0, 255, 255, 0.04);
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 500;
                line-height: 1.5;
                font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Helvetica Neue', sans-serif;
                border: 1px solid rgba(0, 255, 255, 0.2);
                border-radius: 8px;
                padding: 8px 10px;
            }
        """)
        self.answer_display.setPlaceholderText("When a question is asked, your direct answer will appear here in natural spoken wording...")
        card_layout.addWidget(self.answer_display)

        # ── Key Talking Points (Elaboration) ──────────────────────
        self.points_display = QLabel("", self)
        self.points_display.setWordWrap(True)
        self.points_display.setStyleSheet("""
            color: #C9D1D9;
            font-size: 12px;
            line-height: 1.4;
            font-family: 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif;
            background: transparent;
            border: none;
            padding: 2px 4px;
        """)
        self.points_display.hide()
        card_layout.addWidget(self.points_display)

        # Footer tip
        footer = QLabel("⌥S: Toggle HUD • ⌥A: Capture Question • Esc: Dismiss", self)
        footer.setStyleSheet("""
            color: #6E7681;
            font-size: 10px;
            border: none;
            background: transparent;
        """)
        card_layout.addWidget(footer)

        root_layout.addWidget(self.card)

    def _on_text_submitted(self):
        """Handle user typing a question directly into the stealth HUD."""
        query = self.question_input.text().strip()
        if query:
            self.text_question_submitted.emit(query)
            self.question_input.clear()

    def _position_below_webcam(self):
        """Position the HUD centered at the top of the active screen just beneath the webcam."""
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if screen:
            geom = screen.geometry()
            x = geom.x() + (geom.width() - self.width()) // 2
            y = geom.y() + 45  # Right below the top menu bar / webcam
            self.move(x, y)

    def showEvent(self, event):
        """When the window is shown, ensure macOS NSWindowSharingNone is applied immediately."""
        super().showEvent(event)
        self._apply_stealth()

    def _apply_stealth(self):
        """Apply stealth screen-share exclusion."""
        ok = _apply_stealth_to_window(self)
        self._is_stealth_configured = ok
        if ok:
            self.badge_label.setText("🟢 STEALTH ACTIVE — INVISIBLE TO SCREEN SHARE")
            self.badge_label.setStyleSheet("color: #00FF88; font-size: 11px; font-weight: bold; border: none; background: transparent;")
        else:
            self.badge_label.setText("🟡 HUD ACTIVE")

    def toggle_hud(self):
        """Toggle HUD visibility."""
        if self.isVisible():
            self.hide()
        else:
            self._position_below_webcam()
            self.show()
            self.raise_()
            self.activateWindow()
            self._apply_stealth()
            self.question_input.setFocus()

    def set_listening_state(self, is_listening: bool = True, text: str = ""):
        """Update display when listening for teacher's voice."""
        if is_listening:
            self.question_box.setText(text or "🎙️ Listening to teacher's question...")
            self.question_box.setStyleSheet("""
                color: #00FFFF;
                font-size: 12px;
                font-weight: bold;
                background: rgba(0, 255, 255, 0.08);
                border: 1px solid rgba(0, 255, 255, 0.3);
                border-radius: 6px;
                padding: 6px 10px;
            """)
            self.answer_btn.setText("⏳ Listening...")
            self.answer_btn.setEnabled(False)
        else:
            self.answer_btn.setText("⚡ Answer (⌥A)")
            self.answer_btn.setEnabled(True)

    def display_answer(self, question: str, direct_answer: str, key_points: list = None):
        """
        Display the teacher's question and the generated answer on the HUD.
        
        Args:
            question: The question asked by teacher
            direct_answer: 1-2 punchy spoken sentences
            key_points: Optional list of supporting bullets
        """
        self.set_listening_state(is_listening=False)
        
        # Display Question
        clean_q = question.strip() if question.strip() else "Direct Question"
        self.question_box.setText(f"Q: {clean_q}")
        self.question_box.setStyleSheet("""
            color: #E6EDF3;
            font-size: 12.5px;
            font-weight: 600;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(0, 255, 255, 0.25);
            border-radius: 6px;
            padding: 6px 10px;
        """)

        # Display Direct Answer
        self.answer_display.setHtml(f"""
            <div style="font-size: 15px; color: #FFFFFF; line-height: 1.45;">
                {direct_answer}
            </div>
        """)

        # Display Key Points
        if key_points:
            points_html = "<br>".join([f"• <b>{pt}</b>" if ":" not in pt else f"• {pt}" for pt in key_points[:3]])
            self.points_display.setText(points_html)
            self.points_display.show()
        else:
            self.points_display.hide()

        # Ensure window is visible
        if not self.isVisible():
            self.show()
            self.raise_()

    # ── Mouse Dragging for Window Relocation ───────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def keyPressEvent(self, event):
        """Dismiss on Escape key."""
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)
