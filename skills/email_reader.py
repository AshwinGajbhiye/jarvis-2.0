# Jarvis AI — Gmail Email Reader Skill
# Reads emails from Gmail using the Gmail API with OAuth2.
# First-time setup requires browser authentication.

import os
import base64
import email
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

from config import Config


def _get_gmail_service(account_type: str = "default"):
    """
    Initialize and return the Gmail API service.
    Handles OAuth2 authentication and token refresh.
    account_type can be 'default', 'personal', or 'college'.
    """
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        return None

    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
    creds = None

    # Determine token path based on account_type
    if account_type == "personal":
        token_path = Config.GMAIL_PERSONAL_TOKEN_PATH
    elif account_type == "college":
        token_path = Config.GMAIL_COLLEGE_TOKEN_PATH
    else:
        token_path = Config.GMAIL_TOKEN_PATH
        
    creds_path = Config.GMAIL_CREDENTIALS_PATH

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # Refresh or re-authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds:
            if not os.path.exists(creds_path):
                return None
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the token for future use
        with open(token_path, "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def _parse_email_message(msg_data: dict) -> dict:
    """Parse a Gmail API message into a readable format."""
    headers = msg_data.get("payload", {}).get("headers", [])

    result = {
        "id": msg_data.get("id", ""),
        "subject": "",
        "from": "",
        "date": "",
        "snippet": msg_data.get("snippet", ""),
        "is_unread": "UNREAD" in msg_data.get("labelIds", []),
        "body": "",
    }

    for header in headers:
        name = header.get("name", "").lower()
        value = header.get("value", "")
        if name == "subject":
            result["subject"] = value
        elif name == "from":
            result["from"] = value
        elif name == "date":
            result["date"] = value

    # Try to extract body text
    payload = msg_data.get("payload", {})
    body = _extract_body(payload)
    if body:
        result["body"] = body[:500]  # Limit body length

    return result


def _extract_body(payload: dict) -> str:
    """Extract plain text body from email payload."""
    mime_type = payload.get("mimeType", "")

    if mime_type == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    # Check parts for multipart messages
    parts = payload.get("parts", [])
    for part in parts:
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        # Recurse into nested parts
        if part.get("parts"):
            result = _extract_body(part)
            if result:
                return result

    return ""


def read_emails(
    max_results: int = 5,
    unread_only: bool = True,
    hours_ago: int = 24,
    account_type: str = "default",
) -> str:
    """
    Read recent emails from Gmail.

    Args:
        max_results: Maximum number of emails to return
        unread_only: If True, only show unread emails
        hours_ago: How far back to look (in hours)
        account_type: Which account to check ('personal', 'college', or 'default')

    Returns:
        A formatted summary of emails
    """
    service = _get_gmail_service(account_type)
    if service is None:
        return (
            "Gmail is not configured yet. Please set up your credentials.json file. "
            "See SETUP.md for instructions."
        )

    try:
        # Build query
        query_parts = []
        if unread_only:
            query_parts.append("is:unread")

        # Time filter
        after_date = (datetime.now() - timedelta(hours=hours_ago)).strftime("%Y/%m/%d")
        query_parts.append(f"after:{after_date}")

        query = " ".join(query_parts) if query_parts else None

        # Fetch messages
        results = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )

        messages = results.get("messages", [])

        if not messages:
            if unread_only:
                return "You have no unread emails. Your inbox is clean!"
            return f"No emails found in the last {hours_ago} hours."

        # Fetch details for each message
        email_summaries = []
        for msg in messages:
            msg_data = (
                service.users()
                .messages()
                .get(userId="me", id=msg["id"], format="full")
                .execute()
            )
            parsed = _parse_email_message(msg_data)
            email_summaries.append(parsed)

        # Format output
        output_parts = [f"📧 You have {len(email_summaries)} {'unread ' if unread_only else ''}email{'s' if len(email_summaries) != 1 else ''}:\n"]

        for i, em in enumerate(email_summaries, 1):
            sender = em["from"].split("<")[0].strip().strip('"')
            output_parts.append(
                f"{i}. From: {sender}\n"
                f"   Subject: {em['subject']}\n"
                f"   Preview: {em['snippet'][:100]}...\n"
            )

        return "\n".join(output_parts)

    except Exception as e:
        return f"Error reading emails: {e}"


def read_emails_from_sender(sender: str, max_results: int = 5, account_type: str = "default") -> str:
    """
    Read emails from a specific sender.

    Args:
        sender: Sender name or email to filter by
        max_results: Maximum number of emails to return
        account_type: Which account to check
    """
    service = _get_gmail_service(account_type)
    if service is None:
        return "Gmail is not configured. See SETUP.md for instructions."

    try:
        query = f"from:{sender}"
        results = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )

        messages = results.get("messages", [])
        if not messages:
            return f"No emails found from '{sender}'."

        email_summaries = []
        for msg in messages:
            msg_data = (
                service.users()
                .messages()
                .get(userId="me", id=msg["id"], format="full")
                .execute()
            )
            parsed = _parse_email_message(msg_data)
            email_summaries.append(parsed)

        output_parts = [f"📧 Found {len(email_summaries)} email{'s' if len(email_summaries) != 1 else ''} from {sender}:\n"]

        for i, em in enumerate(email_summaries, 1):
            output_parts.append(
                f"{i}. Subject: {em['subject']}\n"
                f"   Date: {em['date']}\n"
                f"   Preview: {em['snippet'][:120]}...\n"
            )

        return "\n".join(output_parts)

    except Exception as e:
        return f"Error reading emails: {e}"


def search_emails(search_query: str, max_results: int = 5, account_type: str = "default") -> str:
    """
    Search emails by keyword.

    Args:
        search_query: Keywords to search in emails
        max_results: Maximum number of results
        account_type: Which account to check
    """
    service = _get_gmail_service(account_type)
    if service is None:
        return "Gmail is not configured. See SETUP.md for instructions."

    try:
        results = (
            service.users()
            .messages()
            .list(userId="me", q=search_query, maxResults=max_results)
            .execute()
        )

        messages = results.get("messages", [])
        if not messages:
            return f"No emails found matching '{search_query}'."

        email_summaries = []
        for msg in messages:
            msg_data = (
                service.users()
                .messages()
                .get(userId="me", id=msg["id"], format="full")
                .execute()
            )
            parsed = _parse_email_message(msg_data)
            email_summaries.append(parsed)

        output_parts = [f"📧 Found {len(email_summaries)} email{'s' if len(email_summaries) != 1 else ''} matching '{search_query}':\n"]

        for i, em in enumerate(email_summaries, 1):
            sender = em["from"].split("<")[0].strip().strip('"')
            output_parts.append(
                f"{i}. From: {sender}\n"
                f"   Subject: {em['subject']}\n"
                f"   Preview: {em['snippet'][:100]}...\n"
            )

        return "\n".join(output_parts)

    except Exception as e:
        return f"Error searching emails: {e}"


def get_email_count(account_type: str = "default") -> str:
    """Get the count of unread emails."""
    service = _get_gmail_service(account_type)
    if service is None:
        return "Gmail is not configured. See SETUP.md for instructions."

    try:
        results = (
            service.users()
            .messages()
            .list(userId="me", q="is:unread", maxResults=100)
            .execute()
        )

        count = results.get("resultSizeEstimate", 0)
        if count == 0:
            return "You have no unread emails. Inbox zero!"
        return f"You have approximately {count} unread email{'s' if count != 1 else ''}."

    except Exception as e:
        return f"Error checking emails: {e}"


# ── Tool definitions for Gemini function calling ─────────────
EMAIL_TOOLS = [
    {
        "name": "read_emails",
        "description": (
            "Read recent emails from Gmail inbox. Can filter by unread status "
            "and time range. Use when the user asks to check, read, or summarize their emails."
        ),
        "function": read_emails,
        "parameters": {
            "type": "object",
            "properties": {
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of emails to return (default: 5)",
                },
                "unread_only": {
                    "type": "boolean",
                    "description": "If true, only show unread emails (default: true)",
                },
                "hours_ago": {
                    "type": "integer",
                    "description": "How many hours back to search (default: 24)",
                },
                "account_type": {
                    "type": "string",
                    "enum": ["personal", "college", "default"],
                    "description": "Which email account to check",
                },
            },
        },
    },
    {
        "name": "read_emails_from_sender",
        "description": (
            "Read emails from a specific person or sender. "
            "Use when the user asks about emails from a particular person."
        ),
        "function": read_emails_from_sender,
        "parameters": {
            "type": "object",
            "properties": {
                "sender": {
                    "type": "string",
                    "description": "Sender name or email address to filter by",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of emails to return (default: 5)",
                },
                "account_type": {
                    "type": "string",
                    "enum": ["personal", "college", "default"],
                    "description": "Which email account to check",
                },
            },
            "required": ["sender"],
        },
    },
    {
        "name": "search_emails",
        "description": (
            "Search emails by keyword or topic. "
            "Use when the user wants to find specific emails by content."
        ),
        "function": search_emails,
        "parameters": {
            "type": "object",
            "properties": {
                "search_query": {
                    "type": "string",
                    "description": "Keywords to search for in emails",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 5)",
                },
                "account_type": {
                    "type": "string",
                    "enum": ["personal", "college", "default"],
                    "description": "Which email account to check",
                },
            },
            "required": ["search_query"],
        },
    },
    {
        "name": "get_email_count",
        "description": "Get the number of unread emails in the inbox.",
        "function": get_email_count,
        "parameters": {
            "type": "object",
            "properties": {
                "account_type": {
                    "type": "string",
                    "enum": ["personal", "college", "default"],
                    "description": "Which email account to check",
                },
            }
        },
    },
]
