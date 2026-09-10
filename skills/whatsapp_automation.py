# Jarvis AI — WhatsApp Desktop Automation Skill
# Automates the native WhatsApp Desktop application on macOS via AppleScript.
# Supports searching contacts, drafting messages into the chat, and human-in-the-loop confirmation before sending.

import subprocess
import time
import urllib.parse
import re
from typing import Optional, Dict, Any


# ── Global State for Pending Confirmation ─────────────────────
_pending_confirmation: Optional[Dict[str, Any]] = None


# ── Helper Functions ──────────────────────────────────────────

def _run_applescript(script: str) -> tuple[bool, str]:
    """Execute AppleScript and return (success, stdout/stderr)."""
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


def _copy_to_clipboard(text: str):
    """Safely put text onto macOS system clipboard for pasting with emojis/newlines."""
    proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
    proc.communicate(text.encode("utf-8"))


def _escape_applescript_string(s: str) -> str:
    """Escape backslashes and double quotes for AppleScript."""
    return s.replace('\\', '\\\\').replace('"', '\\"')


def _is_phone_number(contact: str) -> bool:
    """Check if contact looks like a phone number."""
    cleaned = re.sub(r'[\s\-\(\)\+]', '', contact)
    return cleaned.isdigit() and len(cleaned) >= 7


def _ensure_whatsapp_running():
    """Ensure WhatsApp Desktop is running and active."""
    check_script = '''
    tell application "System Events"
        return (count of (processes whose name is "WhatsApp")) > 0
    end tell
    '''
    success, out = _run_applescript(check_script)
    if not success or out != "true":
        # Launch WhatsApp Desktop
        subprocess.run(["open", "-a", "WhatsApp"])
        time.sleep(1.8)
    else:
        _run_applescript('tell application "WhatsApp" to activate')
        time.sleep(0.3)


def _get_whatsapp_window_bounds() -> tuple[int, int, int, int]:
    """Retrieve (x, y, width, height) of WhatsApp main window."""
    script = '''
    tell application "System Events"
        tell process "WhatsApp"
            set w to first window
            set p to position of w
            set s to size of w
            return (item 1 of p as text) & "," & (item 2 of p as text) & "," & (item 1 of s as text) & "," & (item 2 of s as text)
        end tell
    end tell
    '''
    success, out = _run_applescript(script)
    if success and ',' in out:
        try:
            parts = [int(p.strip()) for p in out.split(',')]
            return parts[0], parts[1], parts[2], parts[3]
        except Exception:
            pass
    return 0, 30, 1440, 870


def _find_contact_element_pos(contact_name: str) -> Optional[tuple[int, int]]:
    """
    Search WhatsApp's UI tree for the contact element in the chats/search column.
    Returns (center_x, center_y) if found, else None.
    """
    clean_name = _escape_applescript_string(contact_name.lower())
    script = f'''
    tell application "System Events"
        tell process "WhatsApp"
            set q to {{UI element 1 of window 1}}
            set depth to 0
            repeat while (count of q) > 0 and depth < 10
                set nextQ to {{}}
                repeat with item1 in q
                    try
                        set d to (description of item1 as text)
                        set r to (role of item1 as text)
                        -- Check description (case-insensitive search in AppleScript)
                        if (d contains "{clean_name}") and (r is not "AXHeading") and (r is not "AXGroup") then
                            set p to position of item1
                            set s to size of item1
                            -- Must be in the search results column (X < 450) and below title bar
                            if (item 1 of p) < 450 and (item 2 of p) > 100 then
                                return (item 1 of p as text) & "," & (item 2 of p as text) & "," & (item 1 of s as text) & "," & (item 2 of s as text)
                            end if
                        end if
                        repeat with ch in (UI elements of item1)
                            set end of nextQ to ch
                        end repeat
                    end try
                end repeat
                set q to nextQ
                set depth to depth + 1
            end repeat
            return "NONE"
        end tell
    end tell
    '''
    success, out = _run_applescript(script)
    if success and out and out != "NONE" and "," in out:
        try:
            parts = [int(x.strip()) for x in out.split(",")]
            cx = parts[0] + parts[2] // 2
            cy = parts[1] + parts[3] // 2
            return cx, cy
        except Exception:
            pass
    return None


def _focus_chat_message_input():
    """
    Focus the message input box at the bottom of the open conversation panel.
    Clicks directly at the message input box coordinates.
    """
    import pyautogui
    wx, wy, ww, wh = _get_whatsapp_window_bounds()
    # Message box is at the bottom of the conversation panel:
    # X ~ 65% across window width (e.g. 940 on a 1440w display)
    # Y ~ bottom of window (e.g. wy + wh - 30)
    target_x = wx + int(ww * 0.65)
    target_y = wy + wh - 30
    pyautogui.click(target_x, target_y)
    time.sleep(0.3)


# ── Core WhatsApp Desktop Operations ──────────────────────────

def whatsapp_search_contact(contact_name: str) -> str:
    """
    Search for a person or group in the WhatsApp Desktop app and open their chat.
    
    Args:
        contact_name: The name or phone number of the person/group to find
    """
    _ensure_whatsapp_running()

    # If it's a phone number, use whatsapp:// URL scheme for instant navigation
    if _is_phone_number(contact_name):
        clean_phone = re.sub(r'[\s\-\(\)\+]', '', contact_name)
        subprocess.run(["open", f"whatsapp://send?phone={clean_phone}"])
        time.sleep(1.0)
        _focus_chat_message_input()
        return f"Opened chat with {contact_name} on WhatsApp Desktop."

    clean_name = _escape_applescript_string(contact_name)

    # Step 1: Trigger Search via Cmd + F, clear search bar, type contact name
    search_script = f'''
    tell application "WhatsApp" to activate
    delay 0.2
    tell application "System Events"
        tell process "WhatsApp"
            -- Trigger Search via Cmd + F
            keystroke "f" using {{command down}}
            delay 0.2
            -- Select all in search bar and delete
            keystroke "a" using {{command down}}
            delay 0.1
            key code 51 -- Backspace
            delay 0.1
            -- Type the contact name
            keystroke "{clean_name}"
        end tell
    end tell
    '''
    _run_applescript(search_script)
    time.sleep(1.0)  # Wait for search results to populate

    # Step 2: Open the chat by clicking the contact in search results
    import pyautogui
    pos = _find_contact_element_pos(contact_name)
    if pos:
        pyautogui.click(pos[0], pos[1])
    else:
        # Fallback: Click the top search result in chat column
        wx, wy, ww, wh = _get_whatsapp_window_bounds()
        pyautogui.click(wx + 250, wy + 190)
        # Also send Down Arrow + Return to ensure chat opens
        _run_applescript('''
        tell application "System Events"
            tell process "WhatsApp"
                key code 125 -- Down Arrow
                delay 0.2
                key code 36 -- Return
            end tell
        end tell
        ''')

    time.sleep(0.8)

    # Step 3: Focus the chat's message input field
    _focus_chat_message_input()

    return f"Searched for and opened chat with '{contact_name}' on WhatsApp Desktop."


def whatsapp_draft_message(contact_name: str, message: str) -> str:
    """
    Search for a contact on WhatsApp Desktop, open their chat, and write the message
    into the chat input field. Does NOT send it immediately — asks user for confirmation.
    
    Args:
        contact_name: The name or phone number of the recipient
        message: The message text to type into the input field
    """
    global _pending_confirmation

    _ensure_whatsapp_running()

    # Step 1: Search and explicitly open chat
    if _is_phone_number(contact_name):
        clean_phone = re.sub(r'[\s\-\(\)\+]', '', contact_name)
        encoded_msg = urllib.parse.quote(message)
        subprocess.run(["open", f"whatsapp://send?phone={clean_phone}&text={encoded_msg}"])
        time.sleep(1.0)
        _focus_chat_message_input()
    else:
        search_res = whatsapp_search_contact(contact_name)
        if "Failed" in search_res:
            return search_res

        # Step 2: Ensure chat message input box is focused
        _focus_chat_message_input()

        # Step 3: Copy message to clipboard and paste into WhatsApp Desktop message input
        _copy_to_clipboard(message)
        time.sleep(0.1)

        paste_script = '''
        tell application "WhatsApp" to activate
        delay 0.1
        tell application "System Events"
            tell process "WhatsApp"
                -- Select any existing text in message input and replace with new message
                keystroke "a" using {command down}
                delay 0.1
                keystroke "v" using {command down}
                delay 0.2
            end tell
        end tell
        '''
        success, out = _run_applescript(paste_script)
        if not success:
            return f"Failed to write message into WhatsApp: {out}"

    # Step 4: Record pending confirmation state
    _pending_confirmation = {
        "contact": contact_name,
        "message": message,
        "timestamp": time.time(),
        "platform": "whatsapp_desktop"
    }

    return (
        f"I have opened the chat with {contact_name} on WhatsApp Desktop and drafted the message: '{message}'. "
        f"Should I send it now, Sir?"
    )


def whatsapp_confirm_send() -> str:
    """
    Confirm and dispatch the drafted WhatsApp message.
    Use this when the user responds affirmatively ('yes', 'send it', 'confirm', 'go ahead').
    """
    global _pending_confirmation

    if not _pending_confirmation:
        return "There is no pending WhatsApp message to send, Sir."

    contact = _pending_confirmation["contact"]
    message = _pending_confirmation["message"]

    _ensure_whatsapp_running()
    _focus_chat_message_input()

    # Send the message by pressing Return in WhatsApp Desktop
    send_script = '''
    tell application "WhatsApp" to activate
    delay 0.1
    tell application "System Events"
        tell process "WhatsApp"
            -- Press Return to send the drafted message
            key code 36 -- Return
            delay 0.2
        end tell
    end tell
    '''
    success, out = _run_applescript(send_script)
    
    if success:
        _pending_confirmation = None
        return f"Message sent to {contact} on WhatsApp, Sir: '{message}'."
    return f"Failed to dispatch WhatsApp message: {out}"


def whatsapp_cancel_send() -> str:
    """
    Cancel and erase the drafted WhatsApp message.
    Use this when the user declines ('no', 'cancel', 'don't send', 'stop').
    """
    global _pending_confirmation

    if not _pending_confirmation:
        return "No pending WhatsApp message to cancel, Sir."

    contact = _pending_confirmation["contact"]

    _ensure_whatsapp_running()
    _focus_chat_message_input()

    # Clear the drafted message by selecting all and hitting Backspace
    clear_script = '''
    tell application "WhatsApp" to activate
    delay 0.1
    tell application "System Events"
        tell process "WhatsApp"
            keystroke "a" using {command down}
            delay 0.1
            key code 51 -- Backspace
            delay 0.1
        end tell
    end tell
    '''
    _run_applescript(clear_script)
    _pending_confirmation = None

    return f"I have cancelled and cleared the message to {contact}, Sir."


def whatsapp_send_direct(contact_name: str, message: str) -> str:
    """
    Send a WhatsApp message immediately without asking for confirmation.
    ONLY use if user explicitly ordered to bypass confirmation.
    """
    draft_res = whatsapp_draft_message(contact_name, message)
    if "drafted" in draft_res.lower() or "should i send" in draft_res.lower():
        return whatsapp_confirm_send()
    return draft_res


def has_pending_whatsapp_message() -> bool:
    """Check if there is a drafted WhatsApp message waiting for confirmation."""
    return _pending_confirmation is not None


def get_pending_whatsapp_message() -> Optional[Dict[str, Any]]:
    """Get the current pending confirmation payload if any."""
    return _pending_confirmation


# ── Tool Definitions for Function Calling ─────────────────────

WHATSAPP_TOOLS = [
    {
        "name": "whatsapp_search_contact",
        "description": "Search for a person or group in the WhatsApp Desktop application and open their chat.",
        "function": whatsapp_search_contact,
        "parameters": {
            "type": "object",
            "properties": {
                "contact_name": {
                    "type": "string",
                    "description": "Name or phone number of the person or group on WhatsApp Desktop",
                }
            },
            "required": ["contact_name"],
        },
    },
    {
        "name": "whatsapp_draft_message",
        "description": (
            "Search for a person on the WhatsApp Desktop app, open their chat, and write the message in the input field. "
            "Always use this when the user asks to send a WhatsApp message so that Jarvis can confirm with the user before sending."
        ),
        "function": whatsapp_draft_message,
        "parameters": {
            "type": "object",
            "properties": {
                "contact_name": {
                    "type": "string",
                    "description": "Name or phone number of the recipient on WhatsApp",
                },
                "message": {
                    "type": "string",
                    "description": "The exact message text to write in the input box",
                }
            },
            "required": ["contact_name", "message"],
        },
    },
    {
        "name": "whatsapp_confirm_send",
        "description": (
            "Send the drafted WhatsApp message that is currently awaiting confirmation. "
            "Call this when the user confirms with 'yes', 'send it', 'go ahead', 'confirm', 'do it', etc."
        ),
        "function": whatsapp_confirm_send,
        "parameters": {},
    },
    {
        "name": "whatsapp_cancel_send",
        "description": (
            "Cancel and clear the drafted WhatsApp message. "
            "Call this when the user declines with 'no', 'cancel', 'don't send', 'stop', etc."
        ),
        "function": whatsapp_cancel_send,
        "parameters": {},
    },
    {
        "name": "whatsapp_send_direct",
        "description": "Send a WhatsApp message immediately without asking for confirmation. ONLY use if user explicitly instructed to bypass confirmation.",
        "function": whatsapp_send_direct,
        "parameters": {
            "type": "object",
            "properties": {
                "contact_name": {
                    "type": "string",
                    "description": "Name or phone number of the recipient",
                },
                "message": {
                    "type": "string",
                    "description": "Message text to send",
                }
            },
            "required": ["contact_name", "message"],
        },
    },
]
