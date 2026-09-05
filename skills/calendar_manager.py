# Jarvis AI — macOS Calendar Manager Skill
# Reads and creates calendar events using AppleScript.

import subprocess
import datetime


def _run_applescript(script: str) -> str:
    """Run an AppleScript and return the output."""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return result.stderr.strip() or "No output"
    except subprocess.TimeoutExpired:
        return "Calendar script timed out."
    except Exception as e:
        return f"Calendar error: {e}"


def get_todays_events() -> str:
    """
    Get all calendar events scheduled for today.

    Returns:
        Formatted list of today's events
    """
    script = '''
    set todayStart to current date
    set time of todayStart to 0
    set todayEnd to todayStart + (1 * days) - 1

    set eventList to ""

    tell application "Calendar"
        repeat with cal in calendars
            set calEvents to (every event of cal whose start date ≥ todayStart and start date ≤ todayEnd)
            repeat with evt in calEvents
                set evtTitle to summary of evt
                set evtStart to start date of evt
                set evtEnd to end date of evt
                set startTime to time string of evtStart
                set endTime to time string of evtEnd
                set eventList to eventList & evtTitle & " | " & startTime & " - " & endTime & linefeed
            end repeat
        end repeat
    end tell

    if eventList is "" then
        return "No events scheduled for today."
    end if
    return eventList
    '''

    result = _run_applescript(script)

    if "No events" in result or not result.strip():
        return "You have no events scheduled for today. Your day is clear!"

    # Format the events nicely
    events = result.strip().split("\n")
    formatted = [f"📅 You have {len(events)} event{'s' if len(events) != 1 else ''} today:\n"]

    for i, event in enumerate(events, 1):
        parts = event.split("|")
        if len(parts) >= 2:
            title = parts[0].strip()
            time_range = parts[1].strip()
            formatted.append(f"  {i}. {title} — {time_range}")
        else:
            formatted.append(f"  {i}. {event.strip()}")

    return "\n".join(formatted)


def get_upcoming_events(days: int = 7) -> str:
    """
    Get upcoming calendar events for the next N days.

    Args:
        days: Number of days to look ahead (default: 7)
    """
    script = f'''
    set todayStart to current date
    set time of todayStart to 0
    set futureDate to todayStart + ({days} * days)

    set eventList to ""

    tell application "Calendar"
        repeat with cal in calendars
            set calEvents to (every event of cal whose start date ≥ todayStart and start date ≤ futureDate)
            repeat with evt in calEvents
                set evtTitle to summary of evt
                set evtStart to start date of evt
                set startDateStr to date string of evtStart
                set startTime to time string of evtStart
                set eventList to eventList & evtTitle & " | " & startDateStr & " | " & startTime & linefeed
            end repeat
        end repeat
    end tell

    if eventList is "" then
        return "No upcoming events in the next {days} days."
    end if
    return eventList
    '''

    result = _run_applescript(script)

    if "No upcoming" in result or not result.strip():
        return f"You have no events in the next {days} days."

    events = result.strip().split("\n")
    formatted = [f"📅 You have {len(events)} upcoming event{'s' if len(events) != 1 else ''} in the next {days} days:\n"]

    for i, event in enumerate(events, 1):
        parts = event.split("|")
        if len(parts) >= 3:
            title = parts[0].strip()
            date_str = parts[1].strip()
            time_str = parts[2].strip()
            formatted.append(f"  {i}. {title} — {date_str} at {time_str}")
        else:
            formatted.append(f"  {i}. {event.strip()}")

    return "\n".join(formatted)


def create_event(
    title: str,
    start_hour: int,
    start_minute: int = 0,
    duration_hours: int = 1,
    notes: str = "",
) -> str:
    """
    Create a new calendar event for today.

    Args:
        title: Event title
        start_hour: Start hour (24-hour format, e.g., 14 for 2 PM)
        start_minute: Start minute (default: 0)
        duration_hours: Duration in hours (default: 1)
        notes: Optional notes for the event
    """
    notes_line = f'set description of newEvent to "{notes}"' if notes else ""

    script = f'''
    tell application "Calendar"
        set todayDate to current date
        set time of todayDate to ({start_hour} * 3600 + {start_minute} * 60)
        set endDate to todayDate + ({duration_hours} * hours)

        tell calendar 1
            set newEvent to make new event with properties {{summary:"{title}", start date:todayDate, end date:endDate}}
            {notes_line}
        end tell
    end tell
    return "Event created successfully."
    '''

    result = _run_applescript(script)

    if "successfully" in result.lower() or "event" in result.lower():
        time_str = f"{start_hour:02d}:{start_minute:02d}"
        return f"Created event '{title}' at {time_str} for {duration_hours} hour{'s' if duration_hours != 1 else ''}."
    return f"Could not create event: {result}"


def open_calendar() -> str:
    """Open the macOS Calendar app."""
    try:
        subprocess.run(
            ["open", "-a", "Calendar"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return "Opening Calendar app."
    except Exception as e:
        return f"Error opening Calendar: {e}"


# ── Tool definitions for Gemini function calling ─────────────
CALENDAR_TOOLS = [
    {
        "name": "get_todays_events",
        "description": (
            "Get all calendar events scheduled for today. "
            "Use when the user asks about their schedule, meetings, or what's on today."
        ),
        "function": get_todays_events,
        "parameters": {},
    },
    {
        "name": "get_upcoming_events",
        "description": (
            "Get upcoming calendar events for the next few days. "
            "Use when the user asks about their upcoming schedule or future events."
        ),
        "function": get_upcoming_events,
        "parameters": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to look ahead (default: 7)",
                }
            },
        },
    },
    {
        "name": "create_event",
        "description": (
            "Create a new calendar event for today. "
            "Use when the user wants to add a meeting or event to their calendar."
        ),
        "function": create_event,
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title of the event",
                },
                "start_hour": {
                    "type": "integer",
                    "description": "Start hour in 24-hour format (e.g., 14 for 2 PM)",
                },
                "start_minute": {
                    "type": "integer",
                    "description": "Start minute (default: 0)",
                },
                "duration_hours": {
                    "type": "integer",
                    "description": "Duration in hours (default: 1)",
                },
                "notes": {
                    "type": "string",
                    "description": "Optional notes or description for the event",
                },
            },
            "required": ["title", "start_hour"],
        },
    },
    {
        "name": "open_calendar",
        "description": "Open the macOS Calendar application.",
        "function": open_calendar,
        "parameters": {},
    },
]
