"""
Meeting & Lecture Audio Recorder for J.A.R.V.I.S.
Records audio in the background using PyAudio, saving high-fidelity
16kHz audio for Gemini Multimodal Audio analysis.
"""

import os
import time
import wave
import threading
import datetime
from typing import Optional, Tuple
import pyaudio

from config import Config

RECORDINGS_DIR = os.path.expanduser("~/.jarvis/recordings")


class MeetingRecorder:
    """
    Background audio recorder for meetings, lectures, and calls.
    """
    def __init__(self, sample_rate: int = 16000, channels: int = 1, chunk: int = 1024):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk = chunk
        
        self._pyaudio: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None
        self._thread: Optional[threading.Thread] = None
        
        self._is_recording = False
        self._start_time = 0.0
        self._current_title = "Meeting / Class"
        self._output_path = ""
        self._frames = []
        self._lock = threading.Lock()

    def is_recording(self) -> bool:
        """Check if currently recording."""
        with self._lock:
            return self._is_recording

    def get_title(self) -> str:
        """Get the title/label of the active recording."""
        with self._lock:
            return self._current_title

    def get_elapsed_seconds(self) -> int:
        """Get duration in seconds of the current recording session."""
        with self._lock:
            if not self._is_recording:
                return 0
            return int(time.time() - self._start_time)

    def start(self, title: str = "Class / Meeting") -> Tuple[bool, str]:
        """
        Start recording in a background thread.
        """
        with self._lock:
            if self._is_recording:
                return False, f"Already recording '{self._current_title}' ({self.get_elapsed_seconds()}s elapsed)."

            os.makedirs(RECORDINGS_DIR, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self._output_path = os.path.join(RECORDINGS_DIR, f"meeting_{timestamp}.wav")
            self._current_title = title.strip() or "Class / Meeting"
            self._frames = []
            self._start_time = time.time()
            self._is_recording = True

            try:
                self._pyaudio = pyaudio.PyAudio()
                self._stream = self._pyaudio.open(
                    format=pyaudio.paInt16,
                    channels=self.channels,
                    rate=self.sample_rate,
                    input=True,
                    frames_per_buffer=self.chunk
                )
            except Exception as e:
                self._is_recording = False
                if self._pyaudio:
                    self._pyaudio.terminate()
                    self._pyaudio = None
                return False, f"Could not access microphone: {e}"

            self._thread = threading.Thread(target=self._record_loop, daemon=True)
            self._thread.start()
            return True, f"Started recording '{self._current_title}'."

    def _record_loop(self):
        """Audio streaming loop in background thread."""
        while True:
            with self._lock:
                if not self._is_recording or self._stream is None:
                    break

            try:
                data = self._stream.read(self.chunk, exception_on_overflow=False)
                with self._lock:
                    self._frames.append(data)
            except Exception as e:
                print(f"  ⚠️ Audio recording buffer error: {e}")
                time.sleep(0.01)

    def stop(self) -> Tuple[Optional[str], float, str]:
        """
        Stop recording, write the wave file, and clean up audio resources.
        
        Returns:
            Tuple of (output_file_path, duration_seconds, title)
        """
        with self._lock:
            if not self._is_recording:
                return None, 0.0, "No active recording"

            self._is_recording = False
            duration = max(0.1, time.time() - self._start_time)
            title = self._current_title
            out_path = self._output_path

        # Wait briefly for thread to exit
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

        with self._lock:
            # Close audio stream
            if self._stream:
                try:
                    self._stream.stop_stream()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None

            if self._pyaudio:
                try:
                    self._pyaudio.terminate()
                except Exception:
                    pass
                self._pyaudio = None

            # Write WAV file
            if self._frames:
                try:
                    wf = wave.open(out_path, 'wb')
                    wf.setnchannels(self.channels)
                    wf.setsampwidth(2)  # 16-bit = 2 bytes
                    wf.setframerate(self.sample_rate)
                    wf.writeframes(b''.join(self._frames))
                    wf.close()
                    print(f"  💾 Saved meeting recording to: {out_path} ({duration:.1f}s)")
                except Exception as e:
                    print(f"  ❌ Error saving WAV recording: {e}")
                    return None, duration, title
            else:
                return None, 0.0, title

            self._frames = []
            return out_path, duration, title


# Global Singleton Instance
_recorder_instance = MeetingRecorder()

def get_meeting_recorder() -> MeetingRecorder:
    """Get the global meeting recorder instance."""
    return _recorder_instance
