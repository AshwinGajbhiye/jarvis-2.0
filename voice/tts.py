# Jarvis AI — Text-to-Speech (macOS Native)
# Uses the built-in macOS `say` command with the "Daniel" voice
# for that authentic British Jarvis feel.

import subprocess
import threading
import os
import signal

from config import Config


class Speaker:
    """macOS native text-to-speech engine."""

    def __init__(self):
        self.voice = Config.JARVIS_VOICE
        self.rate = Config.JARVIS_SPEECH_RATE
        self._current_process = None
        self._lock = threading.Lock()

    def speak(self, text: str, block: bool = True):
        """
        Speak the given text aloud.

        Args:
            text: The text to speak
            block: If True, wait for speech to finish. If False, speak in background.
        """
        if not text or not text.strip():
            return

        # Clean the text for speech
        text = self._clean_for_speech(text)

        if block:
            self._speak_sync(text)
        else:
            thread = threading.Thread(target=self._speak_sync, args=(text,), daemon=True)
            thread.start()

    def _speak_sync(self, text: str):
        """Synchronous speech — blocks until done."""
        self.stop()  # Stop any currently playing speech

        with self._lock:
            try:
                self._current_process = subprocess.Popen(
                    ["say", "-v", self.voice, "-r", str(self.rate), text],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self._current_process.wait()
            except Exception as e:
                print(f"  ⚠️  TTS Error: {e}")
            finally:
                self._current_process = None

    def stop(self):
        """Stop any currently playing speech."""
        if self._current_process and self._current_process.poll() is None:
            try:
                self._current_process.terminate()
                self._current_process.wait(timeout=1)
            except Exception:
                try:
                    self._current_process.kill()
                except Exception:
                    pass

    def _clean_for_speech(self, text: str) -> str:
        """Clean text for natural TTS output."""
        import re

        # Remove markdown formatting
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\*(.+?)\*", r"\1", text)
        text = re.sub(r"```[\s\S]*?```", "", text)
        text = re.sub(r"`(.+?)`", r"\1", text)

        # Remove URLs — they sound terrible spoken aloud
        text = re.sub(r"https?://\S+", "a link", text)

        # Remove emoji-style characters
        text = re.sub(r"[🤖🎤🔊⚡📧🔍📅✅❌⚠️🧠🗣️🌐💼]", "", text)

        # Remove markdown headers and bullets
        text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.MULTILINE)

        # Help macOS pronounce "AI" properly instead of just saying "I"
        text = re.sub(r"\bAI\b", "A.I.", text)

        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # Add a tiny bit of padding to prevent audio clipping at start/end
        text = f" {text} "

        # Limit length for TTS — don't speak novels (increased to 1000)
        if len(text) > 1000:
            text = text[:997] + "..."

        return text

    @staticmethod
    def list_voices() -> list[str]:
        """List all available macOS voices."""
        try:
            result = subprocess.run(
                ["say", "-v", "?"],
                capture_output=True,
                text=True,
            )
            voices = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    voice_name = line.split()[0]
                    voices.append(voice_name)
            return voices
        except Exception:
            return ["Daniel", "Samantha", "Alex"]


# Module-level convenience function
_speaker = None


def speak(text: str, block: bool = True):
    """Speak text using the global speaker instance."""
    global _speaker
    if _speaker is None:
        _speaker = Speaker()
    _speaker.speak(text, block=block)


def stop_speaking():
    """Stop any current speech."""
    global _speaker
    if _speaker:
        _speaker.stop()
