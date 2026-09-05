# Jarvis AI — Conversation Memory
# Maintains conversation history for context-aware responses.
# Persists conversations to disk for continuity across sessions.

import json
import os
import datetime

from config import Config
from utils.helpers import ensure_dir


class Memory:
    """Manages conversation history for Jarvis."""

    def __init__(self):
        self.history: list[dict] = []
        self.max_history = Config.MAX_CONVERSATION_HISTORY
        self.history_dir = Config.HISTORY_DIR
        ensure_dir(self.history_dir)

        # Load previous session if it exists
        self._load_latest_session()

    def add(self, role: str, content: str):
        """
        Add a message to the conversation history.

        Args:
            role: 'user' or 'model' (Gemini convention)
            content: The message text
        """
        self.history.append({
            "role": role,
            "parts": [{"text": content}],
        })

        # Trim history if it exceeds the limit
        if len(self.history) > self.max_history:
            # Keep the first message (system context) and trim the rest
            self.history = self.history[-self.max_history:]

        # Auto-save periodically
        if len(self.history) % 5 == 0:
            self._save_session()

    def get_history(self) -> list[dict]:
        """Return the current conversation history for Gemini API."""
        return self.history.copy()

    def get_last_n(self, n: int = 5) -> list[dict]:
        """Get the last N messages."""
        return self.history[-n:] if self.history else []

    def clear(self):
        """Clear conversation history."""
        self.history = []
        self._save_session()

    def get_context_summary(self) -> str:
        """Get a brief summary of recent conversation for context."""
        if not self.history:
            return "No previous conversation."

        recent = self.history[-6:]  # Last 3 exchanges
        lines = []
        for msg in recent:
            role = "User" if msg["role"] == "user" else "Jarvis"
            text = msg["parts"][0]["text"][:100]  # Truncate long messages
            lines.append(f"{role}: {text}")
        return "\n".join(lines)

    def _save_session(self):
        """Save current session to disk."""
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
            filepath = os.path.join(self.history_dir, f"session_{timestamp}.json")
            with open(filepath, "w") as f:
                json.dump(
                    {
                        "timestamp": datetime.datetime.now().isoformat(),
                        "messages": self.history,
                    },
                    f,
                    indent=2,
                )
        except Exception as e:
            print(f"  ⚠️  Failed to save session: {e}")

    def _load_latest_session(self):
        """Load the most recent session from today, if available."""
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
            filepath = os.path.join(self.history_dir, f"session_{timestamp}.json")
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    data = json.load(f)
                    self.history = data.get("messages", [])
        except Exception:
            self.history = []

    def __len__(self):
        return len(self.history)
