# Jarvis AI — Cold Emailing & Dispatch Skill
# Dual-transport email delivery (SMTP + Gmail API) with AI-powered personalized draft synthesis,
# resume attachment support, and safety confirmation workflow.

import os
import smtplib
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Optional, Dict, Any, Tuple

from config import Config
from skills.profile_manager import get_user_profile
from skills.cold_outreach_tracker import log_cold_application

# Global in-memory storage for the pending cold email awaiting confirmation
_pending_cold_email: Optional[Dict[str, Any]] = None


def get_pending_cold_email() -> Optional[Dict[str, Any]]:
    """Get the currently drafted cold email awaiting user confirmation."""
    global _pending_cold_email
    return _pending_cold_email


def has_pending_cold_email() -> bool:
    """Check if there is a pending cold email waiting to be sent."""
    global _pending_cold_email
    return _pending_cold_email is not None


def _get_candidate_info() -> Dict[str, Any]:
    """Fetch candidate details from profile store."""
    return get_user_profile()


def _synthesize_cold_email_content(
    recipient_name: str,
    company: str,
    job_title: str,
    job_details: str = "",
    custom_notes: str = "",
    tone: str = "professional",
) -> Tuple[str, str]:
    """
    Synthesize an impactful, high-converting cold email body and subject line
    tailored to the target role, company, and candidate's profile.
    """
    profile = _get_candidate_info()
    candidate_name = profile.get("full_name", "Ashwin Gajbhiye")
    candidate_skills = profile.get("skills", ["Python", "FastAPI", "React", "AI/LLMs"])
    years_exp = profile.get("years_of_experience", "2 years")
    github = profile.get("github_url", "")
    linkedin = profile.get("linkedin_url", "")
    portfolio = profile.get("portfolio_url", "")

    salutation = f"Hi {recipient_name}," if recipient_name and recipient_name.lower() not in ("hiring team", "hr", "recruiter", "") else "Hi Hiring Team,"

    # Tailored Subject
    subject = f"Application: {job_title} — {candidate_name}"

    # Highlight top 3-4 skills relevant to the role
    skills_highlight = ", ".join(candidate_skills[:4])

    # Construct clean, punchy cold email body
    paragraphs = [
        salutation,
        f"\nI hope this email finds you well. I'm writing to express my enthusiastic interest in the **{job_title}** position at **{company}**.",
        f"With over {years_exp} of hands-on experience developing robust backend services, AI integrations, and full-stack software, I believe my background aligns strongly with your engineering goals.",
    ]

    if custom_notes:
        paragraphs.append(f"\n{custom_notes}")

    paragraphs.append("\nA few highlights of what I bring to the team:")
    paragraphs.append(f"• **Core Technical Stack**: Proficient in {skills_highlight} and scalable API architectures.")
    paragraphs.append(f"• **Hands-On Execution**: Designed and deployed production systems focusing on performance, reliability, and clean code.")
    if portfolio:
        paragraphs.append(f"• **Portfolio & Code**: Demonstrated projects available at {portfolio}.")
    elif github:
        paragraphs.append(f"• **Open Source & Code**: Project repositories and contributions on GitHub ({github}).")

    paragraphs.append(
        "\nI have attached my resume for your review. I would welcome the opportunity for a brief 15-minute conversation "
        "to discuss how my technical skill set can contribute to the team's roadmap."
    )

    paragraphs.append("\nThank you for your time and consideration.")
    paragraphs.append(f"\nWarm regards,\n**{candidate_name}**")
    
    contact_footer = []
    if profile.get("email"):
        contact_footer.append(f"Email: {profile.get('email')}")
    if linkedin:
        contact_footer.append(f"LinkedIn: {linkedin}")
    if github:
        contact_footer.append(f"GitHub: {github}")

    if contact_footer:
        paragraphs.append(" | ".join(contact_footer))

    body = "\n".join(paragraphs)
    return subject, body


def draft_cold_email(
    to_email: str,
    recipient_name: str = "",
    company: str = "",
    job_title: str = "",
    job_details: str = "",
    custom_notes: str = "",
    attach_resume: bool = True,
    tone: str = "professional",
) -> str:
    """
    Draft a personalized cold outreach email and stage it for user review.
    Does NOT send immediately — Jarvis presents the draft and awaits confirmation.

    Args:
        to_email: Recipient's email address (e.g., 'careers@company.com' or 'recruiter@company.com')
        recipient_name: Optional name of the recipient/hiring manager
        company: Company name
        job_title: Target role
        job_details: Optional requirements or job description notes
        custom_notes: Any specific achievements or custom points to include
        attach_resume: Whether to attach resume PDF (default: True)
        tone: Tone of the email ('professional', 'concise', 'enthusiastic')
    """
    global _pending_cold_email

    if not to_email or "@" not in to_email:
        return "Please provide a valid recipient email address, Sir."

    if not company:
        company = "your company"
    if not job_title:
        job_title = Config.LINKEDIN_JOB_TITLE or "Software Engineer"

    subject, body = _synthesize_cold_email_content(
        recipient_name=recipient_name,
        company=company,
        job_title=job_title,
        job_details=job_details,
        custom_notes=custom_notes,
        tone=tone,
    )

    profile = _get_candidate_info()
    resume_path = profile.get("resume_path") or Config.RESUME_PATH
    has_valid_resume = bool(resume_path and os.path.exists(resume_path))

    _pending_cold_email = {
        "to_email": to_email.strip(),
        "recipient_name": recipient_name.strip() or "Hiring Team",
        "company": company.strip(),
        "job_title": job_title.strip(),
        "subject": subject,
        "body": body,
        "attach_resume": attach_resume and has_valid_resume,
        "resume_path": resume_path if has_valid_resume else None,
        "dispatch_method": Config.EMAIL_DISPATCH_METHOD,
    }

    # Log as DRAFTED in tracker
    log_cold_application(
        company=company,
        job_title=job_title,
        recipient_email=to_email,
        recipient_name=recipient_name,
        subject=subject,
        body=body,
        status="DRAFTED",
        has_attachment=attach_resume and has_valid_resume,
        attachment_name=os.path.basename(resume_path) if (has_valid_resume and attach_resume) else "",
        dispatch_method=Config.EMAIL_DISPATCH_METHOD,
    )

    resume_note = (
        f"📎 **Attachment**: `{os.path.basename(resume_path)}` attached"
        if (attach_resume and has_valid_resume)
        else ("⚠️ Resume file not found or attachment disabled" if attach_resume else "No attachment requested")
    )

    lines = [
        "### ✉️ Cold Email Draft Prepared for Review",
        f"- **To**: {recipient_name or 'Hiring Team'} (`{to_email}`)",
        f"- **Company**: {company} | **Role**: {job_title}",
        f"- **Subject**: _{subject}_",
        f"- {resume_note}",
        "\n**Draft Email Preview:**",
        "```text",
        body,
        "```",
        "\n❓ **Sir, should I send this cold email now?**",
        "*(Say 'Yes, send it', 'Confirm send', or 'Cancel draft')*",
    ]

    return "\n".join(lines)


def preview_pending_cold_email() -> str:
    """View the currently staged cold email awaiting confirmation."""
    global _pending_cold_email
    if not _pending_cold_email:
        return "There is no cold email currently pending dispatch, Sir."

    p = _pending_cold_email
    return (
        f"### ✉️ Pending Cold Email\n"
        f"**To**: {p['to_email']}\n"
        f"**Subject**: {p['subject']}\n\n"
        f"{p['body']}\n\n"
        f"Say 'Yes, send it' to dispatch or 'Cancel' to discard."
    )


def confirm_send_cold_email(attach_resume: Optional[bool] = None) -> str:
    """
    Send the previously drafted cold email after user confirmation.
    Delivers via SMTP or Gmail API according to configuration.
    """
    global _pending_cold_email

    if not _pending_cold_email:
        return "No cold email is currently staged for sending. Please draft one first."

    draft = _pending_cold_email
    if attach_resume is not None:
        draft["attach_resume"] = attach_resume

    success, message = _dispatch_email(
        to_email=draft["to_email"],
        subject=draft["subject"],
        body=draft["body"],
        recipient_name=draft["recipient_name"],
        attach_resume=draft.get("attach_resume", False),
        resume_path=draft.get("resume_path"),
    )

    if success:
        # Update tracker status
        log_cold_application(
            company=draft["company"],
            job_title=draft["job_title"],
            recipient_email=draft["to_email"],
            recipient_name=draft["recipient_name"],
            subject=draft["subject"],
            body=draft["body"],
            status="SENT",
            has_attachment=draft.get("attach_resume", False),
            attachment_name=os.path.basename(draft.get("resume_path") or "") if draft.get("attach_resume") else "",
            dispatch_method=draft.get("dispatch_method", "smtp"),
        )
        _pending_cold_email = None
        return f"🚀 **Cold email successfully sent to {draft['to_email']}!**\n{message}"
    else:
        return f"❌ **Failed to dispatch cold email**: {message}\nDraft is still saved. You can verify your SMTP/.env credentials and retry."


def cancel_send_cold_email() -> str:
    """Cancel and clear the current staged cold email."""
    global _pending_cold_email
    if not _pending_cold_email:
        return "No pending cold email to cancel, Sir."

    comp = _pending_cold_email.get("company", "the company")
    _pending_cold_email = None
    return f"Cold email draft for {comp} has been cancelled and discarded, Sir."


def send_cold_email_direct(
    to_email: str,
    recipient_name: str = "",
    company: str = "",
    job_title: str = "",
    custom_notes: str = "",
    attach_resume: bool = True,
) -> str:
    """
    Synthesize and send a cold email immediately in a single step
    (use when user explicitly commands direct dispatch).
    """
    draft_msg = draft_cold_email(
        to_email=to_email,
        recipient_name=recipient_name,
        company=company,
        job_title=job_title,
        custom_notes=custom_notes,
        attach_resume=attach_resume,
    )
    send_res = confirm_send_cold_email()
    return f"{draft_msg}\n\n---\n{send_res}"


# ── Internal Delivery Transports (SMTP & Gmail API) ──────────

def _dispatch_email(
    to_email: str,
    subject: str,
    body: str,
    recipient_name: str = "",
    attach_resume: bool = False,
    resume_path: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Route email delivery through configured transport (SMTP or Gmail API).
    """
    method = Config.EMAIL_DISPATCH_METHOD.lower()

    if method == "gmail_api":
        return _dispatch_via_gmail_api(to_email, subject, body, attach_resume, resume_path)
    else:
        return _dispatch_via_smtp(to_email, subject, body, attach_resume, resume_path)


def _dispatch_via_smtp(
    to_email: str,
    subject: str,
    body: str,
    attach_resume: bool = False,
    resume_path: Optional[str] = None,
) -> Tuple[bool, str]:
    """Deliver email via SMTP."""
    smtp_user = Config.SMTP_USER
    smtp_password = Config.SMTP_PASSWORD
    smtp_host = Config.SMTP_HOST or "smtp.gmail.com"
    smtp_port = Config.SMTP_PORT or 587
    from_name = Config.SMTP_FROM_NAME or Config.USER_NAME or "Ashwin Gajbhiye"

    if not smtp_user or not smtp_password:
        return (
            False,
            "SMTP credentials are not configured in your .env file.\n"
            "Please set `SMTP_USER` and `SMTP_PASSWORD` (use a Google App Password for Gmail)."
        )

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{smtp_user}>"
    msg["To"] = to_email

    # Plaintext and HTML body
    msg_alt = MIMEMultipart("alternative")
    msg_alt.attach(MIMEText(body, "plain", "utf-8"))

    # Convert simple markdown to basic HTML formatting
    html_body = body.replace("\n", "<br>").replace("**", "<b>").replace("•", "&bull;")
    msg_alt.attach(MIMEText(f"<html><body>{html_body}</body></html>", "html", "utf-8"))
    msg.attach(msg_alt)

    # Attach resume if requested and available
    if attach_resume and resume_path and os.path.exists(resume_path):
        try:
            with open(resume_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(resume_path))
            part["Content-Disposition"] = f'attachment; filename="{os.path.basename(resume_path)}"'
            msg.attach(part)
        except Exception as e:
            print(f"Warning: Could not attach resume: {e}")

    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
            server.ehlo()
            server.starttls()
            server.ehlo()

        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, [to_email], msg.as_string())
        server.quit()
        return True, f"Delivered via SMTP ({smtp_host}) from {smtp_user}."

    except smtplib.SMTPAuthenticationError:
        return False, "SMTP Authentication failed. For Gmail, verify you generated a 16-digit App Password."
    except Exception as e:
        return False, f"SMTP error: {str(e)}"


def _dispatch_via_gmail_api(
    to_email: str,
    subject: str,
    body: str,
    attach_resume: bool = False,
    resume_path: Optional[str] = None,
) -> Tuple[bool, str]:
    """Deliver email via Gmail API."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        return False, "Google API client packages not installed."

    SCOPES = [
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.readonly",
    ]

    token_path = Config.GMAIL_TOKEN_PATH
    creds_path = Config.GMAIL_CREDENTIALS_PATH

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
                return False, f"Gmail {creds_path} not found. Please provide credentials.json or switch to SMTP."
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as token:
            token.write(creds.to_json())

    try:
        service = build("gmail", "v1", credentials=creds)

        message = MIMEMultipart()
        message["to"] = to_email
        message["subject"] = subject
        message.attach(MIMEText(body, "plain"))

        if attach_resume and resume_path and os.path.exists(resume_path):
            with open(resume_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(resume_path))
            part["Content-Disposition"] = f'attachment; filename="{os.path.basename(resume_path)}"'
            message.attach(part)

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return True, "Delivered via authorized Gmail API."

    except Exception as e:
        return False, f"Gmail API error: {str(e)}"


# ── Tool Definitions for Gemini Function Calling ─────────────
COLD_EMAIL_TOOLS = [
    {
        "name": "draft_cold_email",
        "description": (
            "Synthesize and draft a personalized cold email for a job opportunity without sending immediately. "
            "Presents the draft with recipient, company, subject, and body for user review. "
            "ALWAYS call this first when the user asks to write, draft, or prepare a cold email for a job."
        ),
        "function": draft_cold_email,
        "parameters": {
            "type": "object",
            "properties": {
                "to_email": {"type": "string", "description": "Recipient email address (e.g. 'careers@company.com')"},
                "recipient_name": {"type": "string", "description": "Hiring manager or recruiter's name"},
                "company": {"type": "string", "description": "Target company name"},
                "job_title": {"type": "string", "description": "Target job title"},
                "job_details": {"type": "string", "description": "Optional notes from job requirements or description"},
                "custom_notes": {"type": "string", "description": "Any specific personal achievements or points to add"},
                "attach_resume": {"type": "boolean", "description": "Whether to attach resume PDF (default: true)"},
                "tone": {
                    "type": "string",
                    "enum": ["professional", "concise", "enthusiastic"],
                    "description": "Tone of the outreach email",
                },
            },
            "required": ["to_email", "company", "job_title"],
        },
    },
    {
        "name": "confirm_send_cold_email",
        "description": (
            "Dispatch the currently drafted cold email to the recipient. "
            "Use ONLY after the draft has been shown to the user and the user says 'yes', 'send it', 'proceed', or confirms."
        ),
        "function": confirm_send_cold_email,
        "parameters": {
            "type": "object",
            "properties": {
                "attach_resume": {
                    "type": "boolean",
                    "description": "Optional override to attach or exclude resume PDF",
                },
            },
        },
    },
    {
        "name": "cancel_send_cold_email",
        "description": "Discard and cancel the pending cold email draft if the user decides not to send it.",
        "function": cancel_send_cold_email,
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "preview_pending_cold_email",
        "description": "Review the details of the currently staged cold email draft awaiting confirmation.",
        "function": preview_pending_cold_email,
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "send_cold_email_direct",
        "description": (
            "Synthesize and send a cold email immediately in one turn. "
            "Only use when the user explicitly commands to send directly without staging a preview."
        ),
        "function": send_cold_email_direct,
        "parameters": {
            "type": "object",
            "properties": {
                "to_email": {"type": "string", "description": "Recipient email address"},
                "recipient_name": {"type": "string", "description": "Recruiter or hiring manager name"},
                "company": {"type": "string", "description": "Company name"},
                "job_title": {"type": "string", "description": "Job title"},
                "custom_notes": {"type": "string", "description": "Custom accomplishments or highlights"},
                "attach_resume": {"type": "boolean", "description": "Attach resume PDF (default: true)"},
            },
            "required": ["to_email", "company", "job_title"],
        },
    },
]
