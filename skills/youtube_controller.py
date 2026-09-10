# Jarvis AI — YouTube Controller
# Controls YouTube playback directly in the user's running browser tab (Brave, Chrome, Safari, Edge, Arc).
# Supports in-tab playback, forward/rewind, play/pause, ad-skipping, and volume WITHOUT opening new tabs or browsers.

import subprocess
import threading
import time
import urllib.parse
from typing import Optional, Tuple

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False


# ── Helper functions ──────────────────────────────────────────

def _run_applescript(script: str) -> Tuple[bool, str]:
    """Execute an AppleScript snippet and return (success, output)."""
    try:
        proc = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=8
        )
        if proc.returncode == 0:
            return True, proc.stdout.strip()
        return False, proc.stderr.strip()
    except Exception as e:
        return False, str(e)


def _find_and_focus_youtube_tab() -> Tuple[bool, str, str]:
    """
    Search all running browsers (Brave, Chrome, Safari, Edge, Arc) for an open YouTube tab.
    If found, brings that tab to the foreground in its window and activates the browser.
    Returns (found, browser_app_name, tab_title).
    NEVER opens a new browser window or creates new tabs.
    """
    script = '''
    on findYT()
        set foundApp to ""
        set foundTitle to ""
        
        -- 1. Check Brave Browser
        try
            tell application "System Events"
                if (count of (processes whose name is "Brave Browser")) > 0 then
                    tell application "Brave Browser"
                        repeat with w in windows
                            set tIdx to 1
                            repeat with t in tabs of w
                                set u to (URL of t as text)
                                set tit to (title of t as text)
                                if (u contains "youtube.com") or (tit contains "YouTube") then
                                    set active tab index of w to tIdx
                                    set index of w to 1
                                    set foundApp to "Brave Browser"
                                    set foundTitle to tit
                                    exit repeat
                                end if
                                set tIdx to tIdx + 1
                            end repeat
                            if foundApp is not "" then exit repeat
                        end repeat
                    end tell
                end if
            end tell
        end try
        
        -- 2. Check Google Chrome
        if foundApp is "" then
            try
                tell application "System Events"
                    if (count of (processes whose name is "Google Chrome")) > 0 then
                        tell application "Google Chrome"
                            repeat with w in windows
                                set tIdx to 1
                                repeat with t in tabs of w
                                    set u to (URL of t as text)
                                    set tit to (title of t as text)
                                    if (u contains "youtube.com") or (tit contains "YouTube") then
                                        set active tab index of w to tIdx
                                        set index of w to 1
                                        set foundApp to "Google Chrome"
                                        set foundTitle to tit
                                        exit repeat
                                    end if
                                    set tIdx to tIdx + 1
                                end repeat
                                if foundApp is not "" then exit repeat
                            end repeat
                        end tell
                    end if
                end tell
            end try
        end if
        
        -- 3. Check Safari
        if foundApp is "" then
            try
                tell application "System Events"
                    if (count of (processes whose name is "Safari")) > 0 then
                        tell application "Safari"
                            repeat with w in windows
                                set tIdx to 1
                                repeat with t in tabs of w
                                    set u to (URL of t as text)
                                    set tit to (name of t as text)
                                    if (u contains "youtube.com") or (tit contains "YouTube") then
                                        set current tab of w to t
                                        set index of w to 1
                                        set foundApp to "Safari"
                                        set foundTitle to tit
                                        exit repeat
                                    end if
                                    set tIdx to tIdx + 1
                                end repeat
                                if foundApp is not "" then exit repeat
                            end repeat
                        end tell
                    end if
                end tell
            end try
        end if
        
        -- 4. Check Microsoft Edge
        if foundApp is "" then
            try
                tell application "System Events"
                    if (count of (processes whose name is "Microsoft Edge")) > 0 then
                        tell application "Microsoft Edge"
                            repeat with w in windows
                                set tIdx to 1
                                repeat with t in tabs of w
                                    set u to (URL of t as text)
                                    set tit to (title of t as text)
                                    if (u contains "youtube.com") or (tit contains "YouTube") then
                                        set active tab index of w to tIdx
                                        set index of w to 1
                                        set foundApp to "Microsoft Edge"
                                        set foundTitle to tit
                                        exit repeat
                                    end if
                                    set tIdx to tIdx + 1
                                end repeat
                                if foundApp is not "" then exit repeat
                            end repeat
                        end tell
                    end if
                end tell
            end try
        end if
        
        -- 5. Check Arc
        if foundApp is "" then
            try
                tell application "System Events"
                    if (count of (processes whose name is "Arc")) > 0 then
                        tell application "Arc"
                            repeat with w in windows
                                set tIdx to 1
                                repeat with t in tabs of w
                                    set u to (URL of t as text)
                                    set tit to (title of t as text)
                                    if (u contains "youtube.com") or (tit contains "YouTube") then
                                        set active tab index of w to tIdx
                                        set index of w to 1
                                        set foundApp to "Arc"
                                        set foundTitle to tit
                                        exit repeat
                                    end if
                                    set tIdx to tIdx + 1
                                end repeat
                                if foundApp is not "" then exit repeat
                            end repeat
                        end tell
                    end if
                end tell
            end try
        end if

        if foundApp is not "" then
            tell application foundApp to activate
            return foundApp & "|||" & foundTitle
        else
            return "NONE"
        end if
    end findYT

    return findYT()
    '''
    success, out = _run_applescript(script)
    if success and out != "NONE" and "|||" in out:
        parts = out.split("|||", 1)
        return True, parts[0].strip(), parts[1].strip()
    return False, "", ""


def _send_keys_to_browser(browser_name: str, keys_script: str):
    """Ensure the target browser is frontmost and send keystrokes."""
    script = f'''
    tell application "{browser_name}" to activate
    delay 0.1
    tell application "System Events"
        tell process "{browser_name}"
            {keys_script}
        end tell
    end tell
    '''
    _run_applescript(script)


# ── YouTube Operations in Current Tab ──────────────────────────

def youtube_forward(seconds: int = 10) -> str:
    """
    Fast-forward the currently playing YouTube video by N seconds in the current tab.
    Uses official YouTube keyboard shortcuts ('l' for 10s, right arrow for 5s).
    """
    found, app_name, title = _find_and_focus_youtube_tab()
    if not found:
        return "No active YouTube tab found in your open browsers, Sir. Please make sure YouTube is open."

    # In YouTube web player:
    # 'l' seeks forward 10s
    # Right arrow (key code 124) seeks forward 5s
    if seconds <= 5:
        key_cmd = 'key code 124'  # Right arrow
    else:
        jumps = max(1, round(seconds / 10))
        key_cmd = 'keystroke "l"\n            delay 0.1\n            ' * (jumps - 1) + 'keystroke "l"'

    _send_keys_to_browser(app_name, key_cmd)
    return f"Forwarded YouTube video by {seconds} seconds in {app_name}."


def youtube_rewind(seconds: int = 10) -> str:
    """
    Rewind the currently playing YouTube video by N seconds in the current tab.
    Uses official YouTube keyboard shortcuts ('j' for 10s, left arrow for 5s).
    """
    found, app_name, title = _find_and_focus_youtube_tab()
    if not found:
        return "No active YouTube tab found in your open browsers, Sir. Please make sure YouTube is open."

    # In YouTube web player:
    # 'j' seeks rewind 10s
    # Left arrow (key code 123) seeks rewind 5s
    if seconds <= 5:
        key_cmd = 'key code 123'  # Left arrow
    else:
        jumps = max(1, round(seconds / 10))
        key_cmd = 'keystroke "j"\n            delay 0.1\n            ' * (jumps - 1) + 'keystroke "j"'

    _send_keys_to_browser(app_name, key_cmd)
    return f"Rewound YouTube video by {seconds} seconds in {app_name}."


def youtube_play_pause() -> str:
    """
    Toggle play/pause on the currently playing YouTube video in the open tab.
    Uses YouTube's official 'k' shortcut.
    """
    found, app_name, title = _find_and_focus_youtube_tab()
    if not found:
        return "No active YouTube tab found in your open browsers, Sir."

    _send_keys_to_browser(app_name, 'keystroke "k"')
    return f"Toggled play/pause on YouTube in {app_name}."


def youtube_fullscreen() -> str:
    """
    Toggle fullscreen mode on the currently open YouTube video.
    Uses YouTube's official 'f' shortcut.
    """
    found, app_name, title = _find_and_focus_youtube_tab()
    if not found:
        return "No active YouTube tab found in your open browsers, Sir."

    _send_keys_to_browser(app_name, 'keystroke "f"')
    return f"Toggled fullscreen on YouTube in {app_name}."


def youtube_next_video() -> str:
    """
    Skip to the next video in the YouTube queue/playlist.
    Uses YouTube's official Shift+N shortcut.
    """
    found, app_name, title = _find_and_focus_youtube_tab()
    if not found:
        return "No active YouTube tab found in your open browsers, Sir."

    _send_keys_to_browser(app_name, 'keystroke "N" using {shift down}')
    return f"Skipped to next video on YouTube in {app_name}."


def youtube_set_volume(level: int) -> str:
    """
    Adjust YouTube player volume.
    Uses 'm' for mute if level == 0, or Up/Down arrows.
    """
    found, app_name, title = _find_and_focus_youtube_tab()
    if not found:
        return "No active YouTube tab found in your open browsers, Sir."

    level_clamped = max(0, min(100, level))
    if level_clamped == 0:
        _send_keys_to_browser(app_name, 'keystroke "m"')
        return f"Muted YouTube in {app_name}."
    elif level_clamped > 60:
        _send_keys_to_browser(app_name, 'key code 126\n            delay 0.05\n            key code 126\n            delay 0.05\n            key code 126')
        return f"Turned volume up on YouTube in {app_name}."
    else:
        _send_keys_to_browser(app_name, 'key code 125\n            delay 0.05\n            key code 125\n            delay 0.05\n            key code 125')
        return f"Turned volume down on YouTube in {app_name}."


def youtube_skip_ad() -> str:
    """
    Skip the ad currently playing on YouTube in the user's active tab.
    Uses YouTube's native Tab+Return skip sequence and video player corner clicks.
    Does NOT open new tabs or new browser windows.
    """
    found, app_name, title = _find_and_focus_youtube_tab()
    if not found:
        return "No active YouTube tab found in your open browsers, Sir."

    # Action 1: YouTube keyboard sequence for Skip Ad (Tab to focus skip button, then Return/Space)
    skip_key_script = '''
    key code 48 -- Tab
    delay 0.1
    key code 36 -- Return
    delay 0.1
    key code 49 -- Space
    '''
    _send_keys_to_browser(app_name, skip_key_script)

    # Action 2: Click the bottom-right corner of the video player where Skip Ad button appears
    if HAS_PYAUTOGUI:
        try:
            bounds_script = f'''
            tell application "System Events"
                tell process "{app_name}"
                    set w to first window
                    set p to position of w
                    set s to size of w
                    return (item 1 of p as text) & "," & (item 2 of p as text) & "," & (item 1 of s as text) & "," & (item 2 of s as text)
                end tell
            end tell
            '''
            b_success, b_out = _run_applescript(bounds_script)
            if b_success and "," in b_out:
                parts = [int(x.strip()) for x in b_out.split(",")]
                wx, wy, ww, wh = parts[0], parts[1], parts[2], parts[3]
                
                # Try clicking the standard YouTube Skip Ad button region:
                # 1. Standard player bottom-right
                pyautogui.click(wx + int(ww * 0.62), wy + int(wh * 0.58))
                time.sleep(0.08)
                # 2. Theater mode / wide player bottom-right
                pyautogui.click(wx + int(ww * 0.85), wy + int(wh * 0.65))
                time.sleep(0.08)
                # 3. Fullscreen bottom-right
                pyautogui.click(wx + int(ww * 0.90), wy + int(wh * 0.88))
        except Exception:
            pass

    return f"Skipped YouTube ad in {app_name}, Sir."


def youtube_search_in_tab(query: str) -> str:
    """
    Search for a video on YouTube within the currently open YouTube tab.
    Reuses the EXACT same tab without opening new tabs.
    If no YouTube tab is open, opens YouTube in the default browser.
    """
    found, app_name, title = _find_and_focus_youtube_tab()
    encoded = urllib.parse.quote_plus(query)
    target_url = f"https://www.youtube.com/results?search_query={encoded}"

    if found:
        # Re-use the existing tab! Focus address bar via Cmd + L, paste URL, hit Return
        script = f'''
        tell application "{app_name}" to activate
        delay 0.1
        tell application "System Events"
            tell process "{app_name}"
                -- Select address bar in the active tab
                keystroke "l" using {{command down}}
                delay 0.2
            end tell
        end tell
        '''
        _run_applescript(script)

        # Set clipboard and paste
        proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        proc.communicate(target_url.encode("utf-8"))

        paste_script = f'''
        tell application "System Events"
            tell process "{app_name}"
                keystroke "v" using {{command down}}
                delay 0.1
                key code 36 -- Return
            end tell
        end tell
        '''
        _run_applescript(paste_script)
        return f"Searching YouTube for '{query}' in your existing {app_name} tab."
    else:
        # Open in default browser
        import webbrowser
        webbrowser.open(target_url)
        return f"Opened YouTube search for '{query}' in your browser."


def youtube_play_first_result() -> str:
    """
    Click and play the first video result in the active YouTube tab.
    """
    found, app_name, title = _find_and_focus_youtube_tab()
    if not found:
        return "No active YouTube tab found in your open browsers, Sir."

    script = '''
    key code 125 -- Down Arrow
    delay 0.2
    key code 36 -- Return
    '''
    _send_keys_to_browser(app_name, script)
    return f"Selecting and playing the first result in {app_name}."


# ── Background Ad Skipper Daemon ──────────────────────────────
_ad_skipper_running = False
_ad_skipper_thread = None


def start_auto_ad_skipper() -> str:
    """Start a background daemon that automatically skips YouTube ads."""
    global _ad_skipper_running, _ad_skipper_thread
    
    if _ad_skipper_running:
        return "Auto ad-skipper is already running."
    
    _ad_skipper_running = True
    
    def _skipper_loop():
        global _ad_skipper_running
        while _ad_skipper_running:
            try:
                # Only check if YouTube tab is currently running
                found, app_name, title = _find_and_focus_youtube_tab()
                if found:
                    # Silently send Tab + Return to catch any skippable ad
                    _send_keys_to_browser(app_name, 'key code 48\ndelay 0.05\nkey code 36')
            except Exception:
                pass
            time.sleep(3)
    
    _ad_skipper_thread = threading.Thread(target=_skipper_loop, daemon=True)
    _ad_skipper_thread.start()
    return "Auto ad-skipper started. I'll skip ads automatically in your current YouTube tab."


def stop_auto_ad_skipper() -> str:
    """Stop the background ad skipper daemon."""
    global _ad_skipper_running
    _ad_skipper_running = False
    return "Auto ad-skipper stopped."


# ── Tool Definitions ──────────────────────────────────────────
YOUTUBE_TOOLS = [
    {
        "name": "youtube_search_in_tab",
        "description": "Search for a video on YouTube within the currently open YouTube tab. If no YouTube tab is open, it opens one. Use this instead of youtube_search when the user wants to search within the same tab.",
        "function": youtube_search_in_tab,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for on YouTube",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "youtube_play_first_result",
        "description": "Click and play the first video from YouTube search results. Use after youtube_search_in_tab.",
        "function": youtube_play_first_result,
        "parameters": {},
    },
    {
        "name": "youtube_play_pause",
        "description": "Toggle play/pause on the currently playing YouTube video.",
        "function": youtube_play_pause,
        "parameters": {},
    },
    {
        "name": "youtube_forward",
        "description": "Fast-forward the YouTube video by a number of seconds.",
        "function": youtube_forward,
        "parameters": {
            "type": "object",
            "properties": {
                "seconds": {
                    "type": "integer",
                    "description": "Number of seconds to skip forward (default: 10)",
                }
            },
            "required": ["seconds"],
        },
    },
    {
        "name": "youtube_rewind",
        "description": "Rewind the YouTube video by a number of seconds.",
        "function": youtube_rewind,
        "parameters": {
            "type": "object",
            "properties": {
                "seconds": {
                    "type": "integer",
                    "description": "Number of seconds to rewind (default: 10)",
                }
            },
            "required": ["seconds"],
        },
    },
    {
        "name": "youtube_skip_ad",
        "description": "Skip the ad currently playing on a YouTube video. Click the 'Skip Ad' button if available.",
        "function": youtube_skip_ad,
        "parameters": {},
    },
    {
        "name": "youtube_fullscreen",
        "description": "Toggle fullscreen mode on the YouTube video player.",
        "function": youtube_fullscreen,
        "parameters": {},
    },
    {
        "name": "youtube_set_volume",
        "description": "Set the volume of the YouTube video player (0 to 100).",
        "function": youtube_set_volume,
        "parameters": {
            "type": "object",
            "properties": {
                "level": {
                    "type": "integer",
                    "description": "Volume level from 0 (mute) to 100 (max)",
                }
            },
            "required": ["level"],
        },
    },
    {
        "name": "youtube_next_video",
        "description": "Skip to the next video in the YouTube queue or playlist.",
        "function": youtube_next_video,
        "parameters": {},
    },
    {
        "name": "start_auto_ad_skipper",
        "description": "Start a background daemon that automatically detects and skips YouTube ads every few seconds. Use when the user says 'skip all ads automatically' or 'auto skip ads'.",
        "function": start_auto_ad_skipper,
        "parameters": {},
    },
    {
        "name": "stop_auto_ad_skipper",
        "description": "Stop the background auto ad-skipper daemon.",
        "function": stop_auto_ad_skipper,
        "parameters": {},
    },
]
