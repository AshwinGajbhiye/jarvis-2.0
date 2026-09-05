# Jarvis AI — Reminder Skill
# Sets native macOS reminders using AppleScript + Reminders.app.
# Reminders sync across all Apple devices via iCloud.

import subprocess
import datetime


def set_reminder(title: str, reminder_time: str = "", notes: str = "") -> str:
    """
    Set a reminder on macOS using the native Reminders app.
    
    Args:
        title: The reminder text/title
        reminder_time: When to remind. Accepts formats like:
                       "2026-07-08 18:30", "18:30", "6:30 PM",
                       "in 30 minutes", "in 2 hours", "tomorrow 9:00 AM"
                       If empty, creates a reminder with no due date.
        notes: Optional additional notes for the reminder
    
    Returns:
        Confirmation message
    """
    try:
        # Parse the reminder time
        due_date = _parse_reminder_time(reminder_time) if reminder_time else None
        
        # Build the AppleScript
        if due_date:
            y, m, d, h, mn, s = due_date.year, due_date.month, due_date.day, due_date.hour, due_date.minute, due_date.second
            script = f'''
            set dueDate to (current date)
            set year of dueDate to {y}
            set month of dueDate to {m}
            set day of dueDate to {d}
            set hours of dueDate to {h}
            set minutes of dueDate to {mn}
            set seconds of dueDate to {s}
            
            tell application "Reminders"
                set newReminder to make new reminder in list "Reminders" with properties {{name:"{_escape_applescript(title)}", due date:dueDate}}
            '''
            if notes:
                script += f'''
                set body of newReminder to "{_escape_applescript(notes)}"
                '''
            script += '''
            end tell
            '''
        else:
            script = f'''
            tell application "Reminders"
                set newReminder to make new reminder in list "Reminders" with properties {{name:"{_escape_applescript(title)}"}}
            '''
            if notes:
                script += f'''
                set body of newReminder to "{_escape_applescript(notes)}"
                '''
            script += '''
            end tell
            '''
        
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            time_msg = f" for {due_date.strftime('%I:%M %p on %B %d, %Y')}" if due_date else ""
            return f"Reminder set{time_msg}: '{title}'"
        else:
            error = result.stderr.strip()
            if "Not authorized" in error or "denied" in error:
                return "I need permission to access Reminders. Please go to System Settings → Privacy & Security → Reminders and allow Terminal/Python access."
            return f"Failed to set reminder: {error}"
    
    except Exception as e:
        return f"Error setting reminder: {str(e)}"


def list_reminders(count: int = 10) -> str:
    """
    List upcoming incomplete reminders from the macOS Reminders app.
    
    Args:
        count: Maximum number of reminders to show
    
    Returns:
        Formatted list of reminders
    """
    try:
        script = f'''
        tell application "Reminders"
            set output to ""
            set reminderList to (reminders in list "Reminders" whose completed is false)
            set maxCount to {count}
            set i to 0
            repeat with r in reminderList
                if i ≥ maxCount then exit repeat
                set reminderName to name of r
                try
                    set dueDate to due date of r
                    set output to output & "⏰ " & reminderName & " — Due: " & (dueDate as string) & linefeed
                on error
                    set output to output & "📌 " & reminderName & " — No due date" & linefeed
                end try
                set i to i + 1
            end repeat
            if output is "" then
                return "No pending reminders."
            end if
            return output
        end tell
        '''
        
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            output = result.stdout.strip()
            return f"**📋 Your Reminders:**\n{output}" if output else "No pending reminders, Sir."
        else:
            return f"Could not fetch reminders: {result.stderr.strip()}"
    
    except Exception as e:
        return f"Error listing reminders: {str(e)}"


def _escape_applescript(text: str) -> str:
    """Escape special characters for AppleScript strings."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _parse_reminder_time(time_str: str) -> datetime.datetime:
    """
    Parse a natural/flexible time string into a datetime.
    
    Supports:
        - "18:30" or "6:30 PM" → today at that time
        - "2026-07-08 18:30" → exact date+time
        - "in 30 minutes" → relative time
        - "in 2 hours" → relative time
        - "tomorrow 9:00 AM" → tomorrow at that time
    """
    now = datetime.datetime.now()
    time_str = time_str.strip().lower()
    
    # Relative time: "in X minutes/hours"
    if time_str.startswith("in "):
        parts = time_str[3:].split()
        if len(parts) >= 2:
            try:
                amount = int(parts[0])
                unit = parts[1]
                if "minute" in unit:
                    return now + datetime.timedelta(minutes=amount)
                elif "hour" in unit:
                    return now + datetime.timedelta(hours=amount)
                elif "day" in unit:
                    return now + datetime.timedelta(days=amount)
            except ValueError:
                pass
    
    # "tomorrow X"
    if time_str.startswith("tomorrow"):
        time_part = time_str.replace("tomorrow", "").strip()
        tomorrow = now + datetime.timedelta(days=1)
        if time_part:
            parsed_time = _parse_time_only(time_part)
            if parsed_time:
                return tomorrow.replace(
                    hour=parsed_time.hour, minute=parsed_time.minute,
                    second=0, microsecond=0
                )
        return tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
    
    # Full datetime: "2026-07-08 18:30"
    for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d %I:%M %p", "%d/%m/%Y %H:%M"]:
        try:
            return datetime.datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    
    # Time only: "18:30" or "6:30 PM"
    parsed_time = _parse_time_only(time_str)
    if parsed_time:
        result = now.replace(
            hour=parsed_time.hour, minute=parsed_time.minute,
            second=0, microsecond=0
        )
        # If the time has passed today, set for tomorrow
        if result < now:
            result += datetime.timedelta(days=1)
        return result
    
    # Fallback: 1 hour from now
    return now + datetime.timedelta(hours=1)


def _parse_time_only(time_str: str):
    """Parse a time-only string like '18:30' or '6:30 PM'."""
    time_str = time_str.strip()
    for fmt in ["%H:%M", "%I:%M %p", "%I:%M%p", "%I %p", "%I%p"]:
        try:
            return datetime.datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    return None


# ── Tool Definitions for Gemini ──────────────────────────────
REMINDER_TOOLS = [
    {
        "name": "set_reminder",
        "description": "Set a reminder on the user's MacBook using the native Reminders app. The reminder will sync across all Apple devices via iCloud. Use when the user says 'remind me to', 'set a reminder', 'don't let me forget', etc. If the user doesn't specify a time, ASK them when they'd like to be reminded.",
        "function": set_reminder,
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "The reminder text (e.g., 'Buy groceries', 'Call mom')",
                },
                "reminder_time": {
                    "type": "string",
                    "description": "When to remind. Examples: '18:30', '6:30 PM', 'in 30 minutes', 'in 2 hours', 'tomorrow 9:00 AM', '2026-07-08 18:30'. Leave empty if the user didn't specify a time — in that case, ASK the user what time they want.",
                },
                "notes": {
                    "type": "string",
                    "description": "Optional additional notes or details for the reminder",
                },
            },
            "required": ["title"],
        },
    },
    {
        "name": "list_reminders",
        "description": "Show the user's upcoming/incomplete reminders from the macOS Reminders app. Use when the user asks 'what are my reminders', 'show reminders', 'any reminders', etc.",
        "function": list_reminders,
        "parameters": {
            "type": "object",
            "properties": {
                "count": {
                    "type": "integer",
                    "description": "Maximum number of reminders to show (default 10)",
                },
            },
        },
    },
]
