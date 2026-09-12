"""
Hotkey Manager for J.A.R.V.I.S.
Provides system-wide global hotkey listening using pynput,
forwarding triggers thread-safely to PyQt6 signals.
"""

import sys
import threading
from PyQt6.QtCore import QObject, pyqtSignal


class HotkeyManager(QObject):
    """
    Global Hotkey Manager.
    Listens for system-wide key combinations (e.g. Option+Space)
    and emits a Qt signal to toggle the floating launcher.
    """
    hotkey_triggered = pyqtSignal()
    meeting_hotkey_triggered = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._listener = None
        self._running = False
        self._has_accessibility = True

    def start(self):
        """Start the background hotkey listener."""
        if self._running:
            return

        try:
            from pynput import keyboard

            # Supported hotkeys:
            # - Launcher: Option+Space (⌥Space), Cmd+Shift+J (⌘⇧J), Cmd+Option+J (⌘⌥J)
            # - Meeting Auto-Notes: Option+R (⌥R), Cmd+Shift+M (⌘⇧M)
            hotkeys = {
                '<alt>+<space>': self._on_hotkey_activated,
                '<cmd>+<shift>+j': self._on_hotkey_activated,
                '<cmd>+<shift>+<space>': self._on_hotkey_activated,
                '<cmd>+<alt>+j': self._on_hotkey_activated,
                '<alt>+r': self._on_meeting_hotkey_activated,
                '<cmd>+<shift>+m': self._on_meeting_hotkey_activated,
            }

            self._listener = keyboard.GlobalHotKeys(hotkeys)
            self._listener.daemon = True
            self._listener.start()
            self._running = True
            print("  ⌨️  Global hotkeys registered:")
            print("      • ⌥Space or ⌘⇧J: Quick Launcher")
            print("      • ⌥R or ⌘⇧M: Toggle Meeting / Class Auto-Notes")

        except Exception as e:
            self._has_accessibility = False
            print(f"  ⚠️  Global hotkey registration warning: {e}")
            print("  ℹ️  If hotkeys do not trigger, ensure Accessibility permissions are granted in:")
            print("      System Settings -> Privacy & Security -> Accessibility")

    def _on_hotkey_activated(self):
        """Called by pynput on its listener thread when the launcher hotkey is pressed."""
        self.hotkey_triggered.emit()

    def _on_meeting_hotkey_activated(self):
        """Called by pynput on its listener thread when the meeting hotkey is pressed."""
        self.meeting_hotkey_triggered.emit()

    def stop(self):
        """Stop listening for global hotkeys."""
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
            self._running = False
