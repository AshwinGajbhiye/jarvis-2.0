# Jarvis AI — Unified Web & Multi-Platform Job Search Skill
# Searches across the open web, job aggregators, startup boards, and company career pages.
# Also extracts hiring manager / HR / recruiter contact emails for cold outreach.

import re
import urllib.parse
from typing import List, Dict, Any, Optional

import requests
from bs4 import BeautifulSoup

from config import Config

# In-memory store for web job results
_cached_web_jobs: List[Dict[str, Any]] = []

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def get_cached_web_jobs() -> List[Dict[str, Any]]:
    global _cached_web_jobs
    return _cached_web_jobs


def search_web_jobs(
    job_title: str = "",
    location: str = "",
    keywords: str = "",
    platform: str = "all",
    max_results: int = 5,
) -> str:
    """
    Search the open web for job openings across company career pages, Indeed, Glassdoor,
    Wellfound, Instahyre, and job boards.

    Args:
        job_title: Target position (e.g. 'Full Stack Engineer', 'Python AI Developer')
        location: Target location (e.g. 'Remote', 'Pune', 'Bangalore', 'USA')
        keywords: Specific required skills or tech stack (e.g. 'FastAPI React', 'PyTorch')
        platform: Filter: 'all', 'linkedin', 'indeed', 'wellfound', 'careers'
        max_results: Max items to return (default 5, max 10)
    """
    global _cached_web_jobs

    if not job_title:
        job_title = Config.LINKEDIN_JOB_TITLE or "Software Engineer"
    if not location:
        location = Config.LINKEDIN_JOB_LOCATION or "Remote"

    query_parts = [f'"{job_title}"', f'"{location}"']
    if keywords:
        query_parts.append(keywords)

    if platform == "linkedin":
        query_parts.append("site:linkedin.com/jobs")
    elif platform == "indeed":
        query_parts.append("site:indeed.com")
    elif platform == "wellfound":
        query_parts.append("site:wellfound.com")
    elif platform == "careers":
        query_parts.append('("careers" OR "we are hiring" OR "apply now")')
    else:
        query_parts.append('("apply" OR "job" OR "careers")')

    query = " ".join(query_parts)
    max_results = min(max(1, max_results), 10)

    results = []

    # Attempt 1: ddgs package
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results * 2):
                results.append(r)
    except Exception:
        # Attempt 2: duckduckgo_search fallback
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results * 2):
                    results.append(r)
        except Exception:
            pass

    # Attempt 3: Direct HTTP search fallback if ddgs unavailable
    if not results:
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for link in soup.find_all("a", class_="result__url"):
                    href = link.get("href", "")
                    title_elem = link.find_parent("div", class_="result__body")
                    title = title_elem.find("a", class_="result__title").get_text(strip=True) if title_elem else "Job Opening"
                    snippet = title_elem.find("a", class_="result__snippet").get_text(strip=True) if title_elem else ""
                    results.append({"title": title, "href": href, "body": snippet})
                    if len(results) >= max_results:
                        break
        except Exception:
            pass

    if not results:
        return f"No job postings found on the web for '{query}'. Try simplifying keywords or broadening location."

    # Parse and normalize results
    parsed_jobs: List[Dict[str, Any]] = []
    seen_urls = set()

    for r in results:
        url = r.get("href") or r.get("link", "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        raw_title = r.get("title", "Job Posting")
        snippet = r.get("body") or r.get("snippet", "")

        # Try to infer company name from title or snippet
        company = "Company"
        if " at " in raw_title:
            company = raw_title.split(" at ")[-1].split("|")[0].split("-")[0].strip()
        elif " - " in raw_title:
            parts = raw_title.split(" - ")
            if len(parts) > 1:
                company = parts[1].split("|")[0].strip()

        parsed_jobs.append({
            "index": len(parsed_jobs) + 1,
            "title": raw_title,
            "company": company,
            "url": url,
            "snippet": snippet[:220] + ("..." if len(snippet) > 220 else ""),
        })

        if len(parsed_jobs) >= max_results:
            break

    _cached_web_jobs = parsed_jobs

    lines = [
        f"### 🌐 Web Job Search Results for **'{job_title}'** ({location})\n",
        f"Found **{len(parsed_jobs)}** relevant opportunities:\n",
    ]

    for j in parsed_jobs:
        lines.append(
            f"**{j['index']}. {j['title']}**\n"
            f"   - 🏢 **Inferred Company**: {j['company']}\n"
            f"   - 🔗 **URL**: {j['url']}\n"
            f"   - 📝 **Preview**: _{j['snippet']}_\n"
            f"   - 💡 *Say 'Find contacts for {j['company']}' or 'Draft cold email for job #{j['index']}'*\n"
        )

    return "\n".join(lines)


def find_company_contacts(company_name: str, company_domain: str = "") -> str:
    """
    Search for recruitment, HR, talent acquisition, or hiring manager contact emails
    for a target company to enable cold outreach.

    Args:
        company_name: Name of the company (e.g., 'Swiggy', 'Postman', 'Razorpay')
        company_domain: Optional website domain (e.g., 'postman.com')
    """
    if not company_name:
        return "Please specify a company name, Sir."

    # Build search query for recruitment emails
    domain_part = f"site:{company_domain}" if company_domain else f'"{company_name}"'
    query = f'{domain_part} ("careers" OR "jobs" OR "recruiting" OR "hr") ("@") ("email" OR "contact")'

    found_emails = set()
    snippets = []

    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=6):
                body = (r.get("body") or "") + " " + (r.get("title") or "")
                # Extract emails
                emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", body)
                for email in emails:
                    # Filter out image/code false positives
                    if not any(email.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"]):
                        found_emails.add(email.lower())
                snippets.append(r.get("body", ""))
    except Exception:
        pass

    # Generic career mail fallback suggestions
    guessed_domain = company_domain or (company_name.lower().replace(" ", "").replace(",", "").replace(".", "") + ".com")
    standard_suggestions = [
        f"careers@{guessed_domain}",
        f"jobs@{guessed_domain}",
        f"talent@{guessed_domain}",
        f"hr@{guessed_domain}",
    ]

    lines = [f"### 🔎 Contact & Email Intelligence for **{company_name}**:\n"]

    if found_emails:
        lines.append("**Verified Public Emails Found:**")
        for em in sorted(list(found_emails))[:5]:
            lines.append(f"- ✉️ `{em}`")
        lines.append("")
    else:
        lines.append("No directly indexed personal recruiter emails were publicly exposed on the web.\n")

    lines.append("**Common Corporate Talent Mailboxes for Outreach:**")
    for em in standard_suggestions[:3]:
        lines.append(f"- 📬 `{em}`")

    lines.append(
        f"\n💡 *You can command: 'Draft cold email to {list(found_emails)[0] if found_emails else standard_suggestions[0]} "
        f"for {company_name}'*"
    )

    return "\n".join(lines)


# ── Tool Definitions for Gemini Function Calling ─────────────
JOB_SEARCH_TOOLS = [
    {
        "name": "search_web_jobs",
        "description": (
            "Search for jobs across the open web, startup boards (Wellfound), Indeed, and company career pages. "
            "Use this to find opportunities beyond LinkedIn or when broader market research is needed."
        ),
        "function": search_web_jobs,
        "parameters": {
            "type": "object",
            "properties": {
                "job_title": {"type": "string", "description": "Target job title (e.g. 'Python Developer', 'AI Engineer')"},
                "location": {"type": "string", "description": "Location preference or 'Remote'"},
                "keywords": {"type": "string", "description": "Specific skills or keywords (e.g. 'FastAPI', 'PyTorch')"},
                "platform": {
                    "type": "string",
                    "enum": ["all", "linkedin", "indeed", "wellfound", "careers"],
                    "description": "Platform filter",
                },
                "max_results": {"type": "integer", "description": "Max results to return (default 5)"},
            },
        },
    },
    {
        "name": "find_company_contacts",
        "description": (
            "Find public recruitment, HR, or hiring manager contact emails for a target company "
            "to initiate cold email outreach."
        ),
        "function": find_company_contacts,
        "parameters": {
            "type": "object",
            "properties": {
                "company_name": {"type": "string", "description": "Target company name (e.g. 'Postman', 'Swiggy')"},
                "company_domain": {"type": "string", "description": "Optional official website domain (e.g. 'postman.com')"},
            },
            "required": ["company_name"],
        },
    },
]
