"""
Stealth Teleprompter HUD for J.A.R.V.I.S. (Screen-Share Invisible)
Google Meet Real-Time Q&A Copilot.

Uses macOS Cocoa AppKit's NSWindowSharingNone (sharingType = 0) to ensure the
HUD is 100% visible on the user's physical screen, but COMPLETELY INVISIBLE
to screen sharing (Google Meet, Zoom, Microsoft Teams, Discord, etc.)
and screen recording / screenshots.

Features:
  • Streaming answer display (word-by-word typing animation)
  • Loading spinner (animated braille pattern)
  • Copy-to-clipboard button
  • Audio source indicator badge (Mic vs System Audio)
  • Session Q&A history (collapsible sidebar)
  • Draggable window, positioned below webcam
"""

import sys
import os
import threading
from typing import Optional, List, Dict

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QFrame, QGraphicsDropShadowEffect, QSizePolicy,
    QApplication, QLineEdit, QScrollArea
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QTimer
from ctypes import c_void_p
from PyQt6.QtGui import QFont, QColor, QPalette, QCursor, QPainter, QBrush, QPen

from config import Config


def _apply_stealth_to_window(qt_widget: QWidget) -> bool:
    """
    Configure the Stealth HUD as a Spotlight-like NSPanel for reliable
    fullscreen overlay and screen-share invisibility.

    Architecture (modeled after macOS Spotlight):
      1. Qt.WindowType.Tool flag → Qt creates QNSPanel (NSPanel subclass)
      2. setFloatingPanel_(True) → float above ALL windows including fullscreen
      3. FullScreenAuxiliary collection behavior → native fullscreen Space overlay
      4. setSharingType_(0) → invisible to screen capture / screen sharing
      5. SkyLight kCGSTagSticky (0x800) → belt-and-suspenders fullscreen stickiness

    This is the exact same mechanism macOS Spotlight, Alfred, Raycast, and
    Notification Center use to appear on ALL Spaces including fullscreen apps.
    """
    if sys.platform != "darwin":
        return False

    try:
        import objc
        from AppKit import NSApp

        qt_widget.setWindowTitle("JarvisStealthHUD")

        ns_panel = None

        # 1. Direct retrieval via Qt winId using c_void_p
        try:
            view_ptr = int(qt_widget.winId())
            ns_view = objc.objc_object(c_void_p=view_ptr)
            ns_panel = ns_view.window()
        except Exception:
            pass

        # 2. Fallback search through NSApp windows
        if not ns_panel and NSApp:
            for win in NSApp.windows():
                if win.title() == "JarvisStealthHUD" or (
                    abs(win.frame().size.width - qt_widget.width()) < 10
                    and abs(win.frame().size.height - qt_widget.height()) < 10
                ):
                    ns_panel = win
                    break

        if not ns_panel:
            print("  ⚠️ Could not retrieve NSPanel for Stealth HUD.")
            return False

        is_panel = ns_panel.isKindOfClass_(objc.lookUpClass('NSPanel'))

        # ═══ Screen-Share Invisibility ═══
        # NSWindowSharingNone = 0 (omitted from screen capture / screen sharing)
        ns_panel.setSharingType_(0)

        # ═══ Spotlight-Like NSPanel Configuration ═══
        # These properties are what make Spotlight appear on every fullscreen app.
        # They only work properly on NSPanel (created by Qt.WindowType.Tool flag).

        # setFloatingPanel_(True): THE critical property. Makes the panel float
        # above ALL windows across ALL Spaces, including fullscreen Spaces.
        # This is the #1 difference between NSPanel and NSWindow behavior.
        if is_panel and hasattr(ns_panel, 'setFloatingPanel_'):
            ns_panel.setFloatingPanel_(True)

        # worksWhenModal: appear even when modal dialogs are open
        if is_panel and hasattr(ns_panel, 'setWorksWhenModal_'):
            ns_panel.setWorksWhenModal_(True)

        # becomesKeyOnlyIfNeeded: clicks on buttons/text don't steal app focus
        if is_panel and hasattr(ns_panel, 'setBecomesKeyOnlyIfNeeded_'):
            ns_panel.setBecomesKeyOnlyIfNeeded_(True)

        # ═══ Collection Behavior (Spaces + Fullscreen) ═══
        CAN_JOIN_ALL_SPACES = 1 << 0    # Appear on every desktop/Space
        STATIONARY = 1 << 4              # Stay in place during Space-switch animations
        IGNORES_CYCLE = 1 << 6           # Skip Cmd+` app window cycling
        FULL_SCREEN_AUXILIARY = 1 << 8   # Overlay fullscreen apps (NSPanel-native)
        ns_panel.setCollectionBehavior_(
            CAN_JOIN_ALL_SPACES | STATIONARY | IGNORES_CYCLE | FULL_SCREEN_AUXILIARY
        )

        # ═══ Window Level ═══
        # kCGScreenSaverWindowLevel (1000) — high enough to be above all app windows
        # and fullscreen content, but below the compositor's shielding windows.
        # Spotlight uses level 23, but we use 1000 for maximum reliability.
        TARGET_LEVEL = 1000
        ns_panel.setLevel_(TARGET_LEVEL)

        # Don't hide when app deactivates
        ns_panel.setHidesOnDeactivate_(False)

        # Prevent activation stealing — keep focus on user's active window
        if ns_panel.respondsToSelector_(b"_setPreventsActivation:"):
            ns_panel._setPreventsActivation_(True)

        # No animation on space switch
        if ns_panel.respondsToSelector_(b"setAnimationBehavior:"):
            ns_panel.setAnimationBehavior_(0)

        # Prevent macOS from auto-hiding us
        if ns_panel.respondsToSelector_(b"setCanHide:"):
            ns_panel.setCanHide_(False)

        ns_panel.orderFrontRegardless()

        # ═══ SkyLight Private Framework: Belt-and-Suspenders Stickiness ═══
        # The NSPanel + floatingPanel + FullScreenAuxiliary combination is the
        # primary mechanism (identical to Spotlight). SkyLight sticky tag is
        # applied as additional insurance for edge cases during Space transitions.
        try:
            from ctypes import cdll, c_int, c_int64, byref
            skylight = cdll.LoadLibrary(
                "/System/Library/PrivateFrameworks/SkyLight.framework/SkyLight"
            )
            skylight._CGSDefaultConnection.restype = c_int
            cgs_conn = skylight._CGSDefaultConnection()
            wid = ns_panel.windowNumber()

            # kCGSTagSticky (0x800) = appear on ALL Spaces including fullscreen
            kCGSTagSticky = c_int64(0x800)
            skylight.SLSSetWindowTags(
                c_int(cgs_conn), c_int(wid), byref(kCGSTagSticky), c_int(64)
            )
            # Also set level at CGS layer
            skylight.SLSSetWindowLevel(
                c_int(cgs_conn), c_int(wid), c_int(TARGET_LEVEL)
            )

            # Cache for reassert timer
            qt_widget._skylight = skylight
            qt_widget._cgs_conn = cgs_conn
            qt_widget._window_id = wid

            ns_panel.orderFrontRegardless()

            panel_type = "NSPanel" if is_panel else "NSWindow"
            floating = ns_panel.isFloatingPanel() if is_panel else False
            print(f"  🛡️ Stealth mode active: {panel_type} (floating={floating}), "
                  f"sharingType={ns_panel.sharingType()}, level={ns_panel.level()}, "
                  f"SkyLight sticky ✅, Spotlight-like ✅")
        except Exception as e_sl:
            print(f"  🛡️ Stealth mode active: sharingType={ns_panel.sharingType()}, "
                  f"level={ns_panel.level()}, SkyLight unavailable ({e_sl})")

        # Cache the NSPanel reference for fast access in reassert timer
        qt_widget._cached_ns_window = ns_panel

        return True

    except Exception as e:
        print(f"  ⚠️ Error configuring Spotlight-like stealth panel: {e}")
        return False


class StealthHUDWindow(QWidget):
    """
    A frameless, screen-share-invisible teleprompter HUD that floats on top
    of all windows (positioned just beneath the user's webcam).

    Designed for real-time Q&A during Google Meet screen-sharing sessions.
    """

    answer_requested = pyqtSignal()              # Signal to trigger microphone listening & answering
    text_question_submitted = pyqtSignal(str)    # Signal to trigger answering for typed question
    snip_requested = pyqtSignal()                 # Signal to trigger screen snippet OCR (⌥O)
    copy_requested = pyqtSignal()                # Copy answer to clipboard

    # Spinner frames for loading animation
    _SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, parent=None):
        super().__init__(parent)

        self.drag_position = QPoint()
        self._is_stealth_configured = False
        self._is_compact = False
        self._spinner_index = 0
        self._spinner_timer = QTimer(self)
        self._spinner_timer.timeout.connect(self._animate_spinner)

        # Streaming text animation
        self._stream_buffer = ""
        self._stream_index = 0
        self._stream_timer = QTimer(self)
        self._stream_timer.timeout.connect(self._stream_next_word)

        # Periodic re-assertion timer: macOS can demote window levels during
        # fullscreen Space transitions. This timer re-applies the level every 2s
        # while the HUD is visible, ensuring it stays above fullscreen apps.
        self._reassert_timer = QTimer(self)
        self._reassert_timer.timeout.connect(self._reassert_stealth_level)

        # Session Q&A history (local mirror)
        self._qa_history: List[Dict[str, str]] = []
        self._history_visible = False

        self.setWindowTitle("JarvisStealthHUD")

        # Frameless + Always on top + Transparent background
        # Qt.WindowType.Tool → makes Qt create QNSPanel (NSPanel subclass)
        # instead of QNSWindow (NSWindow). NSPanel is what Spotlight, Alfred,
        # and Raycast use to appear on fullscreen Spaces natively.
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.setMinimumSize(420, 200)
        self.resize(580, 340)

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

        # Audio source indicator badge
        self.audio_badge = QLabel("🎤 Mic", self)
        self.audio_badge.setStyleSheet("""
            color: #8B949E;
            font-size: 10px;
            font-weight: bold;
            font-family: 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif;
            border: 1px solid rgba(139, 148, 158, 0.3);
            border-radius: 4px;
            padding: 2px 6px;
            background: rgba(139, 148, 158, 0.1);
        """)
        top_bar.addWidget(self.audio_badge)

        # Answer source badge
        self.source_badge = QLabel("", self)
        self.source_badge.setStyleSheet("""
            color: #58A6FF;
            font-size: 10px;
            font-weight: bold;
            font-family: 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif;
            border: 1px solid rgba(88, 166, 255, 0.3);
            border-radius: 4px;
            padding: 2px 6px;
            background: rgba(88, 166, 255, 0.1);
        """)
        self.source_badge.hide()
        top_bar.addWidget(self.source_badge)

        # Screen Snippet Question Tool Button (Req 4)
        self.snip_btn = QPushButton("✂️ Snip (⌥O)", self)
        self.snip_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.snip_btn.setToolTip("Crop and solve question from Friend 1's screen (⌥O)")
        self.snip_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(88, 166, 255, 0.18);
                color: #58A6FF;
                font-weight: bold;
                font-size: 10px;
                padding: 4px 8px;
                border-radius: 4px;
                border: 1px solid rgba(88, 166, 255, 0.4);
            }
            QPushButton:hover {
                background-color: rgba(88, 166, 255, 0.35);
                color: #FFFFFF;
            }
        """)
        self.snip_btn.clicked.connect(self.snip_requested.emit)
        top_bar.addWidget(self.snip_btn)

        # Listen / Answer Button (Req 2 & 3)
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
            QPushButton:disabled {
                background-color: #1A3A3A;
                color: #4A6A6A;
            }
        """)
        self.answer_btn.clicked.connect(self.answer_requested.emit)
        top_bar.addWidget(self.answer_btn)

        # Compact / Full view toggle button (Req 6)
        self.compact_btn = QPushButton("⤢", self)
        self.compact_btn.setFixedSize(26, 26)
        self.compact_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.compact_btn.setToolTip("Toggle Compact / Expanded View")
        self.compact_btn.setStyleSheet("""
            QPushButton {
                color: #8B949E;
                font-size: 13px;
                background: rgba(139, 148, 158, 0.1);
                border: 1px solid rgba(139, 148, 158, 0.2);
                border-radius: 4px;
            }
            QPushButton:hover {
                color: #00FFFF;
                border-color: rgba(0, 255, 255, 0.4);
                background: rgba(0, 255, 255, 0.1);
            }
        """)
        self.compact_btn.clicked.connect(self._toggle_compact)
        top_bar.addWidget(self.compact_btn)

        # History toggle button
        self.history_btn = QPushButton("📋", self)
        self.history_btn.setFixedSize(26, 26)
        self.history_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.history_btn.setToolTip("Toggle Q&A History")
        self.history_btn.setStyleSheet("""
            QPushButton {
                color: #8B949E;
                font-size: 14px;
                background: rgba(139, 148, 158, 0.1);
                border: 1px solid rgba(139, 148, 158, 0.2);
                border-radius: 4px;
            }
            QPushButton:hover {
                color: #00FFFF;
                border-color: rgba(0, 255, 255, 0.4);
                background: rgba(0, 255, 255, 0.1);
            }
        """)
        self.history_btn.clicked.connect(self._toggle_history)
        top_bar.addWidget(self.history_btn)

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
        self.question_box = QLabel("Waiting for question... (Press ⌥A or type above)", self)
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

        # ── Direct Flash Answer Header + Copy Button ──────────────
        answer_header = QHBoxLayout()
        answer_header.setContentsMargins(0, 0, 0, 0)

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
        answer_header.addWidget(self.direct_answer_label)
        answer_header.addStretch()

        # Copy Answer button
        self.copy_btn = QPushButton("📋 Copy", self)
        self.copy_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.copy_btn.setStyleSheet("""
            QPushButton {
                color: #8B949E;
                font-size: 10px;
                font-weight: bold;
                background: rgba(139, 148, 158, 0.1);
                border: 1px solid rgba(139, 148, 158, 0.2);
                border-radius: 4px;
                padding: 2px 8px;
            }
            QPushButton:hover {
                color: #00FF88;
                border-color: rgba(0, 255, 136, 0.4);
                background: rgba(0, 255, 136, 0.1);
            }
        """)
        self.copy_btn.clicked.connect(self._copy_answer)
        answer_header.addWidget(self.copy_btn)

        card_layout.addLayout(answer_header)

        # ── Answer Display (Scrollable) ───────────────────────────
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
            QScrollBar:vertical {
                background: rgba(10, 15, 23, 0.5);
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(0, 255, 255, 0.3);
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        self.answer_display.setPlaceholderText("Your answer will appear here...")
        self.answer_display.setMinimumHeight(80)
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

        # ── Session Q&A History (Collapsible) ─────────────────────
        self.history_frame = QFrame(self)
        self.history_frame.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(0, 255, 255, 0.15);
                border-radius: 6px;
            }
        """)
        history_layout = QVBoxLayout(self.history_frame)
        history_layout.setContentsMargins(8, 6, 8, 6)
        history_layout.setSpacing(4)

        history_title = QLabel("📋 Session Q&A History", self)
        history_title.setStyleSheet("""
            color: #58A6FF;
            font-size: 11px;
            font-weight: bold;
            border: none;
            background: transparent;
        """)
        history_layout.addWidget(history_title)

        self.history_list = QLabel("No questions asked yet.", self)
        self.history_list.setWordWrap(True)
        self.history_list.setStyleSheet("""
            color: #8B949E;
            font-size: 11px;
            border: none;
            background: transparent;
            padding: 2px;
        """)
        history_layout.addWidget(self.history_list)

        self.history_frame.hide()
        card_layout.addWidget(self.history_frame)

        # Footer tip
        footer = QLabel("⌥S: Toggle • ⌥A: Listen • Enter: Send • Esc: Hide", self)
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
            self.question_input.clearFocus()

    def _toggle_compact(self):
        """Toggle between compact (440x220) and standard (580x340) views (Req 6)."""
        self._is_compact = not self._is_compact
        if self._is_compact:
            self.resize(440, 220)
            self.compact_btn.setText("⤢")
            self.compact_btn.setToolTip("Switch to Standard View")
            self.answer_display.setMinimumHeight(60)
        else:
            self.resize(580, 340)
            self.compact_btn.setText("⤡")
            self.compact_btn.setToolTip("Switch to Compact View")
            self.answer_display.setMinimumHeight(80)

    def _copy_answer(self):
        """Copy the current answer text to clipboard."""
        text = self.answer_display.toPlainText().strip()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            # Visual feedback
            original_text = self.copy_btn.text()
            self.copy_btn.setText("✅ Copied!")
            self.copy_btn.setStyleSheet("""
                QPushButton {
                    color: #00FF88;
                    font-size: 10px;
                    font-weight: bold;
                    background: rgba(0, 255, 136, 0.15);
                    border: 1px solid rgba(0, 255, 136, 0.4);
                    border-radius: 4px;
                    padding: 2px 8px;
                }
            """)
            QTimer.singleShot(1500, lambda: self._reset_copy_btn(original_text))

    def _reset_copy_btn(self, text: str):
        """Reset copy button to default state."""
        self.copy_btn.setText(text)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                color: #8B949E;
                font-size: 10px;
                font-weight: bold;
                background: rgba(139, 148, 158, 0.1);
                border: 1px solid rgba(139, 148, 158, 0.2);
                border-radius: 4px;
                padding: 2px 8px;
            }
            QPushButton:hover {
                color: #00FF88;
                border-color: rgba(0, 255, 136, 0.4);
                background: rgba(0, 255, 136, 0.1);
            }
        """)

    def _toggle_history(self):
        """Toggle the session Q&A history panel."""
        self._history_visible = not self._history_visible
        if self._history_visible:
            self._refresh_history()
            self.history_frame.show()
            self.history_btn.setStyleSheet("""
                QPushButton {
                    color: #00FFFF;
                    font-size: 14px;
                    background: rgba(0, 255, 255, 0.15);
                    border: 1px solid rgba(0, 255, 255, 0.4);
                    border-radius: 4px;
                }
            """)
        else:
            self.history_frame.hide()
            self.history_btn.setStyleSheet("""
                QPushButton {
                    color: #8B949E;
                    font-size: 14px;
                    background: rgba(139, 148, 158, 0.1);
                    border: 1px solid rgba(139, 148, 158, 0.2);
                    border-radius: 4px;
                }
                QPushButton:hover {
                    color: #00FFFF;
                    border-color: rgba(0, 255, 255, 0.4);
                    background: rgba(0, 255, 255, 0.1);
                }
            """)

    def _refresh_history(self):
        """Refresh the Q&A history display from session data."""
        try:
            from skills.stealth_copilot import get_session_history
            history = get_session_history()
        except Exception:
            history = self._qa_history

        if not history:
            self.history_list.setText("No questions asked yet.")
            return

        lines = []
        for i, entry in enumerate(reversed(history[-5:]), 1):
            q = entry.get("question", "")[:60]
            a = entry.get("answer", "")[:80]
            lines.append(f"<b style='color:#00FFFF;'>Q{i}:</b> {q}")
            lines.append(f"<span style='color:#C9D1D9;'>→ {a}</span>")
            if i < len(history):
                lines.append("")

        self.history_list.setText("<br>".join(lines))

    def _position_below_webcam(self):
        """Position the HUD centered at the top of the active screen just beneath the webcam."""
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if screen:
            geom = screen.geometry()
            x = geom.x() + (geom.width() - self.width()) // 2
            y = geom.y() + 45  # Right below the top menu bar / webcam
            self.move(x, y)

    def showEvent(self, event):
        """When the window is shown, apply stealth + start the re-assertion timer."""
        super().showEvent(event)
        self._apply_stealth()
        # Start periodic re-assertion as a lightweight safety net.
        # With NSPanel + floatingPanel, this is rarely needed (Spotlight-like behavior
        # is native), but it catches edge cases during rapid Space switches.
        if not self._reassert_timer.isActive():
            self._reassert_timer.start(3000)  # 3s — NSPanel needs less aggressive reassertion

    def hideEvent(self, event):
        """When the window is hidden, stop the re-assertion timer to save CPU."""
        super().hideEvent(event)
        self._reassert_timer.stop()

    def _apply_stealth(self):
        """Apply stealth screen-share exclusion + fullscreen overlay config."""
        ok = _apply_stealth_to_window(self)
        self._is_stealth_configured = ok
        if ok:
            self.badge_label.setText("🟢 STEALTH ACTIVE — INVISIBLE TO SCREEN SHARE")
            self.badge_label.setStyleSheet("color: #00FF88; font-size: 11px; font-weight: bold; border: none; background: transparent;")
        else:
            self.badge_label.setText("🟡 HUD ACTIVE")

    def _reassert_stealth_level(self):
        """Lightweight safety net: re-assert NSPanel stealth properties if demoted.

        With the Spotlight-like NSPanel architecture (floatingPanel + FullScreenAuxiliary),
        fullscreen overlay works natively — this timer is a belt-and-suspenders fallback
        that re-applies SkyLight sticky tags and NSPanel properties if macOS ever
        demotes the window during rapid Space transitions.

        Runs every 3 seconds while the HUD is visible.
        """
        if not self.isVisible():
            self._reassert_timer.stop()
            return

        if sys.platform != "darwin":
            return

        try:
            # Use cached NSPanel reference (set by _apply_stealth_to_window)
            ns_panel = getattr(self, "_cached_ns_window", None)

            if not ns_panel:
                import objc
                try:
                    view_ptr = int(self.winId())
                    ns_view = objc.objc_object(c_void_p=view_ptr)
                    ns_panel = ns_view.window()
                    self._cached_ns_window = ns_panel
                except Exception:
                    pass

            if not ns_panel:
                return

            TARGET_LEVEL = 1000  # kCGScreenSaverWindowLevel

            # Re-assert NSPanel floating panel property (can be reset by Qt updates)
            is_panel = ns_panel.isKindOfClass_(
                __import__('objc').lookUpClass('NSPanel')
            )
            if is_panel and hasattr(ns_panel, 'isFloatingPanel'):
                if not ns_panel.isFloatingPanel():
                    ns_panel.setFloatingPanel_(True)

            # Re-assert level if demoted
            if ns_panel.level() < TARGET_LEVEL:
                ns_panel.setLevel_(TARGET_LEVEL)

            # Re-apply SkyLight sticky tag if available
            skylight = getattr(self, "_skylight", None)
            cgs_conn = getattr(self, "_cgs_conn", None)
            wid = getattr(self, "_window_id", None)

            if skylight and cgs_conn is not None and wid is not None:
                from ctypes import c_int, c_int64, byref
                kCGSTagSticky = c_int64(0x800)
                skylight.SLSSetWindowTags(
                    c_int(cgs_conn), c_int(wid), byref(kCGSTagSticky), c_int(64)
                )

            # Ensure visible
            ns_panel.orderFrontRegardless()

        except Exception:
            pass

    def toggle_hud(self):
        """Toggle HUD visibility without stealing focus from the active workspace (Req 5)."""
        if self.isVisible():
            self.hide()
        else:
            self._position_below_webcam()
            self.show()
            self.raise_()
            self._apply_stealth()

    def set_listening_state(self, is_listening: bool = True, text: str = ""):
        """Update display when listening for voice or processing a question."""
        if is_listening:
            self.question_box.setText(text or "🎙️ Listening for question...")
            self.question_box.setStyleSheet("""
                color: #00FFFF;
                font-size: 12px;
                font-weight: bold;
                background: rgba(0, 255, 255, 0.08);
                border: 1px solid rgba(0, 255, 255, 0.3);
                border-radius: 6px;
                padding: 6px 10px;
            """)
            self.answer_btn.setText("⏳ Processing...")
            self.answer_btn.setEnabled(False)
            # Start loading spinner
            self._start_spinner()
        else:
            self.answer_btn.setText("⚡ Answer (⌥A)")
            self.answer_btn.setEnabled(True)
            self._stop_spinner()

    def _start_spinner(self):
        """Start the loading spinner animation in the answer display."""
        self._spinner_index = 0
        self.answer_display.setPlainText("⏳ Generating answer...")
        self._spinner_timer.start(100)  # 100ms per frame

    def _stop_spinner(self):
        """Stop the spinner animation."""
        self._spinner_timer.stop()

    def _animate_spinner(self):
        """Advance the spinner animation frame."""
        frame = self._SPINNER_FRAMES[self._spinner_index % len(self._SPINNER_FRAMES)]
        self.answer_display.setPlainText(f"  {frame}  Generating answer from Antigravity...")
        self._spinner_index += 1

    def set_audio_source(self, source_text: str):
        """Update the audio source badge (Mic vs System Audio)."""
        self.audio_badge.setText(source_text)
        if "system" in source_text.lower() or "blackhole" in source_text.lower():
            self.audio_badge.setStyleSheet("""
                color: #00FF88;
                font-size: 10px;
                font-weight: bold;
                font-family: 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif;
                border: 1px solid rgba(0, 255, 136, 0.3);
                border-radius: 4px;
                padding: 2px 6px;
                background: rgba(0, 255, 136, 0.1);
            """)
        else:
            self.audio_badge.setStyleSheet("""
                color: #8B949E;
                font-size: 10px;
                font-weight: bold;
                font-family: 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif;
                border: 1px solid rgba(139, 148, 158, 0.3);
                border-radius: 4px;
                padding: 2px 6px;
                background: rgba(139, 148, 158, 0.1);
            """)

    def set_answer_source(self, source: str):
        """Show which engine generated the answer."""
        if source:
            self.source_badge.setText(f"⚡ {source}")
            self.source_badge.show()
        else:
            self.source_badge.hide()

    def display_answer(self, question: str, direct_answer: str, key_points: list = None):
        """
        Display the question and generated answer on the HUD.

        Args:
            question: The question asked
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

        # Start streaming animation for the answer
        self._stream_answer(direct_answer)

        # Display Key Points
        if key_points:
            points_html = "<br>".join([
                f"• <b>{pt}</b>" if ":" not in pt else f"• {pt}"
                for pt in key_points[:4]
            ])
            self.points_display.setText(points_html)
            self.points_display.show()
        else:
            self.points_display.hide()

        # Update local Q&A history cache
        self._qa_history.append({"question": clean_q, "answer": direct_answer})
        if len(self._qa_history) > 5:
            self._qa_history = self._qa_history[-5:]

        # Refresh history panel if visible
        if self._history_visible:
            self._refresh_history()

        # Ensure window is visible
        if not self.isVisible():
            self.show()
            self.raise_()

    def display_partial_answer(self, question: str, direct_answer: str, key_points: list = None):
        """
        Display a quick partial answer (from local KB) before the full answer arrives.
        Shows with a subtle "flash" badge to indicate it's an instant result.
        """
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

        # Show flash answer immediately (no streaming for partial)
        self.answer_display.setHtml(f"""
            <div style="font-size: 14px; color: #C9D1D9; line-height: 1.45; font-style: italic;">
                {direct_answer}
            </div>
            <div style="font-size: 10px; color: #58A6FF; margin-top: 6px;">
                ⚡ Flash answer — full response loading...
            </div>
        """)

        if key_points:
            points_html = "<br>".join([
                f"• <b>{pt}</b>" if ":" not in pt else f"• {pt}"
                for pt in key_points[:3]
            ])
            self.points_display.setText(points_html)
            self.points_display.show()

    def _stream_answer(self, text: str):
        """Start streaming the answer word-by-word with a typing animation."""
        self._stream_timer.stop()
        self._stream_buffer = text
        self._stream_index = 0
        self.answer_display.clear()

        words = text.split()
        if len(words) <= 5:
            # Short answer — display immediately
            self.answer_display.setHtml(f"""
                <div style="font-size: 15px; color: #FFFFFF; line-height: 1.45;">
                    {text}
                </div>
            """)
        else:
            # Stream word-by-word
            self._stream_words = words
            self._stream_rendered = []
            self._stream_timer.start(35)  # 35ms per word

    def _stream_next_word(self):
        """Render the next word in the streaming animation."""
        if self._stream_index >= len(self._stream_words):
            self._stream_timer.stop()
            return

        self._stream_rendered.append(self._stream_words[self._stream_index])
        self._stream_index += 1

        rendered_text = " ".join(self._stream_rendered)
        self.answer_display.setHtml(f"""
            <div style="font-size: 15px; color: #FFFFFF; line-height: 1.45;">
                {rendered_text}<span style="color: #00FFFF;">▌</span>
            </div>
        """)

        # Auto-scroll to bottom
        scrollbar = self.answer_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        # Remove cursor on last word
        if self._stream_index >= len(self._stream_words):
            self._stream_timer.stop()
            self.answer_display.setHtml(f"""
                <div style="font-size: 15px; color: #FFFFFF; line-height: 1.45;">
                    {rendered_text}
                </div>
            """)

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
