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
            # - <alt>+<space>: Option + Space (⌥Space - Raycast/Alfred style)
            # - <cmd>+<shift>+j: Cmd + Shift + J (⌘⇧J - Zero conflict with Spotlight)
            # - <cmd>+<shift>+<space>: Cmd + Shift + Space (⌘⇧Space)
            # - <cmd>+<alt>+j: Cmd + Option + J (⌘⌥J)
            hotkeys = {
                '<alt>+<space>': self._on_hotkey_activated,
                '<cmd>+<shift>+j': self._on_hotkey_activated,
                '<cmd>+<shift>+<space>': self._on_hotkey_activated,
                '<cmd>+<alt>+j': self._on_hotkey_activated,
            }

            self._listener = keyboard.GlobalHotKeys(hotkeys)
            self._listener.daemon = True
            self._listener.start()
            self._running = True
            print("  ⌨️  Global hotkeys registered: Option+Space (⌥Space) & Cmd+Shift+J (⌘⇧J)")

        except Exception as e:
            self._has_accessibility = False
            print(f"  ⚠️  Global hotkey registration warning: {e}")
            print("  ℹ️  If hotkeys do not trigger, ensure Accessibility permissions are granted in:")
            print("      System Settings -> Privacy & Security -> Accessibility")

    def _on_hotkey_activated(self):
        """Called by pynput on its listener thread when the hotkey is pressed."""
        # Qt's queued signal emission safely routes this to the main GUI thread
        self.hotkey_triggered.emit()

    def stop(self):
        """Stop listening for global hotkeys."""
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
            self._running = False
