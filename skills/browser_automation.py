# Jarvis AI — Browser Automation Skill
# Opens websites, performs Google searches, and controls Chrome/Brave.

import subprocess
import webbrowser
import urllib.parse

from config import Config


# ── Quick-access website shortcuts ────────────────────────────
SITE_SHORTCUTS = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "github": "https://github.com",
    "stackoverflow": "https://stackoverflow.com",
    "stack overflow": "https://stackoverflow.com",
    "reddit": "https://www.reddit.com",
    "twitter": "https://twitter.com",
    "x": "https://x.com",
    "linkedin": "https://www.linkedin.com",
    "wikipedia": "https://www.wikipedia.org",
    "amazon": "https://www.amazon.in",
    "netflix": "https://www.netflix.com",
    "chatgpt": "https://chat.openai.com",
    "gemini": "https://gemini.google.com",
    "drive": "https://drive.google.com",
    "maps": "https://maps.google.com",
    "news": "https://news.google.com",
    "whatsapp web": "https://web.whatsapp.com",
    "notion": "https://www.notion.so",
    "figma": "https://www.figma.com",
    "leetcode": "https://leetcode.com",
    "hackerrank": "https://www.hackerrank.com",
    "coursera": "https://www.coursera.org",
    "udemy": "https://www.udemy.com",
}


def _get_browser_app_name(browser_choice: str = None) -> str:
    """Get the browser application name based on config or user choice."""
    browser = browser_choice.lower() if browser_choice else Config.DEFAULT_BROWSER.lower()
    if browser == "brave":
        return "Brave Browser"
    elif browser == "safari":
        return "Safari"
    elif browser == "firefox":
        return "Firefox"
    elif browser == "arc":
        return "Arc"
    elif browser == "chrome":
        return "Google Chrome"
    else:
        return "Google Chrome"


def open_website(url: str, browser: str = None) -> str:
    """
    Open a URL in the configured browser.

    Args:
        url: Full URL or site shortcut name (e.g., 'youtube', 'github')
        browser: Optional browser to use ('chrome', 'brave', etc.)
    """
    # Check if it's a shortcut name
    url_lower = url.lower().strip()
    if url_lower in SITE_SHORTCUTS:
        actual_url = SITE_SHORTCUTS[url_lower]
    elif not url.startswith(("http://", "https://")):
        # Try as a shortcut first, then as a domain
        for name, site_url in SITE_SHORTCUTS.items():
            if url_lower in name or name in url_lower:
                actual_url = site_url
                break
        else:
            actual_url = f"https://{url}"
    else:
        actual_url = url

    try:
        browser_app = _get_browser_app_name(browser)
        subprocess.run(
            ["open", "-a", browser_app, actual_url],
            capture_output=True,
            text=True,
            timeout=10,
        )
        # Extract display name
        display = url_lower if url_lower in SITE_SHORTCUTS else actual_url
        return f"Opening {display} in {browser_app}."
    except Exception as e:
        # Fallback to default browser
        try:
            webbrowser.open(actual_url)
            return f"Opening {actual_url} in your default browser."
        except Exception as e2:
            return f"Could not open {actual_url}: {e2}"


def google_search(query: str, browser: str = None) -> str:
    """
    Perform a Google search in the browser.

    Args:
        query: The search query
        browser: Optional browser to use ('chrome', 'brave', etc.)
    """
    encoded = urllib.parse.quote_plus(query)
    url = f"https://www.google.com/search?q={encoded}"

    try:
        browser_app = _get_browser_app_name(browser)
        subprocess.run(
            ["open", "-a", browser_app, url],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return f"Searching Google for '{query}'."
    except Exception:
        webbrowser.open(url)
        return f"Searching Google for '{query}'."


def youtube_search(query: str, browser: str = None) -> str:
    """
    Search for something on YouTube.

    Args:
        query: What to search for on YouTube
        browser: Optional browser to use ('chrome', 'brave', etc.)
    """
    encoded = urllib.parse.quote_plus(query)
    url = f"https://www.youtube.com/results?search_query={encoded}"

    try:
        browser_app = _get_browser_app_name(browser)
        subprocess.run(
            ["open", "-a", browser_app, url],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return f"Searching YouTube for '{query}'."
    except Exception:
        webbrowser.open(url)
        return f"Searching YouTube for '{query}'."


def play_youtube_video(query: str, browser: str = None) -> str:
    """
    Search for a video on YouTube and automatically play the first result.
    
    Args:
        query: What video to play
        browser: Optional browser to use ('chrome', 'brave', etc.)
    """
    import requests
    import re
    
    encoded = urllib.parse.quote_plus(query)
    search_url = f"https://www.youtube.com/results?search_query={encoded}"
    
    try:
        html = requests.get(search_url).text
        video_ids = re.findall(r"watch\?v=(\S{11})", html)
        
        if video_ids:
            video_url = f"https://www.youtube.com/watch?v={video_ids[0]}"
            browser_app = _get_browser_app_name(browser)
            subprocess.run(
                ["open", "-a", browser_app, video_url],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return f"Playing '{query}' on YouTube."
        else:
            # Fallback to normal search
            return youtube_search(query, browser)
    except Exception as e:
        # Fallback to normal search
        return youtube_search(query, browser)


def github_search(query: str, browser: str = None) -> str:
    """
    Search on GitHub for repositories, code, or issues.

    Args:
        query: What to search for on GitHub
        browser: Optional browser to use ('chrome', 'brave', etc.)
    """
    encoded = urllib.parse.quote_plus(query)
    url = f"https://github.com/search?q={encoded}"

    try:
        browser_app = _get_browser_app_name(browser)
        subprocess.run(
            ["open", "-a", browser_app, url],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return f"Searching GitHub for '{query}'."
    except Exception:
        webbrowser.open(url)
        return f"Searching GitHub for '{query}'."


def stackoverflow_search(query: str, browser: str = None) -> str:
    """
    Search StackOverflow for programming questions.

    Args:
        query: The programming question to search for
        browser: Optional browser to use ('chrome', 'brave', etc.)
    """
    encoded = urllib.parse.quote_plus(query)
    url = f"https://stackoverflow.com/search?q={encoded}"

    try:
        browser_app = _get_browser_app_name(browser)
        subprocess.run(
            ["open", "-a", browser_app, url],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return f"Searching StackOverflow for '{query}'."
    except Exception:
        webbrowser.open(url)
        return f"Searching StackOverflow for '{query}'."


def search_specific_website(website: str, query: str, browser: str = "default") -> str:
    """Search for specific content on a specific website using a Google site search."""
    return google_search(f"site:{website} {query}", browser)


# ── Tool definitions for Gemini function calling ─────────────
BROWSER_TOOLS = [
    {
        "name": "open_website",
        "description": (
            "Open a website in the browser. Supports shortcut names like 'youtube', "
            "'github', 'gmail', 'linkedin', 'reddit', 'netflix', etc. "
            "Also accepts full URLs."
        ),
        "function": open_website,
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL or site name to open (e.g., 'youtube', 'github', 'https://example.com')",
                },
                "browser": {
                    "type": "string",
                    "enum": ["chrome", "brave", "safari", "firefox", "arc", "default"],
                    "description": "Which browser to use",
                }
            },
            "required": ["url"],
        },
    },
    {
        "name": "google_search",
        "description": "Search Google for any query. Opens the search results in the browser.",
        "function": google_search,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                },
                "browser": {
                    "type": "string",
                    "enum": ["chrome", "brave", "safari", "firefox", "arc", "default"],
                    "description": "Which browser to use",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "youtube_search",
        "description": "Search YouTube for videos on a topic.",
        "function": youtube_search,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for on YouTube",
                },
                "browser": {
                    "type": "string",
                    "enum": ["chrome", "brave", "safari", "firefox", "arc", "default"],
                    "description": "Which browser to use",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "play_youtube_video",
        "description": "Search for a video on YouTube and automatically start playing it. ONLY use this if the user wants to play a video/song on YouTube. Do NOT use this for playing movies or content on other platforms (like Netflix, Netmirror, Amazon, etc).",
        "function": play_youtube_video,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What video or song to play on YouTube",
                },
                "browser": {
                    "type": "string",
                    "enum": ["chrome", "brave", "safari", "firefox", "arc", "default"],
                    "description": "Which browser to use",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "github_search",
        "description": "Search GitHub for repositories, code, or projects.",
        "function": github_search,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for on GitHub",
                },
                "browser": {
                    "type": "string",
                    "enum": ["chrome", "brave", "safari", "firefox", "arc", "default"],
                    "description": "Which browser to use",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "stackoverflow_search",
        "description": "Search StackOverflow for programming questions and solutions.",
        "function": stackoverflow_search,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The programming question to search for",
                },
                "browser": {
                    "type": "string",
                    "enum": ["chrome", "brave", "safari", "firefox", "arc", "default"],
                    "description": "Which browser to use",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_specific_website",
        "description": "Search for specific content (like a movie, product, or article) on a specific website using a Google site search.",
        "function": search_specific_website,
        "parameters": {
            "type": "object",
            "properties": {
                "website": {
                    "type": "string",
                    "description": "The website name or domain (e.g., 'netmirror', 'netflix.com')",
                },
                "query": {
                    "type": "string",
                    "description": "The content to search for (e.g., 'Harry Potter', 'iPhone')",
                },
                "browser": {
                    "type": "string",
                    "enum": ["chrome", "brave", "safari", "firefox", "arc", "default"],
                    "description": "Which browser to use",
                }
            },
            "required": ["website", "query"],
        },
    },
]
