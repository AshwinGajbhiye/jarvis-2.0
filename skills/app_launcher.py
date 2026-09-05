# Jarvis AI — macOS App Launcher Skill
# Controls macOS applications: open, close, switch focus.

import subprocess
import os


# ── App name → actual macOS app name mapping ─────────────────
APP_ALIASES = {
    # Development
    "vs code": "Visual Studio Code",
    "vscode": "Visual Studio Code",
    "code": "Visual Studio Code",
    "visual studio code": "Visual Studio Code",
    "terminal": "Terminal",
    "iterm": "iTerm",
    "xcode": "Xcode",
    "postman": "Postman",
    "docker": "Docker",

    # Browsers
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "brave": "Brave Browser",
    "safari": "Safari",
    "firefox": "Firefox",
    "arc": "Arc",

    # Communication
    "slack": "Slack",
    "discord": "Discord",
    "zoom": "zoom.us",
    "teams": "Microsoft Teams",
    "telegram": "Telegram",
    "whatsapp": "WhatsApp",
    "messages": "Messages",
    "facetime": "FaceTime",

    # Productivity
    "calendar": "Calendar",
    "notes": "Notes",
    "reminders": "Reminders",
    "finder": "Finder",
    "mail": "Mail",
    "pages": "Pages",
    "numbers": "Numbers",
    "keynote": "Keynote",

    # Media
    "spotify": "Spotify",
    "music": "Music",
    "photos": "Photos",
    "vlc": "VLC",
    "quicktime": "QuickTime Player",

    # System
    "settings": "System Settings",
    "system settings": "System Settings",
    "system preferences": "System Settings",
    "activity monitor": "Activity Monitor",
    "calculator": "Calculator",

    # Misc
    "notion": "Notion",
    "figma": "Figma",
    "obsidian": "Obsidian",
}


def _resolve_app_name(name: str) -> str:
    """Resolve a fuzzy app name to the actual macOS app name."""
    name_lower = name.lower().strip()

    # Direct match in aliases
    if name_lower in APP_ALIASES:
        return APP_ALIASES[name_lower]

    # Try to find a partial match
    for alias, real_name in APP_ALIASES.items():
        if alias in name_lower or name_lower in alias:
            return real_name

    # If no match, try the name as-is (user might have given the exact name)
    return name.strip()


def open_app(app_name: str) -> str:
    """
    Open a macOS application.

    Args:
        app_name: Name of the application (can be fuzzy, e.g., 'code', 'chrome')

    Returns:
        Status message
    """
    resolved = _resolve_app_name(app_name)

    try:
        result = subprocess.run(
            ["open", "-a", resolved],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            return f"Opening {resolved}."
        else:
            # Try with the original name
            result2 = subprocess.run(
                ["open", "-a", app_name],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result2.returncode == 0:
                return f"Opening {app_name}."
            return f"Could not find application '{app_name}'. Make sure it's installed."

    except subprocess.TimeoutExpired:
        return f"Timed out trying to open {resolved}."
    except Exception as e:
        return f"Error opening {resolved}: {e}"


def close_app(app_name: str) -> str:
    """
    Close a macOS application gracefully.

    Args:
        app_name: Name of the application to close
    """
    resolved = _resolve_app_name(app_name)

    try:
        script = f'tell application "{resolved}" to quit'
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            return f"Closed {resolved}."
        else:
            return f"Could not close {resolved}. It may not be running."

    except subprocess.TimeoutExpired:
        return f"Timed out trying to close {resolved}."
    except Exception as e:
        return f"Error closing {resolved}: {e}"


def focus_app(app_name: str) -> str:
    """
    Bring an application to the foreground.

    Args:
        app_name: Name of the application to focus
    """
    resolved = _resolve_app_name(app_name)

    try:
        script = f'tell application "{resolved}" to activate'
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            return f"Switched to {resolved}."
        else:
            return f"Could not focus {resolved}. It may not be running."

    except Exception as e:
        return f"Error focusing {resolved}: {e}"


def list_running_apps() -> str:
    """List currently running applications."""
    try:
        script = '''
        tell application "System Events"
            set appList to name of every application process whose background only is false
        end tell
        return appList
        '''
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10,
        )
        apps = result.stdout.strip()
        return f"Running applications: {apps}"
    except Exception as e:
        return f"Error listing apps: {e}"


def open_file_in_app(filepath: str, app_name: str = "") -> str:
    """Open a file, optionally with a specific application."""
    try:
        if app_name:
            resolved = _resolve_app_name(app_name)
            cmd = ["open", "-a", resolved, filepath]
        else:
            cmd = ["open", filepath]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            return f"Opened {os.path.basename(filepath)}."
        return f"Could not open {filepath}."
    except Exception as e:
        return f"Error opening file: {e}"


# ── Tool definitions for Gemini function calling ─────────────
APP_TOOLS = [
    {
        "name": "open_app",
        "description": (
            "Open a macOS application. Supports common apps like VS Code, Chrome, "
            "Brave, Calendar, Terminal, Spotify, Slack, Finder, etc. "
            "Use fuzzy names like 'code' for VS Code or 'chrome' for Google Chrome."
        ),
        "function": open_app,
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Name of the application to open (e.g., 'vs code', 'chrome', 'brave', 'calendar', 'spotify')",
                }
            },
            "required": ["app_name"],
        },
    },
    {
        "name": "close_app",
        "description": "Close/quit a running macOS application.",
        "function": close_app,
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Name of the application to close",
                }
            },
            "required": ["app_name"],
        },
    },
    {
        "name": "focus_app",
        "description": "Bring a running application to the foreground / switch to it.",
        "function": focus_app,
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Name of the application to focus",
                }
            },
            "required": ["app_name"],
        },
    },
    {
        "name": "list_running_apps",
        "description": "List all currently running applications on the Mac.",
        "function": list_running_apps,
        "parameters": {},
    },
]
