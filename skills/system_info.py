# Jarvis AI — System Information Skill
# Provides time, date, battery, system stats, and weather.

import datetime
import platform
import subprocess


def get_time() -> str:
    """Get the current time in a spoken-friendly format."""
    now = datetime.datetime.now()
    hour = now.strftime("%I")  # 12-hour format
    minute = now.strftime("%M")
    period = now.strftime("%p")
    return f"The time is {hour}:{minute} {period}."


def get_date() -> str:
    """Get the current date in a spoken-friendly format."""
    now = datetime.datetime.now()
    return f"Today is {now.strftime('%A, %B %d, %Y')}."


def get_day() -> str:
    """Get the current day of the week."""
    return f"Today is {datetime.datetime.now().strftime('%A')}."


def get_battery() -> str:
    """Get MacBook battery status."""
    try:
        result = subprocess.run(
            ["pmset", "-g", "batt"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = result.stdout.strip()

        # Parse battery percentage
        for line in output.split("\n"):
            if "%" in line:
                parts = line.strip().split("\t")
                if len(parts) >= 2:
                    pct_info = parts[1].strip()
                    pct = pct_info.split("%")[0].strip().split()[-1]
                    charging = "charging" in pct_info.lower()
                    status = "charging" if charging else "on battery"
                    return f"Battery is at {pct}%, currently {status}."

        return "Could not read battery status."
    except Exception as e:
        return f"Error checking battery: {e}"


def get_cpu_usage() -> str:
    """Get current CPU usage."""
    try:
        result = subprocess.run(
            ["top", "-l", "1", "-n", "0"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        for line in result.stdout.split("\n"):
            if "CPU usage" in line:
                return f"CPU: {line.strip()}"
        return "Could not read CPU usage."
    except Exception as e:
        return f"Error checking CPU: {e}"


def get_memory_usage() -> str:
    """Get current memory usage."""
    try:
        result = subprocess.run(
            ["vm_stat"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        lines = result.stdout.strip().split("\n")
        stats = {}
        for line in lines[1:]:  # Skip header
            if ":" in line:
                key, val = line.split(":")
                # Pages are 4096 bytes on macOS
                try:
                    stats[key.strip()] = int(val.strip().rstrip(".")) * 4096
                except ValueError:
                    pass

        active = stats.get("Pages active", 0)
        wired = stats.get("Pages wired down", 0)
        used_gb = (active + wired) / (1024 ** 3)
        return f"Memory usage: approximately {used_gb:.1f} GB in use."
    except Exception as e:
        return f"Error checking memory: {e}"


def get_system_info() -> str:
    """Get basic system information."""
    info = platform.uname()
    return (
        f"You're running {info.system} {info.release} "
        f"on a {info.machine} machine. "
        f"Computer name: {info.node}."
    )


def get_volume() -> str:
    """Get the current system volume."""
    try:
        result = subprocess.run(
            ["osascript", "-e", "output volume of (get volume settings)"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        vol = result.stdout.strip()
        return f"The volume is at {vol}%."
    except Exception as e:
        return f"Error checking volume: {e}"


def set_volume(level: int) -> str:
    """Set the system volume (0-100)."""
    level = max(0, min(100, level))
    try:
        subprocess.run(
            ["osascript", "-e", f"set volume output volume {level}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return f"Volume set to {level}%."
    except Exception as e:
        return f"Error setting volume: {e}"


def get_weather(city: str = "auto") -> str:
    """Get current weather using wttr.in (free, no API key needed)."""
    try:
        import requests

        url = f"https://wttr.in/{city}?format=3" if city != "auto" else "https://wttr.in/?format=3"
        response = requests.get(url, timeout=5, headers={"User-Agent": "curl/7.0"})
        if response.status_code == 200:
            return f"Weather: {response.text.strip()}"
        return "Could not fetch weather information."
    except Exception as e:
        return f"Weather service unavailable: {e}"


# ── Tool definitions for Gemini function calling ─────────────
SYSTEM_TOOLS = [
    {
        "name": "get_time",
        "description": "Get the current time. Use when the user asks what time it is.",
        "function": get_time,
        "parameters": {},
    },
    {
        "name": "get_date",
        "description": "Get today's date. Use when the user asks about the date.",
        "function": get_date,
        "parameters": {},
    },
    {
        "name": "get_day",
        "description": "Get the current day of the week.",
        "function": get_day,
        "parameters": {},
    },
    {
        "name": "get_battery",
        "description": "Check the MacBook battery level and charging status.",
        "function": get_battery,
        "parameters": {},
    },
    {
        "name": "get_system_info",
        "description": "Get system information like OS version and machine type.",
        "function": get_system_info,
        "parameters": {},
    },
    {
        "name": "get_volume",
        "description": "Get the current system volume level.",
        "function": get_volume,
        "parameters": {},
    },
    {
        "name": "set_volume",
        "description": "Set the system volume to a specific level between 0 and 100.",
        "function": set_volume,
        "parameters": {
            "type": "object",
            "properties": {
                "level": {
                    "type": "integer",
                    "description": "Volume level from 0 to 100",
                }
            },
            "required": ["level"],
        },
    },
    {
        "name": "get_weather",
        "description": "Get the current weather. Optionally specify a city name.",
        "function": get_weather,
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name for weather. Use 'auto' for current location.",
                }
            },
        },
    },
    {
        "name": "get_cpu_usage",
        "description": "Get the current CPU usage of the system.",
        "function": get_cpu_usage,
        "parameters": {},
    },
    {
        "name": "get_memory_usage",
        "description": "Get the current RAM/memory usage.",
        "function": get_memory_usage,
        "parameters": {},
    },
]
