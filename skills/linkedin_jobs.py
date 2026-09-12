# Jarvis AI — LinkedIn Job Search & Extraction Skill
# Searches and extracts live LinkedIn job postings using LinkedIn public guest endpoints.
# Does not require LinkedIn credentials or browser automation, preventing account risk.
# Also supports opening job search in browser if requested.

import subprocess
import urllib.parse
import webbrowser
import re
from typing import List, Dict, Any, Optional

import requests
from bs4 import BeautifulSoup

from config import Config

# Cache the latest search results for easy referencing (e.g., "job #1", "job #2")
_last_found_jobs: List[Dict[str, Any]] = []

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def get_cached_jobs() -> List[Dict[str, Any]]:
    """Return recently found jobs from memory."""
    global _last_found_jobs
    return _last_found_jobs


def search_linkedin_jobs_data(
    job_title: str = "",
    location: str = "",
    experience_level: str = "",
    max_results: int = 5,
) -> str:
    """
    Search and fetch real job opportunities directly from LinkedIn without requiring login.
    Returns structured job cards with titles, company names, locations, and direct links.

    Args:
        job_title: Target role (e.g., 'Python Developer', 'AI Engineer', 'Full Stack')
        location: Location preference (e.g., 'Remote', 'Pune', 'Bangalore', 'United States')
        experience_level: Experience filter (e.g., 'Entry Level', 'Mid', 'Senior')
        max_results: Number of postings to retrieve (default: 5, max: 10)
    """
    global _last_found_jobs

    if not job_title:
        job_title = Config.LINKEDIN_JOB_TITLE or "Software Developer"
    if not location:
        location = Config.LINKEDIN_JOB_LOCATION or "Remote"

    keywords = job_title
    if experience_level:
        keywords = f"{job_title} {experience_level}"

    query_encoded = urllib.parse.quote_plus(keywords)
    loc_encoded = urllib.parse.quote_plus(location)
    max_results = min(max(1, max_results), 10)

    url = (
        f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?"
        f"keywords={query_encoded}&location={loc_encoded}&start=0"
    )

    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        response = requests.get(url, headers=headers, timeout=12)
        if response.status_code != 200:
            return f"⚠️ LinkedIn returned status code {response.status_code}. You can also try searching the wider web."

        soup = BeautifulSoup(response.text, "html.parser")
        job_items = soup.find_all("li")

        if not job_items:
            # Fallback to direct search URL
            return f"No direct listings found on LinkedIn for '{job_title}' in '{location}'. Try widening your location or search terms."

        extracted_jobs: List[Dict[str, Any]] = []

        for item in job_items:
            if len(extracted_jobs) >= max_results:
                break

            title_elem = item.find("h3", class_=re.compile(r"base-search-card__title", re.I)) or item.find("h3")
            company_elem = item.find("h4", class_=re.compile(r"base-search-card__subtitle", re.I)) or item.find("h4")
            location_elem = item.find("span", class_=re.compile(r"job-search-card__location", re.I))
            link_elem = item.find("a", class_=re.compile(r"base-card__full-link", re.I)) or item.find("a")
            time_elem = item.find("time")

            title = title_elem.get_text(strip=True) if title_elem else "Role Not Specified"
            company = company_elem.get_text(strip=True) if company_elem else "Company Confidential"
            loc = location_elem.get_text(strip=True) if location_elem else location
            post_time = time_elem.get_text(strip=True) if time_elem else "Recently"

            link = ""
            job_id = ""
            if link_elem and "href" in link_elem.attrs:
                link = link_elem["href"].split("?")[0]
                # Extract numerical job id
                id_match = re.search(r"(\d{8,})", link)
                if id_match:
                    job_id = id_match.group(1)

            extracted_jobs.append({
                "index": len(extracted_jobs) + 1,
                "title": title,
                "company": company,
                "location": loc,
                "posted": post_time,
                "url": link,
                "job_id": job_id,
            })

        _last_found_jobs = extracted_jobs

        lines = [
            f"### 💼 LinkedIn Job Opportunities for **'{job_title}'** ({location})\n",
            f"Found **{len(extracted_jobs)}** active listings:\n",
        ]

        for j in extracted_jobs:
            lines.append(
                f"**{j['index']}. {j['title']}** at **{j['company']}**\n"
                f"   - 📍 **Location**: {j['location']} ({j['posted']})\n"
                f"   - 🔗 **Link**: [{j['title']}]({j['url']})\n"
                f"   - 💡 *Say 'Show details for job #{j['index']}' or 'Draft cold email for job #{j['index']}'*\n"
            )

        return "\n".join(lines)

    except requests.RequestException as e:
        return f"⚠️ Network error while querying LinkedIn: {e}"
    except Exception as e:
        return f"⚠️ Could not complete LinkedIn job search: {e}"


def get_linkedin_job_details(job_reference: str) -> str:
    """
    Fetch and summarize full job description and requirements for a specific LinkedIn job.

    Args:
        job_reference: Can be an index like '#1', 'job 2', a LinkedIn URL, or a numeric job ID.
    """
    global _last_found_jobs

    job_id = ""
    job_info = None

    # Check if reference is an index from cached jobs (e.g. "1", "#1", "job 1")
    index_match = re.search(r"\b(\d+)\b", str(job_reference))
    if index_match and _last_found_jobs:
        idx = int(index_match.group(1))
        if 1 <= idx <= len(_last_found_jobs):
            job_info = _last_found_jobs[idx - 1]
            job_id = job_info.get("job_id", "")

    # If not index, check if numeric ID or URL
    if not job_id:
        if str(job_reference).isdigit():
            job_id = str(job_reference)
        else:
            id_match = re.search(r"(\d{8,})", str(job_reference))
            if id_match:
                job_id = id_match.group(1)

    if not job_id:
        return "Could not determine the LinkedIn Job ID. Please provide a job index (e.g., 'job #1') or the full LinkedIn job URL."

    detail_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}

    try:
        res = requests.get(detail_url, headers=headers, timeout=12)
        if res.status_code != 200:
            return f"Unable to fetch job details from LinkedIn (Status: {res.status_code})."

        soup = BeautifulSoup(res.text, "html.parser")
        desc_elem = soup.find("div", class_=re.compile(r"show-more-less-html__markup", re.I))

        description = ""
        if desc_elem:
            # Clean up text
            for tag in desc_elem(["script", "style"]):
                tag.decompose()
            description = desc_elem.get_text(separator="\n", strip=True)

        company = job_info.get("company") if job_info else "Company"
        title = job_info.get("title") if job_info else "Role"
        url = job_info.get("url") if job_info else f"https://www.linkedin.com/jobs/view/{job_id}"

        # Clean description length for AI/voice context
        cleaned_desc = description[:1500] if len(description) > 1500 else description

        result = [
            f"### 📋 Job Specifications: **{title}** at **{company}**",
            f"🔗 **URL**: {url}\n",
            "**Key Details & Description:**",
            cleaned_desc or "No detailed description text provided.",
            "\n💡 *You can now command: 'Draft a cold email for this role to careers@[company].com'*",
        ]
        return "\n".join(result)

    except Exception as e:
        return f"Error extracting job details: {e}"


def search_linkedin_jobs(
    job_title: str = "",
    location: str = "",
    experience_level: str = "",
) -> str:
    """
    Search for LinkedIn job postings and open results in the browser.

    Args:
        job_title: Job title to search for (e.g., 'Python Developer', 'Frontend Engineer')
        location: Location preference (e.g., 'Pune', 'Remote', 'India')
        experience_level: Experience level (e.g., 'entry level', 'mid level', 'senior')
    """
    if not job_title:
        job_title = Config.LINKEDIN_JOB_TITLE
    if not location:
        location = Config.LINKEDIN_JOB_LOCATION

    query_parts = [f"site:linkedin.com/jobs", f'"{job_title}"']
    if location:
        query_parts.append(location)
    if experience_level:
        query_parts.append(experience_level)

    query = " ".join(query_parts)
    encoded = urllib.parse.quote_plus(query)
    url = f"https://www.google.com/search?q={encoded}"

    browser_app = _get_browser_app()
    try:
        subprocess.run(
            ["open", "-a", browser_app, url],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return f"Opening LinkedIn search results for '{job_title}' in {browser_app}."
    except Exception:
        webbrowser.open(url)
        return f"Opening LinkedIn search results for '{job_title}' in browser."


def search_linkedin_direct(
    job_title: str = "",
    location: str = "",
) -> str:
    """
    Open LinkedIn's job search page directly with filters in the browser.
    """
    if not job_title:
        job_title = Config.LINKEDIN_JOB_TITLE
    if not location:
        location = Config.LINKEDIN_JOB_LOCATION

    keywords = urllib.parse.quote_plus(job_title)
    loc = urllib.parse.quote_plus(location)
    url = f"https://www.linkedin.com/jobs/search/?keywords={keywords}&location={loc}"

    browser_app = _get_browser_app()
    try:
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
    Search for jobs across multiple platforms like Naukri, Indeed, and Glassdoor in browser.
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


# ── Tool Definitions for Gemini Function Calling ─────────────
LINKEDIN_TOOLS = [
    {
        "name": "search_linkedin_jobs_data",
        "description": (
            "Search and fetch real-time job listings directly from LinkedIn without requiring login. "
            "Returns structured job postings (title, company, location, link, job ID) for cold outreach or review. "
            "ALWAYS use this when the user asks to find, search, or look up LinkedIn jobs."
        ),
        "function": search_linkedin_jobs_data,
        "parameters": {
            "type": "object",
            "properties": {
                "job_title": {
                    "type": "string",
                    "description": "Job title or keywords (e.g. 'Python Developer', 'Full Stack Engineer')",
                },
                "location": {
                    "type": "string",
                    "description": "Location or 'Remote' (e.g. 'Pune', 'Remote', 'India')",
                },
                "experience_level": {
                    "type": "string",
                    "description": "Optional experience filter (e.g. 'entry level', 'mid-senior')",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of jobs to retrieve (default: 5, max: 10)",
                },
            },
        },
    },
    {
        "name": "get_linkedin_job_details",
        "description": (
            "Fetch the full job description, qualifications, and requirements for a specific LinkedIn job. "
            "Can accept a job index (e.g. '#1', 'job 2'), a job URL, or a numeric job ID."
        ),
        "function": get_linkedin_job_details,
        "parameters": {
            "type": "object",
            "properties": {
                "job_reference": {
                    "type": "string",
                    "description": "Job index (e.g. '#1', '2'), job URL, or numerical job ID",
                },
            },
            "required": ["job_reference"],
        },
    },
    {
        "name": "search_linkedin_jobs",
        "description": "Open a Google site-search for LinkedIn jobs in the user's web browser.",
        "function": search_linkedin_jobs,
        "parameters": {
            "type": "object",
            "properties": {
                "job_title": {"type": "string", "description": "Job title to search for"},
                "location": {"type": "string", "description": "Location preference"},
            },
        },
    },
    {
        "name": "search_linkedin_direct",
        "description": "Open LinkedIn's job search page directly with filters in the user's browser.",
        "function": search_linkedin_direct,
        "parameters": {
            "type": "object",
            "properties": {
                "job_title": {"type": "string", "description": "Job title to search for"},
                "location": {"type": "string", "description": "Location preference"},
            },
        },
    },
    {
        "name": "search_jobs_on_other_platforms",
        "description": "Open Naukri, Indeed, or Glassdoor job search pages in the browser.",
        "function": search_jobs_on_other_platforms,
        "parameters": {
            "type": "object",
            "properties": {
                "job_title": {"type": "string", "description": "Job title to search for"},
                "location": {"type": "string", "description": "Location preference"},
                "platform": {
                    "type": "string",
                    "enum": ["naukri", "indeed", "glassdoor", "all"],
                    "description": "Target job board",
                },
            },
        },
    },
]
