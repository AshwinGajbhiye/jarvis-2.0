# Jarvis AI — Speech-to-Text
# Uses the SpeechRecognition library with Google Speech Recognition.
# Falls back to keyboard input if microphone is unavailable.

import speech_recognition as sr

from config import Config


class Listener:
    """Speech-to-text engine using Google Speech Recognition."""

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.language = Config.STT_LANGUAGE
        self.timeout = Config.STT_TIMEOUT
        self.phrase_limit = Config.STT_PHRASE_LIMIT
        self.mic_available = self._check_microphone()

        # Adjust recognizer settings for better accuracy
        self.recognizer.energy_threshold = 50
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 1.2

    def _check_microphone(self) -> bool:
        """Check if a microphone is available."""
        try:
            mics = sr.Microphone.list_microphone_names()
            return len(mics) > 0
        except (OSError, AttributeError):
            return False

    def listen(self) -> str | None:
        """
        Listen for voice input and return transcribed text.

        Returns:
            Transcribed text string, or None if nothing was recognized.
        """
        if not self.mic_available:
            return None

        try:
            with sr.Microphone() as source:
                # Adjust for ambient noise (quick calibration)
                self.recognizer.adjust_for_ambient_noise(source, duration=1.0)

                # Listen for speech
                audio = self.recognizer.listen(
                    source,
                    timeout=self.timeout,
                    phrase_time_limit=self.phrase_limit,
                )

            # Recognize using Google Speech Recognition (free)
            text = self.recognizer.recognize_google(
                audio, language=self.language
            )
            return text.strip()

        except sr.WaitTimeoutError:
            print("  ⚠️  [Debug] Microphone timed out waiting for speech.")
            return None
        except sr.UnknownValueError:
            print("  ⚠️  [Debug] Heard audio, but could not understand what was said.")
            return None
        except sr.RequestError as e:
            print(f"  ⚠️  Speech recognition service error: {e}")
            return None
        except OSError as e:
            print(f"  ⚠️  Microphone error: {e}")
            self.mic_available = False
            return None
        except Exception as e:
            print(f"  ⚠️  STT Error: {e}")
            return None


# Module-level convenience
_listener = None


def listen() -> str | None:
    """Listen for voice input using the global listener instance."""
    global _listener
    if _listener is None:
        _listener = Listener()
    return _listener.listen()


def is_mic_available() -> bool:
    """Check if microphone is available."""
    global _listener
    if _listener is None:
        _listener = Listener()
    return _listener.mic_available
