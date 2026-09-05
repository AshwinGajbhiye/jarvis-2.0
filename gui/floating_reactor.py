"""
Floating Arc Reactor Overlay — An always-on-top, frameless, transparent window
that contains the Arc Reactor and floats above all other windows.
Visible on ALL macOS Spaces/Desktops. Click to toggle the main chat window. Drag to reposition.
"""

import sys

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal

from gui.arc_reactor import ArcReactorWidget


def _set_visible_on_all_spaces():
    """
    Use PyObjC to find the floating reactor window by its unique size (180x180)
    and make it visible on ALL macOS Spaces/Desktops.
    """
    if sys.platform != "darwin":
        return False

    try:
        from AppKit import NSApp

        # Constants (from AppKit headers)
        NSWindowCollectionBehaviorCanJoinAllSpaces = 1 << 0        # 1
        NSWindowCollectionBehaviorStationary = 1 << 4              # 16
        NSWindowCollectionBehaviorFullScreenAuxiliary = 1 << 8     # 256
        NSStatusWindowLevel = 25

        behavior = (
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorStationary
            | NSWindowCollectionBehaviorFullScreenAuxiliary
        )

        all_windows = NSApp.windows()
        print(f"  🔍 Searching {len(all_windows)} native windows...")

        configured = False
        for window in all_windows:
            frame = window.frame()
            w = frame.size.width
            h = frame.size.height
            level = window.level()
            title = window.title() or "(no title)"
            print(f"     Window: '{title}' size={w:.0f}x{h:.0f} level={level}")

            # Our reactor window is exactly 180x180 and has a floating level
            if abs(w - ArcReactorWidget.WIDGET_SIZE) < 10 and abs(h - ArcReactorWidget.WIDGET_SIZE) < 10:
                window.setCollectionBehavior_(behavior)
                window.setLevel_(NSStatusWindowLevel)
                window.setHidesOnDeactivate_(False)  # Don't hide when app loses focus!
                print(f"  ✅ Configured reactor window: behavior={behavior}, level={NSStatusWindowLevel}")
                configured = True

        if not configured:
            print("  ⚠️  Could not find the reactor window (180x180).")

        return configured

    except ImportError:
        print("  ⚠️  pyobjc not installed. Run: pip install pyobjc-framework-Cocoa")
        return False
    except Exception as e:
        print(f"  ⚠️  Error configuring spaces: {e}")
        return False


class FloatingReactorWindow(QWidget):
    """
    A frameless, always-on-top transparent window that wraps the ArcReactorWidget.
    Visible on ALL macOS Spaces. Can be dragged around. Click to toggle chat window.
    """

    clicked = pyqtSignal()  # Emitted when the user clicks the reactor

    def __init__(self, parent=None):
        super().__init__(parent)

        # Frameless + always on top + transparent
        # Note: NOT using Qt.WindowType.Tool — that causes hidesOnDeactivate on macOS
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow, True)

        # Size to fit the reactor exactly
        self.setFixedSize(ArcReactorWidget.WIDGET_SIZE, ArcReactorWidget.WIDGET_SIZE)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.reactor = ArcReactorWidget(self)
        layout.addWidget(self.reactor)

        # Dragging state
        self._dragging = False
        self._drag_offset = QPoint()
        self._spaces_configured = False

        # Position in bottom-right corner of screen by default
        self._position_default()

    def showEvent(self, event):
        """After the window is shown, configure macOS all-spaces behavior."""
        super().showEvent(event)
        if not self._spaces_configured:
            # Delay to ensure the native window handle is fully ready
            QTimer.singleShot(800, self._configure_all_spaces)

    def _configure_all_spaces(self):
        """Configure the window to appear on all macOS Spaces."""
        if not self._spaces_configured:
            success = _set_visible_on_all_spaces()
            if success:
                self._spaces_configured = True
            else:
                # Retry once more after another delay
                QTimer.singleShot(1000, lambda: _set_visible_on_all_spaces())

    def _position_default(self):
        """Place the reactor in the bottom-right of the primary screen."""
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.right() - self.width() - 30
            y = geo.bottom() - self.height() - 30
            self.move(x, y)

    def set_state(self, state: str):
        """Forward state changes to the inner reactor widget."""
        self.reactor.set_state(state)

    # ── Mouse Events for Dragging & Clicking ──────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_offset = event.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging:
            new_pos = self.mapToGlobal(event.pos()) - self._drag_offset
            self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            # Only emit "clicked" if the user didn't drag (small movement threshold)
            delta = (event.pos() - self._drag_offset)
            if abs(delta.x()) < 5 and abs(delta.y()) < 5:
                self.clicked.emit()
            event.accept()
