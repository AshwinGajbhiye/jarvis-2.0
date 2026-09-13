"""
Screen Snippet Question Capturer for J.A.R.V.I.S. Stealth Copilot.
Allows the user to drag a selection rectangle over Friend 1's shared screen
to capture and solve visual questions (q1, q2, q3) in real time.
"""

import os
import subprocess
import tempfile
from PyQt6.QtCore import QThread, pyqtSignal


class ScreenSnipperWorker(QThread):
    """
    Background worker that runs macOS native interactive selection screencapture:
    screencapture -i -s -x <target_path>
      -i: interactive selection mode (crosshair marquee)
      -s: only allow mouse selection mode
      -x: silent mode (no shutter sound)
    """
    snippet_captured = pyqtSignal(str)   # Emits absolute path to snippet image
    snippet_cancelled = pyqtSignal()
    snippet_error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.output_path = os.path.join(tempfile.gettempdir(), "jarvis_meet_question.png")

    def run(self):
        # Remove any existing snippet file
        if os.path.exists(self.output_path):
            try:
                os.remove(self.output_path)
            except Exception:
                pass

        try:
            # Launch macOS screencapture interactive selection
            result = subprocess.run(
                ["screencapture", "-i", "-s", "-x", self.output_path],
                capture_output=True,
                timeout=30
            )

            # Check if file was captured and has size > 100 bytes
            if os.path.exists(self.output_path) and os.path.getsize(self.output_path) > 100:
                self.snippet_captured.emit(self.output_path)
            else:
                # User pressed Escape or clicked without dragging
                self.snippet_cancelled.emit()

        except subprocess.TimeoutExpired:
            self.snippet_cancelled.emit()
        except Exception as e:
            self.snippet_error.emit(str(e))
