# Jarvis AI — Cold Outreach Application Tracker
# Persists and tracks cold emails sent to recruiters, HRs, and hiring managers.
# Records status, follow-up dates, and application metrics.

import os
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from config import Config


def _ensure_dir():
    os.makedirs(os.path.dirname(Config.COLD_APPLICATIONS_PATH), exist_ok=True)


def _load_tracker() -> List[Dict[str, Any]]:
    _ensure_dir()
    if not os.path.exists(Config.COLD_APPLICATIONS_PATH):
        return []
    try:
        with open(Config.COLD_APPLICATIONS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_tracker(records: List[Dict[str, Any]]) -> bool:
    _ensure_dir()
    try:
        with open(Config.COLD_APPLICATIONS_PATH, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
        return True
    except Exception:
        return False


def log_cold_application(
    company: str,
    job_title: str,
    recipient_email: str,
    recipient_name: str = "",
    subject: str = "",
    body: str = "",
    job_url: str = "",
    status: str = "SENT",
    has_attachment: bool = False,
    attachment_name: str = "",
    dispatch_method: str = "smtp",
    notes: str = "",
) -> Dict[str, Any]:
    """
    Log a drafted or sent cold outreach email.
    """
    records = _load_tracker()
    now = datetime.now()
    followup_date = (now + timedelta(days=6)).strftime("%Y-%m-%d")

    entry = {
        "id": f"app_{now.strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:4]}",
        "timestamp": now.isoformat(),
        "date_formatted": now.strftime("%b %d, %Y %I:%M %p"),
        "company": company.strip(),
        "job_title": job_title.strip(),
        "recipient_name": recipient_name.strip() or "Hiring Team",
        "recipient_email": recipient_email.strip(),
        "subject": subject.strip(),
        "body_preview": (body.strip()[:200] + "...") if len(body.strip()) > 200 else body.strip(),
        "full_body": body.strip(),
        "job_url": job_url.strip(),
        "status": status.upper(),  # DRAFTED, SENT, REPLIED, FOLLOWED_UP
        "has_attachment": has_attachment,
        "attachment_name": attachment_name,
        "dispatch_method": dispatch_method,
        "followup_due_date": followup_date,
        "notes": notes.strip(),
    }

    records.insert(0, entry)  # Newest first
    _save_tracker(records)
    return entry


def list_cold_applications(status_filter: str = "all", limit: int = 10) -> str:
    """
    List logged cold email applications with their current status.

    Args:
        status_filter: 'all', 'sent', 'drafted', 'replied', or 'followed_up'
        limit: Number of records to show
    """
    records = _load_tracker()
    if not records:
        return "No cold email applications logged yet, Sir."

    if status_filter.lower() != "all":
        records = [r for r in records if r.get("status", "").upper() == status_filter.upper()]

    if not records:
        return f"No applications found with status '{status_filter}'."

    records = records[:limit]
    lines = [f"### 📬 Cold Outreach Log ({len(records)} recent):\n"]

    for i, r in enumerate(records, 1):
        status_icon = "🟢" if r.get("status") == "SENT" else ("🟡" if r.get("status") == "DRAFTED" else "🔵")
        lines.append(
            f"**{i}. {status_icon} {r.get('company')} — {r.get('job_title')}**\n"
            f"   - **Recipient**: {r.get('recipient_name')} (`{r.get('recipient_email')}`)\n"
            f"   - **Date**: {r.get('date_formatted', r.get('timestamp', 'N/A'))}\n"
            f"   - **Status**: `{r.get('status')}` | **Follow-up Due**: `{r.get('followup_due_date', 'N/A')}`\n"
            f"   - **Subject**: _{r.get('subject')}_\n"
            f"   - **ID**: `{r.get('id')}`\n"
        )

    return "\n".join(lines)


def get_outreach_analytics() -> str:
    """
    Get summary statistics of cold outreach campaigns.
    """
    records = _load_tracker()
    if not records:
        return "No cold outreach activity recorded yet, Sir."

    total = len(records)
    sent = sum(1 for r in records if r.get("status") == "SENT")
    drafted = sum(1 for r in records if r.get("status") == "DRAFTED")
    replied = sum(1 for r in records if r.get("status") == "REPLIED")
    followup_needed = 0

    today = datetime.now().strftime("%Y-%m-%d")
    for r in records:
        if r.get("status") == "SENT" and r.get("followup_due_date") and r.get("followup_due_date") <= today:
            followup_needed += 1

    lines = [
        "### 📊 Cold Outreach Performance & Analytics",
        f"- **Total Applications**: {total}",
        f"- **Emails Sent**: {sent}",
        f"- **Pending Drafts**: {drafted}",
        f"- **Responses Received**: {replied}",
        f"- **Follow-ups Due Today or Overdue**: {followup_needed}",
    ]

    return "\n".join(lines)


def update_application_status(app_id: str, new_status: str, notes: str = "") -> str:
    """
    Update the status of an application (e.g. SENT, REPLIED, FOLLOWED_UP, REJECTED).
    """
    records = _load_tracker()
    for r in records:
        if r.get("id") == app_id:
            r["status"] = new_status.upper()
            if notes:
                r["notes"] = notes
            _save_tracker(records)
            return f"✅ Application `{app_id}` updated to `{new_status.upper()}`."

    return f"❌ Application with ID `{app_id}` not found."


# ── Tool Definitions for Gemini ──────────────────────────────
OUTREACH_TRACKER_TOOLS = [
    {
        "name": "list_cold_applications",
        "description": "List recently sent or drafted cold outreach job applications and their statuses.",
        "function": list_cold_applications,
        "parameters": {
            "type": "object",
            "properties": {
                "status_filter": {
                    "type": "string",
                    "enum": ["all", "sent", "drafted", "replied", "followed_up"],
                    "description": "Filter by status (default: 'all')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of entries to display (default: 10)",
                },
            },
        },
    },
    {
        "name": "get_outreach_analytics",
        "description": "Get overall statistics and metrics on cold outreach email campaigns.",
        "function": get_outreach_analytics,
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "update_application_status",
        "description": "Update the tracking status of a specific cold application by ID (e.g. SENT, REPLIED, FOLLOWED_UP).",
        "function": update_application_status,
        "parameters": {
            "type": "object",
            "properties": {
                "app_id": {"type": "string", "description": "The unique application ID (e.g. app_20260911_...)"},
                "new_status": {
                    "type": "string",
                    "enum": ["SENT", "REPLIED", "FOLLOWED_UP", "REJECTED"],
                    "description": "New status for the application",
                },
                "notes": {"type": "string", "description": "Optional notes or response details"},
            },
            "required": ["app_id", "new_status"],
        },
    },
]
