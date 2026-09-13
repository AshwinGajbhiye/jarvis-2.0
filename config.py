# Jarvis AI Configuration
# Load from .env file, with sensible defaults

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Central configuration for Jarvis AI."""

    # ── AI Brain ──────────────────────────────────────────────
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_API_KEY_FALLBACK: str = os.getenv("GEMINI_API_KEY_FALLBACK", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openrouter/free")
    USE_ANTIGRAVITY: bool = os.getenv("USE_ANTIGRAVITY", "true").lower() in ("true", "1", "yes")
    ANTIGRAVITY_MODEL: str = os.getenv("ANTIGRAVITY_MODEL", "gemini-3.5-flash-lite")
    BROWSER_CDP_PORT: int = int(os.getenv("BROWSER_CDP_PORT", "9222"))
    AUTO_SKIP_YOUTUBE_ADS: bool = os.getenv("AUTO_SKIP_YOUTUBE_ADS", "true").lower() in ("true", "1", "yes")

    # ── Mobile API Server ─────────────────────────────────────
    MOBILE_API_KEY: str = os.getenv("MOBILE_API_KEY", "").strip() or "jarvis-mobile-secret-key-2026"

    # ── Voice ─────────────────────────────────────────────────
    JARVIS_VOICE: str = os.getenv("JARVIS_VOICE", "Daniel")
    JARVIS_SPEECH_RATE: int = int(os.getenv("JARVIS_SPEECH_RATE", "180"))
    STT_LANGUAGE: str = os.getenv("STT_LANGUAGE", "en-US")
    STT_TIMEOUT: int = int(os.getenv("STT_TIMEOUT", "5"))
    STT_PHRASE_LIMIT: int = int(os.getenv("STT_PHRASE_LIMIT", "15"))

    # ── Assistant Identity ────────────────────────────────────
    JARVIS_NAME: str = os.getenv("JARVIS_NAME", "Jarvis")
    USER_NAME: str = os.getenv("USER_NAME", "Sir")

    # ── Gmail & Email Sending ──────────────────────────────────
    GMAIL_CREDENTIALS_PATH: str = os.getenv(
        "GMAIL_CREDENTIALS_PATH", "credentials.json"
    )
    GMAIL_TOKEN_PATH: str = os.getenv("GMAIL_TOKEN_PATH", "token.json")
    GMAIL_PERSONAL_TOKEN_PATH: str = os.getenv("GMAIL_PERSONAL_TOKEN_PATH", "token_personal.json")
    GMAIL_COLLEGE_TOKEN_PATH: str = os.getenv("GMAIL_COLLEGE_TOKEN_PATH", "token_college.json")
    GMAIL_MAX_EMAILS: int = int(os.getenv("GMAIL_MAX_EMAILS", "10"))

    # SMTP Configuration (zero-OAuth quick setup for cold emailing)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "")
    EMAIL_DISPATCH_METHOD: str = os.getenv("EMAIL_DISPATCH_METHOD", "smtp")

    # ── Profile & Outreach Paths ──────────────────────────────
    RESUME_PATH: str = os.path.expanduser(os.getenv("RESUME_PATH", "~/.jarvis/resume.pdf"))
    USER_PROFILE_PATH: str = os.path.expanduser(os.getenv("USER_PROFILE_PATH", "~/.jarvis/user_profile.json"))
    COLD_APPLICATIONS_PATH: str = os.path.expanduser(os.getenv("COLD_APPLICATIONS_PATH", "~/.jarvis/cold_applications.json"))

    # ── Browser ───────────────────────────────────────────────
    # Custom Preferences
    DEFAULT_BROWSER = os.getenv("DEFAULT_BROWSER", "brave")
    LEETCODE_USERNAME = os.getenv("LEETCODE_USERNAME", "")

    # ── LinkedIn Job Preferences ──────────────────────────────
    LINKEDIN_JOB_TITLE: str = os.getenv(
        "LINKEDIN_JOB_TITLE", "Software Developer"
    )
    LINKEDIN_JOB_LOCATION: str = os.getenv("LINKEDIN_JOB_LOCATION", "India")

    # ── Memory ────────────────────────────────────────────────
    MAX_CONVERSATION_HISTORY: int = int(
        os.getenv("MAX_CONVERSATION_HISTORY", "50")
    )
    HISTORY_DIR: str = os.path.expanduser("~/.jarvis/history")

    # ── System Paths ──────────────────────────────────────────
    PROJECT_ROOT: str = os.path.dirname(os.path.abspath(__file__))

    @classmethod
    def validate(cls) -> list[str]:
        """Check for missing required configuration. Returns list of warnings."""
        warnings = []
        if not cls.GEMINI_API_KEY:
            warnings.append(
                "⚠️  GEMINI_API_KEY not set. AI features won't work. "
                "Get one free at https://aistudio.google.com/apikey"
            )
        if not os.path.exists(cls.GMAIL_CREDENTIALS_PATH):
            warnings.append(
                "⚠️  Gmail credentials.json not found. Email features won't work. "
                "See SETUP.md for instructions."
            )
        return warnings

    @classmethod
    def print_status(cls):
        """Print configuration status."""
        print(f"  🤖 Model:    {cls.GEMINI_MODEL} (OR: {cls.OPENROUTER_MODEL})")
        print(f"  🗣️  Voice:    {cls.JARVIS_VOICE}")
        print(f"  🌐 Browser:  {cls.DEFAULT_BROWSER}")
        print(f"  📧 Gmail:    {'✅ Ready' if os.path.exists(cls.GMAIL_CREDENTIALS_PATH) else '❌ Not configured'}")
        print(f"  🧠 AI Key:   {'✅ Set' if cls.GEMINI_API_KEY or cls.OPENROUTER_API_KEY else '❌ Not set'}")
