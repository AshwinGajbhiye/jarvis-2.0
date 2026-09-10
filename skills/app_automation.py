# Jarvis AI — Local App Automation Skill
# Controls and interacts with local macOS applications via AppleScript and pyautogui.
# Supports typing text, hotkeys, Apple Music search/playback, and Antigravity IDE typing.

import subprocess
import time
import os

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False


# ── Helper functions ──────────────────────────────────────────

def _run_applescript(script: str) -> tuple[bool, str]:
    """Execute an AppleScript snippet and return (success, output)."""
    try:
        proc = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10
        )
        if proc.returncode == 0:
            return True, proc.stdout.strip()
        return False, proc.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "AppleScript execution timed out"
    except Exception as e:
        return False, str(e)


def _escape_applescript_string(s: str) -> str:
    """Escape quotes and backslashes for AppleScript string literals."""
    return s.replace('\\', '\\\\').replace('"', '\\"')


# ── Core App Automation Functions ─────────────────────────────

def get_active_app_info() -> str:
    """Get the name and window title of the currently focused macOS application."""
    script = '''
    tell application "System Events"
        set frontApp to name of first application process whose frontmost is true
        set frontWindow to ""
        try
            tell process frontApp
                set frontWindow to name of front window
            end tell
        end try
        return frontApp & "|||" & frontWindow
    end tell
    '''
    success, out = _run_applescript(script)
    if success and "|||" in out:
        parts = out.split("|||", 1)
        app_name = parts[0].strip()
        win_title = parts[1].strip() if len(parts) > 1 else ""
        if win_title:
            return f"Active App: {app_name} (Window: '{win_title}')"
        return f"Active App: {app_name}"
    return f"Could not determine active app: {out}"


def app_type_text(app_name: str, text: str, clear_first: bool = False, press_enter: bool = False) -> str:
    """
    Bring an application to the foreground and type text into its active input field.
    
    Args:
        app_name: Name of the application (e.g., 'Music', 'Antigravity', 'Notes', 'Visual Studio Code', 'Slack')
        text: The text to type
        clear_first: If True, selects all existing text and deletes it before typing
        press_enter: If True, presses Enter after typing
    """
    clean_app = _escape_applescript_string(app_name)
    clean_text = _escape_applescript_string(text)
    
    script_lines = [
        f'tell application "{clean_app}" to activate',
        'delay 0.3',
        'tell application "System Events"',
    ]
    
    if clear_first:
        script_lines.extend([
            '    keystroke "a" using {command down}',
            '    delay 0.1',
            '    key code 51',  # Delete / Backspace
            '    delay 0.1',
        ])
    
    script_lines.append(f'    keystroke "{clean_text}"')
    
    if press_enter:
        script_lines.extend([
            '    delay 0.2',
            '    key code 36',  # Return key
        ])
        
    script_lines.append('end tell')
    
    script = "\n".join(script_lines)
    success, out = _run_applescript(script)
    
    if success:
        action_desc = f"Typed '{text}' into {app_name}"
        if press_enter:
            action_desc += " and pressed Enter"
        return action_desc + "."
    else:
        # Fallback to pyautogui if AppleScript failed
        if HAS_PYAUTOGUI:
            try:
                # Activate app first
                _run_applescript(f'tell application "{clean_app}" to activate')
                time.sleep(0.4)
                if clear_first:
                    pyautogui.hotkey('command', 'a')
                    pyautogui.press('backspace')
                pyautogui.write(text, interval=0.02)
                if press_enter:
                    pyautogui.press('enter')
                return f"Typed '{text}' into {app_name} (via pyautogui)."
            except Exception as e:
                return f"Failed to type into {app_name}: {out} (pyautogui error: {e})"
        return f"Failed to type into {app_name}: {out}"


def apple_music_search(query: str, auto_play: bool = True) -> str:
    """
    Open Apple Music, navigate to the search bar, switch to the 'Apple Music' catalog tab,
    type the query, and search. Optionally starts playback of the top result.
    
    Args:
        query: The song, artist, album, or playlist to search for
        auto_play: If True, attempts to start playback of the first result
    """
    clean_query = _escape_applescript_string(query)
    
    # 1. Activate and reopen Music app (reopen ensures main window appears even if app was running with 0 windows)
    reopen_script = '''
    tell application "Music"
        reopen
        activate
    end tell
    '''
    _run_applescript(reopen_script)
    time.sleep(0.5)

    # 2. Focus search bar using Cmd + F, then select 'Apple Music' tab instead of 'Library'
    search_tab_script = f'''
    tell application "Music" to activate
    delay 0.2
    tell application "System Events"
        tell process "Music"
            -- Focus search bar using Cmd + F
            keystroke "f" using {{command down}}
            delay 0.3

            -- Select the "Apple Music" tab in the toolbar radio group
            try
                set w to first window
                set tb to first UI element of w whose role is "AXToolbar"
                repeat with grp in (UI elements of tb)
                    try
                        set rGroup to first UI element of grp whose role is "AXRadioGroup"
                        repeat with btn in (UI elements of rGroup)
                            if (description of btn contains "Apple Music") or (title of btn contains "Apple Music") then
                                click btn
                                exit repeat
                            end if
                        end repeat
                    end try
                end repeat
            end try
            delay 0.2

            -- Select all in search box to clear previous query
            keystroke "a" using {{command down}}
            delay 0.1
            key code 51 -- Backspace
            delay 0.1

            -- Type the query and press Enter to search
            keystroke "{clean_query}"
            delay 0.2
            key code 36 -- Return
        end tell
    end tell
    '''
    
    success, out = _run_applescript(search_tab_script)
    if not success:
        return f"Could not search Apple Music: {out}"
        
    if auto_play:
        time.sleep(1.2)
        # Attempt to play the top result
        play_script = '''
        tell application "Music" to activate
        delay 0.2
        tell application "System Events"
            tell process "Music"
                -- Press Down arrow to enter results list and Return to play
                key code 125 -- Down Arrow
                delay 0.3
                key code 36 -- Return
                delay 0.2
                key code 49 -- Spacebar
            end tell
        end tell
        tell application "Music" to play
        '''
        _run_applescript(play_script)

        # Fallback double-click on first result card if needed
        if HAS_PYAUTOGUI:
            try:
                # Top-left result card in Apple Music grid is typically around (550, 245)
                pyautogui.doubleClick(550, 245)
                time.sleep(0.3)
                _run_applescript('tell application "Music" to play')
            except Exception:
                pass

        return f"Searched Apple Music for '{query}' in the Apple Music tab and initiated playback."
        
    return f"Searched Apple Music for '{query}' in the Apple Music tab."


def apple_music_control(action: str) -> str:
    """
    Control Apple Music playback directly using native AppleScript.
    
    Args:
        action: One of 'play', 'pause', 'toggle', 'next', 'previous', 'stop'
    """
    action_lower = action.lower().strip()
    cmd_map = {
        "play": "play",
        "pause": "pause",
        "toggle": "playpause",
        "next": "next track",
        "previous": "previous track",
        "prev": "previous track",
        "stop": "stop"
    }
    
    if action_lower not in cmd_map:
        return f"Unknown action '{action}'. Use play, pause, toggle, next, or previous."
        
    script = f'tell application "Music" to {cmd_map[action_lower]}'
    success, out = _run_applescript(script)
    if success:
        return f"Apple Music: {action_lower} executed."
    return f"Apple Music control failed: {out}"


def antigravity_type_prompt(prompt: str, press_enter: bool = True) -> str:
    """
    Switch to Antigravity IDE and type a command or prompt into the active chat or editor.
    
    Args:
        prompt: The prompt or command to type into Antigravity
        press_enter: Whether to press Enter after typing to submit the prompt
    """
    # Look for Antigravity or related processes
    find_app_script = '''
    tell application "System Events"
        set appList to name of every application process
        repeat with appName in appList
            if (appName as text) contains "Antigravity" or (appName as text) contains "antigravity" then
                return appName as text
            end if
        end repeat
        return ""
    end tell
    '''
    _, matched_name = _run_applescript(find_app_script)
    target_app = matched_name if matched_name else "Antigravity"
    
    clean_prompt = _escape_applescript_string(prompt)
    
    script_lines = [
        f'tell application "{target_app}" to activate',
        'delay 0.4',
        'tell application "System Events"',
        f'    keystroke "{clean_prompt}"',
    ]
    if press_enter:
        script_lines.extend([
            '    delay 0.2',
            '    key code 36',  # Return
        ])
    script_lines.append('end tell')
    
    success, out = _run_applescript("\n".join(script_lines))
    if success:
        msg = f"Typed prompt into {target_app}"
        if press_enter:
            msg += " and submitted (Enter pressed)"
        return msg + "."
    
    # Fallback to pyautogui
    if HAS_PYAUTOGUI:
        try:
            _run_applescript(f'tell application "{target_app}" to activate')
            time.sleep(0.4)
            pyautogui.write(prompt, interval=0.02)
            if press_enter:
                pyautogui.press('enter')
            return f"Typed prompt into {target_app} (via pyautogui)."
        except Exception as e:
            return f"Failed to type prompt into Antigravity: {e}"
            
    return f"Failed to type prompt into Antigravity: {out}"


def app_press_hotkey(app_name: str, keys: str) -> str:
    """
    Send a keyboard shortcut or hotkey to an application.
    
    Args:
        app_name: Name of the application (or 'active' for current frontmost app)
        keys: Comma-separated keys, e.g., 'command,f' or 'command,shift,p' or 'space' or 'enter'
    """
    key_list = [k.strip().lower() for k in keys.split(",") if k.strip()]
    if not key_list:
        return "No keys provided."
        
    if app_name.lower() != "active":
        clean_app = _escape_applescript_string(app_name)
        _run_applescript(f'tell application "{clean_app}" to activate')
        time.sleep(0.3)
        
    if HAS_PYAUTOGUI:
        try:
            pyautogui.hotkey(*key_list)
            return f"Pressed hotkey '{keys}' in {app_name}."
        except Exception as e:
            return f"Failed to press hotkey: {e}"
            
    return "Hotkey simulation requires pyautogui."


def app_click_coordinates(x: int, y: int) -> str:
    """
    Click at specific screen coordinates (x, y) on macOS.
    
    Args:
        x: X coordinate on screen in pixels
        y: Y coordinate on screen in pixels
    """
    if not HAS_PYAUTOGUI:
        return "Coordinate clicking requires pyautogui."
    try:
        pyautogui.click(x=x, y=y)
        return f"Clicked at ({x}, {y})."
    except Exception as e:
        return f"Failed to click at ({x}, {y}): {e}"


# ── Tool Definitions for Jarvis Function Calling ─────────────

APP_AUTOMATION_TOOLS = [
    {
        "name": "app_type_text",
        "description": "Bring a macOS application to the foreground and type text into its active input field, search box, or editor. Can optionally clear existing text and press Enter.",
        "function": app_type_text,
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Name of the target app (e.g., 'Music', 'Antigravity', 'Notes', 'Visual Studio Code', 'Slack')",
                },
                "text": {
                    "type": "string",
                    "description": "The exact text to type",
                },
                "clear_first": {
                    "type": "boolean",
                    "description": "Whether to select-all and clear existing text before typing (default: false)",
                },
                "press_enter": {
                    "type": "boolean",
                    "description": "Whether to press Enter/Return after typing (default: false)",
                }
            },
            "required": ["app_name", "text"],
        },
    },
    {
        "name": "apple_music_search",
        "description": "Open Apple Music, jump to the search bar (Cmd+F), type a song/artist/playlist search query, and execute the search. Can also automatically begin playback of the top result.",
        "function": apple_music_search,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The song title, artist, album, or genre to search for in Apple Music",
                },
                "auto_play": {
                    "type": "boolean",
                    "description": "Whether to automatically start playback of the first result (default: true)",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "apple_music_control",
        "description": "Control Apple Music playback directly: play, pause, toggle playback, skip to next track, or go to previous track.",
        "function": apple_music_control,
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Playback action: 'play', 'pause', 'toggle', 'next', 'previous', 'stop'",
                }
            },
            "required": ["action"],
        },
    },
    {
        "name": "antigravity_type_prompt",
        "description": "Focus the Antigravity AI IDE window and type a prompt or command into the input box, optionally pressing Enter to submit it.",
        "function": antigravity_type_prompt,
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The prompt or instruction to type into Antigravity",
                },
                "press_enter": {
                    "type": "boolean",
                    "description": "Whether to press Enter to submit the prompt immediately (default: true)",
                }
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "app_press_hotkey",
        "description": "Send a keyboard shortcut or hotkey to an application (e.g., 'command,f' or 'command,shift,p' or 'space').",
        "function": app_press_hotkey,
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "The application to receive the hotkey, or 'active' for the frontmost window",
                },
                "keys": {
                    "type": "string",
                    "description": "Comma-separated key names, e.g. 'command,f' or 'command,a' or 'space' or 'enter'",
                }
            },
            "required": ["app_name", "keys"],
        },
    },
    {
        "name": "get_active_app_info",
        "description": "Get the name and window title of the frontmost active application on macOS.",
        "function": get_active_app_info,
        "parameters": {},
    },
]
