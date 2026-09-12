# Jarvis AI — Candidate Profile Manager Skill
# Manages the candidate's professional profile, skills, links, and resume path
# for personalized job search matching and cold email generation.

import os
import json
from typing import Dict, Any, Optional

from config import Config

DEFAULT_PROFILE = {
    "full_name": Config.SMTP_FROM_NAME or Config.USER_NAME or "Ashwin Gajbhiye",
    "email": Config.SMTP_USER or "",
    "phone": "",
    "location": Config.LINKEDIN_JOB_LOCATION or "India",
    "target_roles": [Config.LINKEDIN_JOB_TITLE or "Software Developer", "Full Stack Developer", "AI Engineer"],
    "current_title": "Software Developer / Engineer",
    "years_of_experience": "1-2 years",
    "skills": [
        "Python",
        "FastAPI",
        "React",
        "JavaScript / TypeScript",
        "Generative AI & LLMs",
        "Playwright Automation",
        "REST APIs",
        "Docker",
    ],
    "projects": [
        "Jarvis 2.0 AI Assistant with voice, browser automation, and multi-agent workflows",
        "Full-stack applications with React, FastAPI, and real-time APIs",
    ],
    "linkedin_url": "https://linkedin.com",
    "github_url": "https://github.com",
    "portfolio_url": "",
    "resume_path": Config.RESUME_PATH,
    "custom_bio": "Passionate software engineer building modern AI-driven and full-stack software solutions.",
}


def _ensure_dir():
    os.makedirs(os.path.dirname(Config.USER_PROFILE_PATH), exist_ok=True)


def get_user_profile() -> Dict[str, Any]:
    """
    Retrieve candidate profile information from disk.
    If no profile file exists, creates one with default values.
    """
    _ensure_dir()
    if not os.path.exists(Config.USER_PROFILE_PATH):
        try:
            with open(Config.USER_PROFILE_PATH, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_PROFILE, f, indent=2)
            return DEFAULT_PROFILE
        except Exception:
            return DEFAULT_PROFILE

    try:
        with open(Config.USER_PROFILE_PATH, "r", encoding="utf-8") as f:
            profile = json.load(f)
            # Merge with defaults for missing keys
            for k, v in DEFAULT_PROFILE.items():
                if k not in profile:
                    profile[k] = v
            return profile
    except Exception:
        return DEFAULT_PROFILE


def update_user_profile(
    full_name: Optional[str] = None,
    email: Optional[str] = None,
    target_roles: Optional[str] = None,
    skills: Optional[str] = None,
    years_of_experience: Optional[str] = None,
    linkedin_url: Optional[str] = None,
    github_url: Optional[str] = None,
    portfolio_url: Optional[str] = None,
    resume_path: Optional[str] = None,
    custom_bio: Optional[str] = None,
) -> str:
    """
    Update details in the candidate profile used for job applications.
    Comma-separated strings can be passed for target_roles and skills.
    """
    profile = get_user_profile()

    if full_name:
        profile["full_name"] = full_name.strip()
    if email:
        profile["email"] = email.strip()
    if target_roles:
        profile["target_roles"] = [r.strip() for r in target_roles.split(",") if r.strip()]
    if skills:
        profile["skills"] = [s.strip() for s in skills.split(",") if s.strip()]
    if years_of_experience:
        profile["years_of_experience"] = years_of_experience.strip()
    if linkedin_url:
        profile["linkedin_url"] = linkedin_url.strip()
    if github_url:
        profile["github_url"] = github_url.strip()
    if portfolio_url:
        profile["portfolio_url"] = portfolio_url.strip()
    if resume_path:
        profile["resume_path"] = os.path.expanduser(resume_path.strip())
    if custom_bio:
        profile["custom_bio"] = custom_bio.strip()

    _ensure_dir()
    try:
        with open(Config.USER_PROFILE_PATH, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2)
        return "✅ Candidate profile updated successfully."
    except Exception as e:
        return f"❌ Failed to save profile: {e}"


def view_candidate_profile() -> str:
    """
    View the stored candidate profile details formatted in Markdown.
    """
    profile = get_user_profile()
    resume_status = "✅ Found" if (profile.get("resume_path") and os.path.exists(profile["resume_path"])) else "⚠️ File not found"

    lines = [
        f"### 👤 Candidate Profile: **{profile.get('full_name')}**",
        f"- **Email**: {profile.get('email') or 'Not set'}",
        f"- **Target Roles**: {', '.join(profile.get('target_roles', []))}",
        f"- **Experience**: {profile.get('years_of_experience', 'Not specified')}",
        f"- **Top Skills**: {', '.join(profile.get('skills', []))}",
        f"- **Resume Path**: `{profile.get('resume_path')}` ({resume_status})",
        f"- **LinkedIn**: {profile.get('linkedin_url') or 'Not set'}",
        f"- **GitHub**: {profile.get('github_url') or 'Not set'}",
        f"- **Portfolio**: {profile.get('portfolio_url') or 'Not set'}",
    ]
    if profile.get("custom_bio"):
        lines.append(f"- **Bio**: _{profile.get('custom_bio')}_")

    return "\n".join(lines)


# ── Tool Definitions for Gemini Function Calling ─────────────
PROFILE_TOOLS = [
    {
        "name": "view_candidate_profile",
        "description": "View the candidate's professional profile, skills, target roles, and resume status used for cold emails.",
        "function": view_candidate_profile,
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "update_user_profile",
        "description": "Update candidate profile fields such as name, email, target roles, skills, resume path, and portfolio links.",
        "function": update_user_profile,
        "parameters": {
            "type": "object",
            "properties": {
                "full_name": {"type": "string", "description": "Candidate's full name"},
                "email": {"type": "string", "description": "Candidate's contact email"},
                "target_roles": {"type": "string", "description": "Comma-separated target roles (e.g. 'Python Developer, AI Engineer')"},
                "skills": {"type": "string", "description": "Comma-separated core skills (e.g. 'Python, React, FastAPI')"},
                "years_of_experience": {"type": "string", "description": "Experience level or years (e.g. '2 years')"},
                "linkedin_url": {"type": "string", "description": "Candidate's LinkedIn URL"},
                "github_url": {"type": "string", "description": "Candidate's GitHub URL"},
                "portfolio_url": {"type": "string", "description": "Portfolio website URL"},
                "resume_path": {"type": "string", "description": "Path to resume PDF file"},
                "custom_bio": {"type": "string", "description": "Brief summary or elevator pitch"},
            },
        },
    },
]
