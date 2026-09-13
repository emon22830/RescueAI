"""Google Drive. Reads project evidence; write actions live in execute_action()."""

import logging

import httpx

from app.agents.state import Evidence, PlannedAction
from app.integrations import google_auth

logger = logging.getLogger(__name__)

API = "https://www.googleapis.com/drive/v3"
TIMEOUT = 30.0
MAX_FILES = 15
MAX_CONTENT_CHARS = 8000

GOOGLE_DOC = "application/vnd.google-apps.document"
GOOGLE_SHEET = "application/vnd.google-apps.spreadsheet"
GOOGLE_SLIDES = "application/vnd.google-apps.presentation"

EXPORT_AS = {
    GOOGLE_DOC: "text/plain",
    GOOGLE_SHEET: "text/csv",
    GOOGLE_SLIDES: "text/plain",
}


def collect_evidence(project_id: str, project_name: str) -> list[Evidence]:
    """Specs and docs that mention the project, with their text read in.

    The text matters: a stale requirement only contradicts a Slack thread if the
    agent can read both.
    """
    if not google_auth.is_connected(project_id):
        logger.warning("Drive skipped: this project has not connected Google")
        return []

    return [
        _to_evidence(file, read_text(project_id, file))
        for file in search_files(project_id, project_name)
    ]


def search_files(project_id: str, project_name: str) -> list[dict]:
    """Files whose content or name mentions the project, most recently modified first."""
    escaped = project_name.replace("'", "\\'")
    body = _get(
        project_id,
        "/files",
        {
            "q": f"fullText contains '{escaped}' and trashed = false",
            "orderBy": "modifiedTime desc",
            "pageSize": MAX_FILES,
            "fields": "files(id,name,mimeType,modifiedTime,webViewLink,owners(displayName),lastModifyingUser(displayName))",
        },
    )
    return body.get("files", [])


def read_text(project_id: str, file: dict) -> str:
    """The readable text of a file: Google formats are exported, plain files downloaded.

    Anything else (a PDF, an image, a zip) has no text to give, so only its name
    and metadata become evidence.
    """
    mime_type = file["mimeType"]

    if mime_type in EXPORT_AS:
        response = _request(project_id, f"/files/{file['id']}/export", {"mimeType": EXPORT_AS[mime_type]})
    elif mime_type.startswith("text/") or mime_type == "application/json":
        response = _request(project_id, f"/files/{file['id']}", {"alt": "media"})
    else:
        return ""

    return response.text[:MAX_CONTENT_CHARS]


def execute_action(action: PlannedAction) -> str:
    """Perform one approved action and return a short human-readable result."""
    raise NotImplementedError(f"Google Drive action not implemented: {action.type}")


# --- normalization -----------------------------------------------------------


def _to_evidence(file: dict, text: str) -> Evidence:
    owner = (file.get("owners") or [{}])[0].get("displayName", "unknown")
    editor = (file.get("lastModifyingUser") or {}).get("displayName", "unknown")
    return Evidence(
        source="drive",
        type="document",
        title=file["name"],
        content=f"Owner: {owner}\nLast edited by: {editor}\n\n{text or '(no readable text in this file)'}",
        url=file.get("webViewLink"),
        timestamp=file.get("modifiedTime"),
        metadata={
            "file_id": file["id"],
            "mime_type": file["mimeType"],
            "owner": owner,
            "last_modified_by": editor,
            "modified_time": file.get("modifiedTime"),
        },
    )


def _get(project_id: str, path: str, params: dict) -> dict:
    return _request(project_id, path, params).json()


def _request(project_id: str, path: str, params: dict) -> httpx.Response:
    response = httpx.get(
        f"{API}{path}",
        params=params,
        headers=google_auth.headers(project_id),
        timeout=TIMEOUT,
        follow_redirects=True,
    )
    response.raise_for_status()
    return response
