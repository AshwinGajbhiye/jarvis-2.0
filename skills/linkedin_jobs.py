# Jarvis AI — LinkedIn Job Search Skill
# Searches for job opportunities using Google site-search on LinkedIn.
# This approach is safe (no LinkedIn login needed) and won't risk account bans.

import subprocess
import urllib.parse
import webbrowser

from config import Config


def search_linkedin_jobs(
    job_title: str = "",
    location: str = "",
    experience_level: str = "",
) -> str:
    """
    Search for LinkedIn job postings using Google site-search.

    Args:
        job_title: Job title to search for (e.g., 'Python Developer', 'Frontend Engineer')
        location: Location preference (e.g., 'Pune', 'Remote', 'India')
        experience_level: Experience level (e.g., 'entry level', 'mid level', 'senior')

    Returns:
        Status message
    """
    # Use defaults from config if not provided
    if not job_title:
        job_title = Config.LINKEDIN_JOB_TITLE
    if not location:
        location = Config.LINKEDIN_JOB_LOCATION

    # Build the search query
    query_parts = [f"site:linkedin.com/jobs", f'"{job_title}"']
    if location:
        query_parts.append(location)
    if experience_level:
        query_parts.append(experience_level)

    query = " ".join(query_parts)
    encoded = urllib.parse.quote_plus(query)
    url = f"https://www.google.com/search?q={encoded}"

    try:
        browser_app = _get_browser_app()
        subprocess.run(
            ["open", "-a", browser_app, url],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return (
            f"Searching LinkedIn jobs for '{job_title}' "
            f"{'in ' + location if location else ''} "
            f"{'(' + experience_level + ')' if experience_level else ''}. "
            f"Opening results in {browser_app}."
        )
    except Exception:
        webbrowser.open(url)
        return f"Searching LinkedIn jobs for '{job_title}'. Opening results in your browser."


def search_linkedin_direct(
    job_title: str = "",
    location: str = "",
) -> str:
    """
    Open LinkedIn's job search page directly with filters.
    Note: Requires LinkedIn to be logged in via browser.

    Args:
        job_title: Job title to search for
        location: Location preference
    """
    if not job_title:
        job_title = Config.LINKEDIN_JOB_TITLE
    if not location:
        location = Config.LINKEDIN_JOB_LOCATION

    keywords = urllib.parse.quote_plus(job_title)
    loc = urllib.parse.quote_plus(location)
    url = f"https://www.linkedin.com/jobs/search/?keywords={keywords}&location={loc}"

    try:
        browser_app = _get_browser_app()
        subprocess.run(
            ["open", "-a", browser_app, url],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return f"Opening LinkedIn jobs page for '{job_title}' in {location}."
    except Exception:
        webbrowser.open(url)
        return f"Opening LinkedIn jobs page for '{job_title}'."


def search_jobs_on_other_platforms(
    job_title: str = "",
    location: str = "",
    platform: str = "all",
) -> str:
    """
    Search for jobs across multiple platforms.

    Args:
        job_title: Job title to search for
        location: Location preference
        platform: Platform to search on ('naukri', 'indeed', 'glassdoor', or 'all')
    """
    if not job_title:
        job_title = Config.LINKEDIN_JOB_TITLE
    if not location:
        location = Config.LINKEDIN_JOB_LOCATION

    platforms_searched = []
    browser_app = _get_browser_app()

    urls = {}
    if platform in ("naukri", "all"):
        kw = urllib.parse.quote_plus(job_title)
        loc = urllib.parse.quote_plus(location)
        urls["Naukri"] = f"https://www.naukri.com/{kw.replace('+', '-')}-jobs-in-{loc.replace('+', '-')}"

    if platform in ("indeed", "all"):
        kw = urllib.parse.quote_plus(job_title)
        loc = urllib.parse.quote_plus(location)
        urls["Indeed"] = f"https://www.indeed.com/jobs?q={kw}&l={loc}"

    if platform in ("glassdoor", "all"):
        kw = urllib.parse.quote_plus(job_title)
        urls["Glassdoor"] = f"https://www.glassdoor.co.in/Job/jobs.htm?sc.keyword={kw}"

    for name, url in urls.items():
        try:
            subprocess.run(
                ["open", "-a", browser_app, url],
                capture_output=True,
                text=True,
                timeout=10,
            )
            platforms_searched.append(name)
        except Exception:
            webbrowser.open(url)
            platforms_searched.append(name)

    if platforms_searched:
        return f"Searching for '{job_title}' jobs on: {', '.join(platforms_searched)}."
    return "Could not open any job platforms."


def _get_browser_app() -> str:
    """Get browser app name from config."""
    browser = Config.DEFAULT_BROWSER.lower()
    if browser == "brave":
        return "Brave Browser"
    elif browser == "safari":
        return "Safari"
    elif browser == "firefox":
        return "Firefox"
    return "Google Chrome"


# ── Tool definitions for Gemini function calling ─────────────
LINKEDIN_TOOLS = [
    {
        "name": "search_linkedin_jobs",
        "description": (
            "Search for job opportunities on LinkedIn using Google search. "
            "Safe and doesn't require LinkedIn login. Use when the user asks "
            "to find jobs, search for opportunities, or check LinkedIn for positions."
        ),
        "function": search_linkedin_jobs,
        "parameters": {
            "type": "object",
            "properties": {
                "job_title": {
                    "type": "string",
                    "description": "Job title to search for (e.g., 'Python Developer', 'Frontend Engineer')",
                },
                "location": {
                    "type": "string",
                    "description": "Location preference (e.g., 'Pune', 'Remote', 'India')",
                },
                "experience_level": {
                    "type": "string",
                    "description": "Experience level filter (e.g., 'entry level', 'mid level', 'senior')",
                },
            },
        },
    },
    {
        "name": "search_linkedin_direct",
        "description": (
            "Open LinkedIn's job search page directly with filters. "
            "The user needs to be logged into LinkedIn in their browser."
        ),
        "function": search_linkedin_direct,
        "parameters": {
            "type": "object",
            "properties": {
                "job_title": {
                    "type": "string",
                    "description": "Job title to search for",
                },
                "location": {
                    "type": "string",
                    "description": "Location preference",
                },
            },
        },
    },
    {
        "name": "search_jobs_on_other_platforms",
        "description": (
            "Search for jobs across multiple platforms like Naukri, Indeed, and Glassdoor. "
            "Use when the user wants to search broadly across job boards."
        ),
        "function": search_jobs_on_other_platforms,
        "parameters": {
            "type": "object",
            "properties": {
                "job_title": {
                    "type": "string",
                    "description": "Job title to search for",
                },
                "location": {
                    "type": "string",
                    "description": "Location preference",
                },
                "platform": {
                    "type": "string",
                    "description": "Specific platform ('naukri', 'indeed', 'glassdoor') or 'all'",
                    "enum": ["naukri", "indeed", "glassdoor", "all"],
                },
            },
        },
    },
]
