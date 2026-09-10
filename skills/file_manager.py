import subprocess
import os
from pathlib import Path
from typing import Optional, List

# Global state to hold the queued file path for the current response
_queued_file: Optional[str] = None

def get_queued_file() -> Optional[str]:
    """Retrieve and clear the currently queued file for mobile download."""
    global _queued_file
    f = _queued_file
    _queued_file = None  # Clear after reading
    return f

def queue_file_for_transfer(file_path: str) -> bool:
    """Explicitly queue a file path to be sent to the mobile client."""
    global _queued_file
    if os.path.exists(file_path) and os.path.isfile(file_path):
        _queued_file = os.path.abspath(file_path)
        return True
    return False

def _score_path(path_str: str) -> int:
    """Prioritize user folders over system / build caches."""
    lower = path_str.lower()
    if "/library/" in lower or "/caches/" in lower or "/site-packages/" in lower or ".git" in lower:
        return -100
    score = 0
    if "/desktop/" in lower:
        score += 50
    elif "/downloads/" in lower:
        score += 40
    elif "/documents/" in lower:
        score += 30
    elif "jarvis" in lower:
        score += 20
    return score

def search_and_send_file(filename: str) -> str:
    """Search for a file on the Mac by name and queue it to be sent to the user's mobile device."""
    global _queued_file
    filename = filename.strip().strip("'\"").strip()
    if not filename:
        return "Please specify the name of the file you would like me to find and send, Sir."

    valid_paths: List[str] = []

    # 1. Use macOS Spotlight mdfind first
    try:
        result = subprocess.run(["mdfind", "-name", filename], capture_output=True, text=True, timeout=5)
        raw_paths = [p.strip() for p in result.stdout.strip().split('\n') if p.strip()]
        valid_paths = [p for p in raw_paths if os.path.isfile(p)]
    except Exception:
        valid_paths = []

    # 2. Filesystem direct search fallback in common user directories
    if not valid_paths:
        search_roots = [
            Path.home() / "Desktop",
            Path.home() / "Downloads",
            Path.home() / "Documents",
            Path.home() / "Pictures",
            Path(os.getcwd())
        ]
        target_lower = filename.lower()
        for root in search_roots:
            if not root.exists():
                continue
            try:
                for entry in root.rglob("*"):
                    # Avoid traversing deeply into hidden or heavy directories
                    if any(part.startswith('.') for part in entry.parts):
                        continue
                    if entry.is_file():
                        if entry.name.lower() == target_lower or target_lower in entry.name.lower():
                            valid_paths.append(str(entry.resolve()))
                            if len(valid_paths) >= 10:
                                break
            except Exception:
                continue

    if not valid_paths:
        return f"I couldn't find any file named '{filename}', Sir. Please ensure it exists on your Mac."

    # Sort paths by priority (Desktop/Downloads first, then newest modified time)
    def sort_key(p: str):
        p_score = _score_path(p)
        try:
            mtime = os.path.getmtime(p)
        except Exception:
            mtime = 0
        return (p_score, mtime)

    valid_paths.sort(key=sort_key, reverse=True)
    best_match = valid_paths[0]

    # Queue the file for mobile download
    _queued_file = best_match

    file_size_bytes = 0
    try:
        file_size_bytes = os.path.getsize(best_match)
        if file_size_bytes < 1024:
            size_str = f"{file_size_bytes} B"
        elif file_size_bytes < 1024 * 1024:
            size_str = f"{file_size_bytes / 1024:.1f} KB"
        else:
            size_str = f"{file_size_bytes / (1024 * 1024):.1f} MB"
    except Exception:
        size_str = "unknown size"

    return (
        f"I found '{os.path.basename(best_match)}' ({size_str}) at `{best_match}`. "
        f"I have dispatched it to your mobile device for download, Sir."
    )

FILE_TOOLS = [
    {
        "name": "search_and_send_file",
        "description": "Searches for a file by name on the Mac and sends it securely to the user's mobile device. Use this whenever the user asks to send, transfer, or get a file on mobile.",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "The name or partial name of the file to search for and send."
                }
            },
            "required": ["filename"]
        },
        "function": search_and_send_file
    }
]
