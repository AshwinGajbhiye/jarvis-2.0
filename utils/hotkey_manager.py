"""
Hotkey Manager for J.A.R.V.I.S.
Provides system-wide global hotkey listening using pynput,
forwarding triggers thread-safely to PyQt6 signals.

On macOS, also registers a fallback NSEvent global monitor
that works reliably in fullscreen Spaces where pynput can
sometimes fail silently.
"""

import sys
import time
import threading
from PyQt6.QtCore import QObject, pyqtSignal


class HotkeyManager(QObject):
    """
    Global Hotkey Manager.
    Listens for system-wide key combinations (e.g. Option+Space)
    and emits a Qt signal to toggle the floating launcher.

    Uses two layers on macOS:
      1. pynput.GlobalHotKeys (primary, works on most desktops)
      2. NSEvent.addGlobalMonitorForEventsMatchingMask (fallback,
         reliable in fullscreen Spaces)
    """
    hotkey_triggered = pyqtSignal()
    meeting_hotkey_triggered = pyqtSignal()
    stealth_toggle_triggered = pyqtSignal()
    stealth_answer_triggered = pyqtSignal()
    stealth_snip_triggered = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._listener = None
        self._running = False
        self._has_accessibility = True
        self._ns_monitor = None
        # Debounce: prevent double-firing from both pynput + NSEvent
        self._last_fire = {}

    def start(self):
        """Start the background hotkey listener."""
        if self._running:
            return

        try:
            from pynput import keyboard

            # Supported hotkeys:
            # - Launcher: Option+Space (⌥Space), Cmd+Shift+J (⌘⇧J), Cmd+Option+J (⌘⌥J)
            # - Meeting Auto-Notes: Option+R (⌥R), Cmd+Shift+M (⌘⇧M)
            # - Stealth Copilot (Invisible to Screen Share): Option+S (⌥S), Cmd+Shift+S (⌘⇧S)
            # - Instant Question Answering: Option+A (⌥A), Cmd+Shift+A (⌘⇧A)
            # - Screen Snippet Question Solver: Option+O (⌥O), Cmd+Shift+O (⌘⇧O)
            hotkeys = {
                '<alt>+<space>': self._on_hotkey_activated,
                '<cmd>+<shift>+j': self._on_hotkey_activated,
                '<cmd>+<shift>+<space>': self._on_hotkey_activated,
                '<cmd>+<alt>+j': self._on_hotkey_activated,
                '<alt>+r': self._on_meeting_hotkey_activated,
                '<cmd>+<shift>+m': self._on_meeting_hotkey_activated,
                '<alt>+s': self._on_stealth_toggle_activated,
                '<cmd>+<shift>+s': self._on_stealth_toggle_activated,
                '<alt>+a': self._on_stealth_answer_activated,
                '<cmd>+<shift>+a': self._on_stealth_answer_activated,
                '<alt>+o': self._on_stealth_snip_activated,
                '<cmd>+<shift>+o': self._on_stealth_snip_activated,
            }

            self._listener = keyboard.GlobalHotKeys(hotkeys)
            self._listener.daemon = True
            self._listener.start()
            self._running = True
            print("  ⌨️  Global hotkeys registered (pynput):")
            print("      • ⌥Space or ⌘⇧J: Quick Launcher")
            print("      • ⌥R or ⌘⇧M: Toggle Meeting Auto-Notes")
            print("      • ⌥S or ⌘⇧S: Toggle Stealth Copilot (Screen-Invisible)")
            print("      • ⌥A or ⌘⇧A: Quick Answer Friend's Question")
            print("      • ⌥O or ⌘⇧O: Screen Snippet Question Solver")

        except Exception as e:
            self._has_accessibility = False
            print(f"  ⚠️  Global hotkey registration warning: {e}")
            print("  ℹ️  If hotkeys do not trigger, ensure Accessibility permissions are granted in:")
            print("      System Settings -> Privacy & Security -> Accessibility")

        # ── macOS Fallback: NSEvent Global Monitor ─────────────
        # pynput's GlobalHotKeys can silently fail in fullscreen Spaces.
        # NSEvent.addGlobalMonitorForEventsMatchingMask works at the Cocoa
        # event level and is reliable across ALL Spaces including fullscreen.
        if sys.platform == "darwin":
            self._start_nsevent_monitor()

    def _start_nsevent_monitor(self):
        """Register a macOS NSEvent global monitor for Option+key hotkeys."""
        try:
            from AppKit import NSEvent, NSKeyDownMask, NSAlternateKeyMask, NSCommandKeyMask, NSShiftKeyMask

            def _handle_global_key(event):
                """Handle global key events at the Cocoa level."""
                try:
                    flags = event.modifierFlags()
                    chars = event.charactersIgnoringModifiers()
                    if not chars:
                        return

                    key = chars.lower()
                    has_alt = bool(flags & NSAlternateKeyMask)
                    has_cmd = bool(flags & NSCommandKeyMask)
                    has_shift = bool(flags & NSShiftKeyMask)

                    # Option+key combinations
                    if has_alt and not has_cmd:
                        if key == 'a':
                            self._debounced_emit('stealth_answer', self.stealth_answer_triggered)
                        elif key == 's':
                            self._debounced_emit('stealth_toggle', self.stealth_toggle_triggered)
                        elif key == 'r':
                            self._debounced_emit('meeting', self.meeting_hotkey_triggered)
                        elif key == 'o':
                            self._debounced_emit('stealth_snip', self.stealth_snip_triggered)
                        elif key == ' ':
                            self._debounced_emit('launcher', self.hotkey_triggered)

                    # Cmd+Shift+key combinations
                    elif has_cmd and has_shift:
                        if key == 'a':
                            self._debounced_emit('stealth_answer', self.stealth_answer_triggered)
                        elif key == 's':
                            self._debounced_emit('stealth_toggle', self.stealth_toggle_triggered)
                        elif key == 'j':
                            self._debounced_emit('launcher', self.hotkey_triggered)
                        elif key == 'm':
                            self._debounced_emit('meeting', self.meeting_hotkey_triggered)
                        elif key == 'o':
                            self._debounced_emit('stealth_snip', self.stealth_snip_triggered)

                except Exception:
                    pass  # Never crash the event handler

            # NSKeyDownMask = 1 << 10 = 1024
            self._ns_monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
                NSKeyDownMask, _handle_global_key
            )
            if self._ns_monitor:
                print("  🛡️  NSEvent fallback hotkey monitor active (fullscreen-safe)")

        except ImportError:
            print("  ℹ️  PyObjC not available — NSEvent fallback hotkeys disabled")
        except Exception as e:
            print(f"  ⚠️  NSEvent monitor setup warning: {e}")

    def _debounced_emit(self, name: str, signal):
        """Emit a signal with debouncing to prevent double-fires from pynput + NSEvent."""
        now = time.time()
        last = self._last_fire.get(name, 0)
        if now - last < 0.5:  # 500ms debounce window
            return
        self._last_fire[name] = now
        signal.emit()

    def _on_hotkey_activated(self):
        """Called by pynput on its listener thread when the launcher hotkey is pressed."""
        self._debounced_emit('launcher', self.hotkey_triggered)

    def _on_meeting_hotkey_activated(self):
        """Called by pynput on its listener thread when the meeting hotkey is pressed."""
        self._debounced_emit('meeting', self.meeting_hotkey_triggered)

    def _on_stealth_toggle_activated(self):
        """Called when the stealth HUD toggle hotkey (⌥S) is pressed."""
        self._debounced_emit('stealth_toggle', self.stealth_toggle_triggered)

    def _on_stealth_answer_activated(self):
        """Called when the stealth answer hotkey (⌥A) is pressed."""
        self._debounced_emit('stealth_answer', self.stealth_answer_triggered)

    def _on_stealth_snip_activated(self):
        """Called when the screen snippet hotkey (⌥O) is pressed."""
        self._debounced_emit('stealth_snip', self.stealth_snip_triggered)

    def stop(self):
        """Stop listening for global hotkeys."""
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
            self._running = False

        # Remove NSEvent monitor
        if self._ns_monitor and sys.platform == "darwin":
            try:
                from AppKit import NSEvent
                NSEvent.removeMonitor_(self._ns_monitor)
            except Exception:
                pass
            self._ns_monitor = None

