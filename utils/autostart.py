"""
macOS Auto-Start / LaunchAgent Management for J.A.R.V.I.S.
Allows Jarvis to launch silently in the background (menu bar daemon) on macOS login.
"""

import os
import sys
import subprocess

PLIST_LABEL = "com.ashwingajbhiye.jarvis"
LAUNCH_AGENTS_DIR = os.path.expanduser("~/Library/LaunchAgents")
PLIST_PATH = os.path.join(LAUNCH_AGENTS_DIR, f"{PLIST_LABEL}.plist")


def get_plist_path() -> str:
    """Return the absolute path to the LaunchAgent plist."""
    return PLIST_PATH


def is_autostart_enabled() -> bool:
    """Check if the LaunchAgent plist exists."""
    return os.path.exists(PLIST_PATH)


def enable_autostart() -> tuple[bool, str]:
    """
    Generate and install a LaunchAgent plist to run Jarvis in minimized mode on login.
    """
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    python_bin = os.path.join(project_dir, "venv", "bin", "python")
    main_py = os.path.join(project_dir, "main.py")

    # Fallback to sys.executable if venv python not found
    if not os.path.exists(python_bin):
        python_bin = sys.executable

    log_dir = os.path.expanduser("~/.jarvis")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "daemon.log")

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{PLIST_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_bin}</string>
        <string>{main_py}</string>
        <string>--minimized</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{project_dir}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>{log_path}</string>
    <key>StandardErrorPath</key>
    <string>{log_path}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>
"""
    try:
        os.makedirs(LAUNCH_AGENTS_DIR, exist_ok=True)
        with open(PLIST_PATH, "w") as f:
            f.write(plist_content)

        # Register with launchctl
        subprocess.run(["launchctl", "unload", PLIST_PATH], capture_output=True, check=False)
        subprocess.run(["launchctl", "load", PLIST_PATH], capture_output=True, check=False)

        return True, f"Auto-start enabled. J.A.R.V.I.S. will start silently on login."
    except Exception as e:
        return False, f"Failed to enable auto-start: {e}"


def disable_autostart() -> tuple[bool, str]:
    """
    Remove the LaunchAgent plist and unregister with launchctl.
    """
    try:
        if os.path.exists(PLIST_PATH):
            subprocess.run(["launchctl", "unload", PLIST_PATH], capture_output=True, check=False)
            os.remove(PLIST_PATH)
        return True, "Auto-start disabled."
    except Exception as e:
        return False, f"Failed to disable auto-start: {e}"


def toggle_autostart() -> tuple[bool, str]:
    """Toggle auto-start on or off."""
    if is_autostart_enabled():
        return disable_autostart()
    else:
        return enable_autostart()
