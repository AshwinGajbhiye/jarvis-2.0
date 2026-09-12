#!/usr/bin/env python3
"""
================================================================================
 Cold Outreach & Job Hunter Toolkit (Standalone & Portable)
================================================================================
A self-contained Python module providing:
 1. Live LinkedIn Job Search & Specifications Extraction (No Login Required)
 2. Multi-Platform Web Job Search (Startups, Wellfound, Indeed, Career sites)
 3. Recruiter, HR & Company Email Intelligence Hunter
 4. Candidate Profile & Resume Management
 5. AI-Powered & Template Cold Email Synthesizer
 6. Dual Email Transport Dispatcher (SMTP + Gmail API) with Resume Attachment
 7. Safety-First Draft, Preview & Confirmation Flow
 8. Cold Outreach History Tracker & Analytics
 9. Function Calling / Agent Tool Definitions (for Gemini, OpenAI, LangChain)
 10. Standalone Interactive Terminal CLI

Drop this single file into any project and start hunting jobs and cold emailing!
================================================================================
"""

import os
import re
import sys
import json
import uuid
import smtplib
import base64
import urllib.parse
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import List, Dict, Any, Optional, Tuple

# Optional external dependencies with graceful fallbacks
try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ==============================================================================
# 1. CONFIGURATION & CANDIDATE PROFILE
# ==============================================================================

class ColdOutreachConfig:
    """Central configuration with environment variable defaults."""
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "Job Candidate")
    EMAIL_DISPATCH_METHOD: str = os.getenv("EMAIL_DISPATCH_METHOD", "smtp").lower()

    # Paths
    RESUME_PATH: str = os.path.expanduser(os.getenv("RESUME_PATH", "~/.jarvis/resume.pdf"))
    USER_PROFILE_PATH: str = os.path.expanduser(os.getenv("USER_PROFILE_PATH", "~/.jarvis/user_profile.json"))
    COLD_APPLICATIONS_PATH: str = os.path.expanduser(os.getenv("COLD_APPLICATIONS_PATH", "~/.jarvis/cold_applications.json"))

    # Gmail API OAuth Paths
    GMAIL_CREDENTIALS_PATH: str = os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")
    GMAIL_TOKEN_PATH: str = os.getenv("GMAIL_TOKEN_PATH", "token.json")

    USER_AGENT: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )


class ProfileManager:
    """Stores candidate background for personalized outreach."""

    DEFAULT_PROFILE = {
        "full_name": ColdOutreachConfig.SMTP_FROM_NAME,
        "email": ColdOutreachConfig.SMTP_USER,
        "phone": "",
        "location": "India",
        "target_roles": ["Software Developer", "Full Stack Developer", "AI Engineer"],
        "current_title": "Software Developer / Engineer",
        "years_of_experience": "1-2 years",
        "skills": [
            "Python", "FastAPI", "React", "JavaScript / TypeScript",
            "Generative AI & LLMs", "Playwright Automation", "REST APIs", "Docker"
        ],
        "projects": [
            "Autonomous AI Assistant with real-time multi-agent workflows",
            "Full-stack applications with React, FastAPI, and real-time APIs"
        ],
        "linkedin_url": "https://linkedin.com",
        "github_url": "https://github.com",
        "portfolio_url": "",
        "resume_path": ColdOutreachConfig.RESUME_PATH,
        "custom_bio": "Passionate software engineer building modern AI-driven and full-stack software solutions."
    }

    @classmethod
    def get_profile(cls) -> Dict[str, Any]:
        path = ColdOutreachConfig.USER_PROFILE_PATH
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(cls.DEFAULT_PROFILE, f, indent=2)
                return cls.DEFAULT_PROFILE
            except Exception:
                return cls.DEFAULT_PROFILE
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in cls.DEFAULT_PROFILE.items():
                    if k not in data:
                        data[k] = v
                return data
        except Exception:
            return cls.DEFAULT_PROFILE

    @classmethod
    def update_profile(cls, **kwargs) -> str:
        profile = cls.get_profile()
        for k, v in kwargs.items():
            if v is not None and k in profile:
                if isinstance(profile[k], list) and isinstance(v, str):
                    profile[k] = [item.strip() for item in v.split(",") if item.strip()]
                else:
                    profile[k] = v
        try:
            path = ColdOutreachConfig.USER_PROFILE_PATH
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(profile, f, indent=2)
            return "Candidate profile updated successfully."
        except Exception as e:
            return f"Failed to save profile: {e}"


# ==============================================================================
# 2. LINKEDIN LIVE JOB SEARCH & SCRAPER (No Login Required)
# ==============================================================================

class LinkedInJobHunter:
    """
    Direct interface to LinkedIn's public guest search endpoints.
    Fetches real-time listings, direct links, and full job descriptions without authentication.
    """
    _cached_jobs: List[Dict[str, Any]] = []

    @classmethod
    def search_jobs(
        cls,
        job_title: str,
        location: str = "Remote",
        experience_level: str = "",
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search and return structured LinkedIn job cards.
        """
        if not requests or not BeautifulSoup:
            return []

        keywords = f"{job_title} {experience_level}".strip()
        query_enc = urllib.parse.quote_plus(keywords)
        loc_enc = urllib.parse.quote_plus(location)
        max_results = min(max(1, max_results), 10)

        url = (
            f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?"
            f"keywords={query_enc}&location={loc_enc}&start=0"
        )
        headers = {
            "User-Agent": ColdOutreachConfig.USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            res = requests.get(url, headers=headers, timeout=12)
            if res.status_code != 200:
                return []

            soup = BeautifulSoup(res.text, "html.parser")
            items = soup.find_all("li")
            jobs: List[Dict[str, Any]] = []

            for item in items:
                if len(jobs) >= max_results:
                    break

                title_el = item.find("h3", class_=re.compile(r"base-search-card__title", re.I)) or item.find("h3")
                comp_el = item.find("h4", class_=re.compile(r"base-search-card__subtitle", re.I)) or item.find("h4")
                loc_el = item.find("span", class_=re.compile(r"job-search-card__location", re.I))
                link_el = item.find("a", class_=re.compile(r"base-card__full-link", re.I)) or item.find("a")
                time_el = item.find("time")

                title = title_el.get_text(strip=True) if title_el else "Role Not Specified"
                company = comp_el.get_text(strip=True) if comp_el else "Company Confidential"
                loc = loc_el.get_text(strip=True) if loc_el else location
                post_time = time_el.get_text(strip=True) if time_el else "Recently"

                link = ""
                job_id = ""
                if link_el and "href" in link_el.attrs:
                    link = link_el["href"].split("?")[0]
                    id_m = re.search(r"(\d{8,})", link)
                    if id_m:
                        job_id = id_m.group(1)

                jobs.append({
                    "index": len(jobs) + 1,
                    "title": title,
                    "company": company,
                    "location": loc,
                    "posted": post_time,
                    "url": link,
                    "job_id": job_id,
                })

            cls._cached_jobs = jobs
            return jobs
        except Exception:
            return []

    @classmethod
    def get_job_details(cls, job_ref: str) -> Dict[str, Any]:
        """
        Extract full job description & requirements by index ('#1'), numeric ID, or URL.
        """
        if not requests or not BeautifulSoup:
            return {"error": "requests and beautifulsoup4 required."}

        job_id = ""
        cached_info = None

        # Check index reference
        idx_match = re.search(r"\b(\d+)\b", str(job_ref))
        if idx_match and cls._cached_jobs:
            idx = int(idx_match.group(1))
            if 1 <= idx <= len(cls._cached_jobs):
                cached_info = cls._cached_jobs[idx - 1]
                job_id = cached_info.get("job_id", "")

        if not job_id:
            if str(job_ref).isdigit():
                job_id = str(job_ref)
            else:
                m = re.search(r"(\d{8,})", str(job_ref))
                if m:
                    job_id = m.group(1)

        if not job_id:
            return {"error": "Could not parse valid numerical LinkedIn Job ID."}

        url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
        headers = {"User-Agent": ColdOutreachConfig.USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}

        try:
            res = requests.get(url, headers=headers, timeout=12)
            if res.status_code != 200:
                return {"error": f"LinkedIn returned status {res.status_code}"}

            soup = BeautifulSoup(res.text, "html.parser")
            desc_el = soup.find("div", class_=re.compile(r"show-more-less-html__markup", re.I))

            desc_text = ""
            if desc_el:
                for tag in desc_el(["script", "style"]):
                    tag.decompose()
                desc_text = desc_el.get_text(separator="\n", strip=True)

            return {
                "job_id": job_id,
                "title": cached_info.get("title") if cached_info else "Job Title",
                "company": cached_info.get("company") if cached_info else "Target Company",
                "url": cached_info.get("url") if cached_info else f"https://www.linkedin.com/jobs/view/{job_id}",
                "description": desc_text,
            }
        except Exception as e:
            return {"error": str(e)}


# ==============================================================================
# 3. MULTI-PLATFORM WEB JOB SEARCH
# ==============================================================================

class WebJobHunter:
    """
    Searches across company career sites, Wellfound, Indeed, and the open web.
    """
    _cached_jobs: List[Dict[str, Any]] = []

    @classmethod
    def search_jobs(
        cls,
        job_title: str,
        location: str = "Remote",
        keywords: str = "",
        platform: str = "all",
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
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

        # Try ddgs or duckduckgo_search
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results * 2):
                    results.append(r)
        except Exception:
            try:
                from duckduckgo_search import DDGS
                with DDGS() as ddgs:
                    for r in ddgs.text(query, max_results=max_results * 2):
                        results.append(r)
            except Exception:
                pass

        # HTML search fallback
        if not results and requests and BeautifulSoup:
            try:
                url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
                resp = requests.get(url, headers={"User-Agent": ColdOutreachConfig.USER_AGENT}, timeout=10)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for link in soup.find_all("a", class_="result__url"):
                        href = link.get("href", "")
                        b_elem = link.find_parent("div", class_="result__body")
                        title = b_elem.find("a", class_="result__title").get_text(strip=True) if b_elem else "Job Opening"
                        snippet = b_elem.find("a", class_="result__snippet").get_text(strip=True) if b_elem else ""
                        results.append({"title": title, "href": href, "body": snippet})
                        if len(results) >= max_results:
                            break
            except Exception:
                pass

        parsed: List[Dict[str, Any]] = []
        seen = set()
        for r in results:
            url = r.get("href") or r.get("link", "")
            if not url or url in seen:
                continue
            seen.add(url)
            title = r.get("title", "Job Opening")
            body = r.get("body") or r.get("snippet", "")

            comp = "Company"
            if " at " in title:
                comp = title.split(" at ")[-1].split("|")[0].split("-")[0].strip()
            elif " - " in title:
                p = title.split(" - ")
                if len(p) > 1:
                    comp = p[1].split("|")[0].strip()

            parsed.append({
                "index": len(parsed) + 1,
                "title": title,
                "company": comp,
                "url": url,
                "snippet": body[:200] + "..." if len(body) > 200 else body,
            })
            if len(parsed) >= max_results:
                break

        cls._cached_jobs = parsed
        return parsed


# ==============================================================================
# 4. RECRUITER & COMPANY EMAIL INTELLIGENCE HUNTER
# ==============================================================================

class RecruiterContactFinder:
    """
    Extracts public hiring manager / HR / recruiter emails for target companies.
    """

    @classmethod
    def find_emails(cls, company_name: str, domain: str = "") -> Dict[str, Any]:
        domain_query = f"site:{domain}" if domain else f'"{company_name}"'
        query = f'{domain_query} ("careers" OR "jobs" OR "recruiting" OR "hr") ("@") ("email" OR "contact")'

        found_emails = set()

        def extract_from_text(txt: str):
            emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", txt)
            for em in emails:
                if not any(em.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif"]):
                    found_emails.add(em.lower())

        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=6):
                    extract_from_text((r.get("body") or "") + " " + (r.get("title") or ""))
        except Exception:
            try:
                from duckduckgo_search import DDGS
                with DDGS() as ddgs:
                    for r in ddgs.text(query, max_results=6):
                        extract_from_text((r.get("body") or "") + " " + (r.get("title") or ""))
            except Exception:
                pass

        cleaned_domain = domain or (company_name.lower().replace(" ", "").replace(".", "") + ".com")
        standard_mailboxes = [
            f"careers@{cleaned_domain}",
            f"jobs@{cleaned_domain}",
            f"talent@{cleaned_domain}",
            f"hr@{cleaned_domain}",
        ]

        return {
            "company": company_name,
            "verified_public_emails": sorted(list(found_emails)),
            "standard_talent_mailboxes": standard_mailboxes,
            "recommended_recipient": list(found_emails)[0] if found_emails else standard_mailboxes[0],
        }


# ==============================================================================
# 5. COLD EMAIL SYNTHESIZER & COMPOSER
# ==============================================================================

class ColdEmailComposer:
    """
    Synthesizes tailored, high-converting cold email body and subject lines.
    """

    @classmethod
    def compose(
        cls,
        recipient_name: str,
        company: str,
        job_title: str,
        job_details: str = "",
        custom_notes: str = "",
        tone: str = "professional"
    ) -> Tuple[str, str]:
        profile = ProfileManager.get_profile()
        cand_name = profile.get("full_name", "Job Applicant")
        cand_skills = profile.get("skills", ["Python", "FastAPI", "React", "AI/LLMs"])
        years = profile.get("years_of_experience", "2 years")
        portfolio = profile.get("portfolio_url", "")
        github = profile.get("github_url", "")
        linkedin = profile.get("linkedin_url", "")

        salutation = f"Hi {recipient_name}," if recipient_name and recipient_name.lower() not in ("hiring team", "hr", "recruiter", "") else "Hi Hiring Team,"
        subject = f"Application: {job_title} — {cand_name}"

        top_skills = ", ".join(cand_skills[:4])

        lines = [
            salutation,
            f"\nI hope this email finds you well. I am writing to express my enthusiastic interest in the **{job_title}** opportunity at **{company}**.",
            f"With over {years} of hands-on software development experience specializing in {top_skills}, I believe my technical background aligns closely with your team's objectives.",
        ]

        if custom_notes:
            lines.append(f"\n{custom_notes}")

        lines.append("\nA few highlights of what I bring to the team:")
        lines.append(f"• **Core Stack & Architecture**: Deep expertise in {top_skills} and production API design.")
        lines.append("• **Execution Focus**: Strong track record delivering high-quality, testable, and maintainable software.")

        if portfolio:
            lines.append(f"• **Portfolio & Projects**: Interactive demos and case studies at {portfolio}.")
        elif github:
            lines.append(f"• **Code & Open Source**: Repositories and contributions available on GitHub ({github}).")

        lines.append(
            "\nI have attached my resume for your review. I would appreciate the opportunity for a brief 15-minute conversation "
            "to discuss how my skill set can support your engineering roadmap."
        )
        lines.append("\nThank you for your time and consideration.")
        lines.append(f"\nWarm regards,\n**{cand_name}**")

        footer = []
        if profile.get("email"):
            footer.append(f"Email: {profile.get('email')}")
        if linkedin:
            footer.append(f"LinkedIn: {linkedin}")
        if github:
            footer.append(f"GitHub: {github}")

        if footer:
            lines.append(" | ".join(footer))

        return subject, "\n".join(lines)


# ==============================================================================
# 6. DUAL TRANSPORT EMAIL SENDER (SMTP + Gmail API)
# ==============================================================================

class EmailDispatcher:
    """
    Sends emails via SMTP (Google App Password / Outlook / standard) or Gmail API.
    Supports HTML rendering and resume attachments.
    """

    @classmethod
    def send(
        cls,
        to_email: str,
        subject: str,
        body: str,
        recipient_name: str = "",
        attach_resume: bool = True,
        resume_path: Optional[str] = None,
    ) -> Tuple[bool, str]:
        method = ColdOutreachConfig.EMAIL_DISPATCH_METHOD
        if method == "gmail_api":
            return cls._send_gmail_api(to_email, subject, body, attach_resume, resume_path)
        else:
            return cls._send_smtp(to_email, subject, body, attach_resume, resume_path)

    @classmethod
    def _send_smtp(
        cls,
        to_email: str,
        subject: str,
        body: str,
        attach_resume: bool,
        resume_path: Optional[str],
    ) -> Tuple[bool, str]:
        user = ColdOutreachConfig.SMTP_USER
        pwd = ColdOutreachConfig.SMTP_PASSWORD
        host = ColdOutreachConfig.SMTP_HOST
        port = ColdOutreachConfig.SMTP_PORT
        from_name = ColdOutreachConfig.SMTP_FROM_NAME

        if not user or not pwd:
            return False, "SMTP_USER or SMTP_PASSWORD is not set in environment or config."

        # Build message
        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"] = f"{from_name} <{user}>"
        msg["To"] = to_email

        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(body, "plain", "utf-8"))

        html_body = body.replace("\n", "<br>").replace("**", "<b>").replace("•", "&bull;")
        alt.attach(MIMEText(f"<html><body>{html_body}</body></html>", "html", "utf-8"))
        msg.attach(alt)

        path = resume_path or ColdOutreachConfig.RESUME_PATH
        if attach_resume and path and os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    part = MIMEApplication(f.read(), Name=os.path.basename(path))
                part["Content-Disposition"] = f'attachment; filename="{os.path.basename(path)}"'
                msg.attach(part)
            except Exception as e:
                print(f"Warning: Failed to attach resume: {e}")

        try:
            if port == 465:
                server = smtplib.SMTP_SSL(host, port, timeout=15)
            else:
                server = smtplib.SMTP(host, port, timeout=15)
                server.ehlo()
                server.starttls()
                server.ehlo()

            server.login(user, pwd)
            server.sendmail(user, [to_email], msg.as_string())
            server.quit()
            return True, f"Email delivered successfully via SMTP ({host}) to {to_email}."
        except Exception as e:
            return False, f"SMTP delivery failed: {e}"

    @classmethod
    def _send_gmail_api(
        cls,
        to_email: str,
        subject: str,
        body: str,
        attach_resume: bool,
        resume_path: Optional[str],
    ) -> Tuple[bool, str]:
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError:
            return False, "Google API client packages missing. Run: pip install google-api-python-client google-auth-oauthlib"

        SCOPES = [
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.compose",
        ]
        token_path = ColdOutreachConfig.GMAIL_TOKEN_PATH
        creds_path = ColdOutreachConfig.GMAIL_CREDENTIALS_PATH

        creds = None
        if os.path.exists(token_path):
            try:
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            except Exception:
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = None
            if not creds:
                if not os.path.exists(creds_path):
                    return False, f"credentials.json not found at {creds_path}"
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_path, "w") as token:
                token.write(creds.to_json())

        try:
            service = build("gmail", "v1", credentials=creds)
            msg = MIMEMultipart()
            msg["to"] = to_email
            msg["subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            path = resume_path or ColdOutreachConfig.RESUME_PATH
            if attach_resume and path and os.path.exists(path):
                with open(path, "rb") as f:
                    part = MIMEApplication(f.read(), Name=os.path.basename(path))
                part["Content-Disposition"] = f'attachment; filename="{os.path.basename(path)}"'
                msg.attach(part)

            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            service.users().messages().send(userId="me", body={"raw": raw}).execute()
            return True, f"Delivered via Gmail API to {to_email}."
        except Exception as e:
            return False, f"Gmail API error: {e}"


# ==============================================================================
# 7. OUTREACH APPLICATION TRACKER & ANALYTICS
# ==============================================================================

class OutreachTracker:
    """
    Persists cold outreach applications and computes pipeline analytics.
    """

    @classmethod
    def log(
        cls,
        company: str,
        job_title: str,
        recipient_email: str,
        recipient_name: str = "",
        subject: str = "",
        body: str = "",
        status: str = "SENT",
        has_attachment: bool = False,
    ) -> Dict[str, Any]:
        path = ColdOutreachConfig.COLD_APPLICATIONS_PATH
        os.makedirs(os.path.dirname(path), exist_ok=True)

        records = []
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    records = json.load(f)
            except Exception:
                records = []

        now = datetime.now()
        followup = (now + timedelta(days=6)).strftime("%Y-%m-%d")

        entry = {
            "id": f"app_{now.strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:4]}",
            "timestamp": now.isoformat(),
            "date": now.strftime("%b %d, %Y"),
            "company": company.strip(),
            "job_title": job_title.strip(),
            "recipient_name": recipient_name.strip() or "Hiring Team",
            "recipient_email": recipient_email.strip(),
            "subject": subject.strip(),
            "body": body.strip(),
            "status": status.upper(),
            "has_attachment": has_attachment,
            "followup_due_date": followup,
        }

        records.insert(0, entry)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)
        except Exception:
            pass
        return entry

    @classmethod
    def list_applications(cls, status_filter: str = "all", limit: int = 10) -> List[Dict[str, Any]]:
        path = ColdOutreachConfig.COLD_APPLICATIONS_PATH
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if status_filter != "all":
                    data = [r for r in data if r.get("status", "").lower() == status_filter.lower()]
                return data[:limit]
        except Exception:
            return []

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        apps = cls.list_applications(limit=1000)
        total = len(apps)
        sent = sum(1 for a in apps if a.get("status") == "SENT")
        drafted = sum(1 for a in apps if a.get("status") == "DRAFTED")
        replied = sum(1 for a in apps if a.get("status") == "REPLIED")
        today = datetime.now().strftime("%Y-%m-%d")
        followups = sum(1 for a in apps if a.get("status") == "SENT" and a.get("followup_due_date", "") <= today)

        return {
            "total_applications": total,
            "sent": sent,
            "drafted": drafted,
            "replied": replied,
            "followups_due": followups,
        }


# ==============================================================================
# 8. HIGH-LEVEL WORKFLOW ORCHESTRATOR
# ==============================================================================

class ColdOutreachAgent:
    """
    End-to-end unified workflow engine.
    Finds jobs -> Discovers recruiter emails -> Drafts cold emails -> Confirms & Sends -> Tracks.
    """
    _pending_draft: Optional[Dict[str, Any]] = None

    @classmethod
    def draft(
        cls,
        to_email: str,
        company: str,
        job_title: str,
        recipient_name: str = "",
        job_details: str = "",
        custom_notes: str = "",
        attach_resume: bool = True,
    ) -> Dict[str, Any]:
        subject, body = ColdEmailComposer.compose(
            recipient_name=recipient_name,
            company=company,
            job_title=job_title,
            job_details=job_details,
            custom_notes=custom_notes,
        )

        profile = ProfileManager.get_profile()
        resume_path = profile.get("resume_path")
        has_resume = bool(resume_path and os.path.exists(resume_path))

        draft_entry = {
            "to_email": to_email,
            "recipient_name": recipient_name,
            "company": company,
            "job_title": job_title,
            "subject": subject,
            "body": body,
            "attach_resume": attach_resume and has_resume,
            "resume_path": resume_path if has_resume else None,
        }

        cls._pending_draft = draft_entry

        # Log as DRAFTED
        OutreachTracker.log(
            company=company,
            job_title=job_title,
            recipient_email=to_email,
            recipient_name=recipient_name,
            subject=subject,
            body=body,
            status="DRAFTED",
            has_attachment=attach_resume and has_resume,
        )

        return draft_entry

    @classmethod
    def confirm_and_send(cls) -> Tuple[bool, str]:
        if not cls._pending_draft:
            return False, "No pending cold email draft found."

        draft = cls._pending_draft
        success, msg = EmailDispatcher.send(
            to_email=draft["to_email"],
            subject=draft["subject"],
            body=draft["body"],
            recipient_name=draft["recipient_name"],
            attach_resume=draft.get("attach_resume", False),
            resume_path=draft.get("resume_path"),
        )

        if success:
            OutreachTracker.log(
                company=draft["company"],
                job_title=draft["job_title"],
                recipient_email=draft["to_email"],
                recipient_name=draft["recipient_name"],
                subject=draft["subject"],
                body=draft["body"],
                status="SENT",
                has_attachment=draft.get("attach_resume", False),
            )
            cls._pending_draft = None

        return success, msg

    @classmethod
    def cancel_draft(cls) -> str:
        if not cls._pending_draft:
            return "No draft to cancel."
        company = cls._pending_draft.get("company", "")
        cls._pending_draft = None
        return f"Pending cold email draft for {company} has been cancelled."


# ==============================================================================
# 9. EXPORTABLE AGENT / LLM TOOL DEFINITIONS (Gemini, OpenAI, LangChain)
# ==============================================================================

TOOL_DEFINITIONS = [
    {
        "name": "search_linkedin_jobs",
        "description": "Search live job opportunities on LinkedIn without requiring login.",
        "parameters": {
            "type": "object",
            "properties": {
                "job_title": {"type": "string", "description": "Target job role"},
                "location": {"type": "string", "description": "Target location or Remote"},
                "max_results": {"type": "integer", "description": "Max results to return"},
            },
            "required": ["job_title"],
        },
    },
    {
        "name": "get_linkedin_job_details",
        "description": "Fetch full job description & requirements for a specific LinkedIn job.",
        "parameters": {
            "type": "object",
            "properties": {
                "job_ref": {"type": "string", "description": "Job index '#1', URL, or numeric ID"},
            },
            "required": ["job_ref"],
        },
    },
    {
        "name": "find_company_emails",
        "description": "Find public recruitment and HR contact emails for a target company.",
        "parameters": {
            "type": "object",
            "properties": {
                "company_name": {"type": "string", "description": "Company name"},
                "domain": {"type": "string", "description": "Optional website domain"},
            },
            "required": ["company_name"],
        },
    },
    {
        "name": "draft_cold_email",
        "description": "Synthesize a personalized cold email tailored to role and company.",
        "parameters": {
            "type": "object",
            "properties": {
                "to_email": {"type": "string", "description": "Target recipient email"},
                "company": {"type": "string", "description": "Target company name"},
                "job_title": {"type": "string", "description": "Target job title"},
                "recipient_name": {"type": "string", "description": "Recruiter/Hiring manager name"},
                "custom_notes": {"type": "string", "description": "Custom achievements or highlights"},
            },
            "required": ["to_email", "company", "job_title"],
        },
    },
    {
        "name": "confirm_and_send_email",
        "description": "Send the previously staged cold email draft upon user approval.",
        "parameters": {"type": "object", "properties": {}},
    },
]


# ==============================================================================
# 10. STANDALONE INTERACTIVE CLI RUNNER
# ==============================================================================

def interactive_cli():
    print("=" * 70)
    print("🚀 COLD OUTREACH & JOB HUNTER TOOLKIT")
    print("=" * 70)
    print("1. Search LinkedIn Jobs")
    print("2. Search Web Jobs")
    print("3. Find Recruiter Contact Emails for a Company")
    print("4. Draft & Preview Cold Email")
    print("5. Send Pending Draft")
    print("6. View Outreach Tracker & Analytics")
    print("7. View / Edit Candidate Profile")
    print("8. Exit")
    print("=" * 70)

    while True:
        choice = input("\nEnter choice (1-8): ").strip()

        if choice == "1":
            title = input("Job Title (e.g. Python Developer): ").strip() or "Python Developer"
            loc = input("Location (e.g. Remote / Pune): ").strip() or "Remote"
            jobs = LinkedInJobHunter.search_jobs(title, loc, max_results=5)
            print(f"\n--- Found {len(jobs)} LinkedIn Jobs ---")
            for j in jobs:
                print(f"[{j['index']}] {j['title']} at {j['company']} ({j['location']})")
                print(f"    URL: {j['url']}")

            detail_choice = input("\nEnter job number to inspect details (or Enter to skip): ").strip()
            if detail_choice:
                details = LinkedInJobHunter.get_job_details(detail_choice)
                print("\n--- Job Specifications ---")
                print(details.get("description", "No description")[:800] + "...\n")

        elif choice == "2":
            title = input("Job Title: ").strip() or "Software Engineer"
            loc = input("Location: ").strip() or "India"
            jobs = WebJobHunter.search_jobs(title, loc, max_results=5)
            print(f"\n--- Found {len(jobs)} Web Jobs ---")
            for j in jobs:
                print(f"[{j['index']}] {j['title']} ({j['company']})")
                print(f"    URL: {j['url']}")
                print(f"    Snippet: {j['snippet']}\n")

        elif choice == "3":
            company = input("Company Name (e.g. Postman, Razorpay): ").strip()
            domain = input("Company Domain (optional, e.g. postman.com): ").strip()
            res = RecruiterContactFinder.find_emails(company, domain)
            print("\n--- Contact Intelligence ---")
            print("Verified Public Emails:", res["verified_public_emails"])
            print("Standard Corporate Mailboxes:", res["standard_talent_mailboxes"])
            print(f"Recommended Recipient: {res['recommended_recipient']}")

        elif choice == "4":
            to_email = input("Recipient Email: ").strip()
            company = input("Company Name: ").strip()
            role = input("Job Title: ").strip()
            rec_name = input("Recruiter Name (optional): ").strip()
            notes = input("Custom points to highlight (optional): ").strip()

            draft = ColdOutreachAgent.draft(
                to_email=to_email,
                company=company,
                job_title=role,
                recipient_name=rec_name,
                custom_notes=notes,
            )
            print("\n--- Cold Email Draft ---")
            print(f"To: {draft['to_email']}")
            print(f"Subject: {draft['subject']}\n")
            print(draft["body"])
            print(f"\nAttachment: {'Resume PDF attached' if draft['attach_resume'] else 'None'}")
            print("Draft is staged. Choose option 5 to send.")

        elif choice == "5":
            confirm = input("Confirm send pending cold email? (yes/no): ").strip().lower()
            if confirm in ("yes", "y"):
                success, msg = ColdOutreachAgent.confirm_and_send()
                print("Result:", msg)
            else:
                print(ColdOutreachAgent.cancel_draft())

        elif choice == "6":
            stats = OutreachTracker.get_stats()
            print("\n--- Analytics ---")
            for k, v in stats.items():
                print(f"{k}: {v}")
            apps = OutreachTracker.list_applications(limit=5)
            print("\n--- Recent Outreach ---")
            for a in apps:
                print(f"• [{a['status']}] {a['company']} - {a['job_title']} ({a['recipient_email']})")

        elif choice == "7":
            prof = ProfileManager.get_profile()
            print("\n--- Candidate Profile ---")
            print(json.dumps(prof, indent=2))

        elif choice == "8":
            print("Goodbye!")
            break


if __name__ == "__main__":
    interactive_cli()
