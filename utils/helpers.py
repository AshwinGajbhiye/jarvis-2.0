# Jarvis AI — Shared Utilities
import os
import subprocess
import datetime


def get_greeting() -> str:
    """Return time-appropriate greeting."""
    hour = datetime.datetime.now().hour
    if hour < 12:
        return "Good morning"
    elif hour < 17:
        return "Good afternoon"
    elif hour < 21:
        return "Good evening"
    else:
        return "Good night"


def run_applescript(script: str) -> str:
    """Execute an AppleScript and return the output."""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "AppleScript timed out."
    except Exception as e:
        return f"AppleScript error: {e}"


def run_shell(command: str, timeout: int = 10) -> str:
    """Execute a shell command and return the output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip() or result.stderr.strip()
    except subprocess.TimeoutExpired:
        return "Command timed out."
    except Exception as e:
        return f"Command error: {e}"


def sanitize_for_speech(text: str) -> str:
    """Clean text for TTS output — remove markdown, code blocks, etc."""
    import re

    # Remove markdown bold/italic
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    # Remove code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)
    # Remove special characters that sound weird in TTS
    text = re.sub(r"[#\-\*_~>]", "", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def format_time_ago(timestamp) -> str:
    """Format a datetime as 'X minutes/hours/days ago'."""
    if isinstance(timestamp, str):
        timestamp = datetime.datetime.fromisoformat(timestamp)
    now = datetime.datetime.now(tz=timestamp.tzinfo)
    diff = now - timestamp
    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        mins = int(seconds / 60)
        return f"{mins} minute{'s' if mins != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"


def ensure_dir(path: str):
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)
