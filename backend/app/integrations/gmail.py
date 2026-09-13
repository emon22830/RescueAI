"""Gmail. Reads project evidence; write actions live in execute_action()."""

import base64
import logging
from datetime import UTC, datetime
from email.message import EmailMessage

import httpx

from app.agents.state import Evidence, PlannedAction
from app.integrations import google_auth

logger = logging.getLogger(__name__)

API = "https://gmail.googleapis.com/gmail/v1/users/me"
TIMEOUT = 20.0
LOOKBACK_DAYS = 60
MAX_EMAILS = 25
MAX_BODY_CHARS = 4000


def collect_evidence(project_name: str) -> list[Evidence]:
    """Recent mail that mentions the project — the stakeholder side of the story."""
    if not google_auth.is_connected():
        logger.warning("Gmail skipped: GOOGLE_* variables are empty in backend/.env")
        return []

    query = f"{project_name} newer_than:{LOOKBACK_DAYS}d -in:spam -in:trash"
    return [_to_evidence(fetch_message(message_id)) for message_id in search_messages(query)]


def search_messages(query: str) -> list[str]:
    """Message ids matching a Gmail search query, newest first."""
    body = _get("/messages", {"q": query, "maxResults": MAX_EMAILS})
    return [message["id"] for message in body.get("messages", [])]


def fetch_message(message_id: str) -> dict:
    """One full message: headers, body parts and all."""
    return _get(f"/messages/{message_id}", {"format": "full"})


def send_email(to: str, subject: str, body: str) -> str:
    """Send mail as the connected account. Returns the new message id."""
    message = EmailMessage()
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    response = httpx.post(
        f"{API}/messages/send",
        json={"raw": raw},
        headers=google_auth.headers(),
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["id"]


def execute_action(action: PlannedAction) -> str:
    """Perform one approved action and return a short human-readable result.

    `target` is the recipient and `value` is what to tell them; the subject comes
    from params.subject when the plan set one, otherwise from the step description.
    """
    if action.type != "send_email":
        raise NotImplementedError(f"Gmail action not implemented: {action.type}")

    to = action.target
    body = action.params.get("value")
    if not to or not body:
        raise ValueError("Gmail send_email needs a target (recipient) and params.value (body)")

    subject = action.params.get("subject") or action.description
    message_id = send_email(to, subject, body)
    return f'Emailed {to} — subject "{subject}" (Gmail id {message_id})'


# --- normalization -----------------------------------------------------------


def _to_evidence(message: dict) -> Evidence:
    headers = _headers(message)
    body = _plain_text(message.get("payload", {})) or message.get("snippet", "")
    return Evidence(
        source="gmail",
        type="email",
        title=headers.get("subject", "(no subject)"),
        content=f"From: {headers.get('from', 'unknown')}\nTo: {headers.get('to', '')}\n\n{body[:MAX_BODY_CHARS]}",
        url=f"https://mail.google.com/mail/u/0/#all/{message['id']}",
        timestamp=_sent_at(message),
        metadata={
            "from": headers.get("from"),
            "to": headers.get("to"),
            "cc": headers.get("cc"),
            "thread_id": message.get("threadId"),
            "labels": message.get("labelIds", []),
        },
    )


def _headers(message: dict) -> dict[str, str]:
    """Gmail returns headers as a list of name/value pairs; this makes them addressable."""
    return {
        header["name"].lower(): header["value"]
        for header in message.get("payload", {}).get("headers", [])
    }


def _plain_text(payload: dict) -> str:
    """The first text/plain part, walking nested multipart messages."""
    data = payload.get("body", {}).get("data")
    if payload.get("mimeType") == "text/plain" and data:
        return base64.urlsafe_b64decode(data + "===").decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        text = _plain_text(part)
        if text:
            return text
    return ""


def _sent_at(message: dict) -> str | None:
    """internalDate is epoch milliseconds as a string."""
    internal = message.get("internalDate")
    if not internal:
        return None
    return datetime.fromtimestamp(int(internal) / 1000, tz=UTC).isoformat()


def _get(path: str, params: dict) -> dict:
    response = httpx.get(f"{API}{path}", params=params, headers=google_auth.headers(), timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()
