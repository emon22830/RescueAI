"""Notion. Reads project evidence; write actions live in execute_action().

Each project connects its own internal integration token from the frontend. Notion only
returns pages the integration has been *shared with* — an empty result usually means
nobody added it to the page, not that the page is missing, so that is what the log says.

Two Notion shapes worth knowing:

- **The version header is mandatory.** Every request carries `Notion-Version`; without
  it the API refuses, and the value pins the response shape.
- **A page's text is not on the page.** Search returns properties and a URL; the prose
  lives in the page's blocks, fetched separately and flattened by `_block_text`.
"""

import logging

import httpx

from app.agents.state import Evidence, PlannedAction

logger = logging.getLogger(__name__)

API = "https://api.notion.com/v1"
NOTION_VERSION = "2026-03-11"
TIMEOUT = 30.0
MAX_PAGES = 12
MAX_BLOCKS = 60
MAX_CHARS = 4000


class NotionError(RuntimeError):
    """Notion refused the request. The reason is in the body's `message`."""


def collect_evidence(project_id: str, project_name: str) -> list[Evidence]:
    """Pages that name the project, most recently edited first, with their text."""
    from app.projects import service

    credential = service.get_integration_credential(project_id, "notion")
    if credential is None:
        logger.warning("Notion skipped: project %s has not connected Notion", project_id)
        return []

    token = credential["token"]
    pages = search_pages(project_name, token)
    if not pages:
        logger.info(
            "Notion returned nothing for '%s' — the integration may not be shared with "
            "the pages about this project",
            project_name,
        )

    return [_to_evidence(page, page_text(page["id"], token)) for page in pages[:MAX_PAGES]]


def verify_token(token: str) -> dict:
    """Confirm the integration token works before it is stored."""
    me = _get("/users/me", token)
    return {
        "account": me.get("name") or (me.get("bot") or {}).get("workspace_name", ""),
        "workspace": (me.get("bot") or {}).get("workspace_name", ""),
    }


def search_pages(project_name: str, token: str) -> list[dict]:
    body = _post(
        "/search",
        {
            "query": project_name,
            "filter": {"property": "object", "value": "page"},
            "sort": {"timestamp": "last_edited_time", "direction": "descending"},
            "page_size": MAX_PAGES,
        },
        token,
    )
    return body.get("results", [])


def page_text(page_id: str, token: str) -> str:
    """The page's prose. A page we cannot read is still worth listing by title, so an
    unreadable body degrades to empty rather than failing the whole collection."""
    try:
        body = _get(f"/blocks/{page_id}/children", token, {"page_size": MAX_BLOCKS})
    except NotionError as error:
        logger.warning("Notion page %s body unreadable: %s", page_id, error)
        return ""

    lines = [_block_text(block) for block in body.get("results", [])]
    return "\n".join(line for line in lines if line)[:MAX_CHARS]


# --- write actions -----------------------------------------------------------


def execute_action(action: PlannedAction) -> str:
    """Perform one approved action and return a short human-readable result."""
    from app.projects import service

    credential = service.get_integration_credential(action.project_id, "notion")
    if credential is None:
        raise RuntimeError("Notion is not connected for this project")

    token = credential["token"]
    body = action.params.get("value", "")

    if action.type == "create_page":
        if not action.target:
            raise ValueError("Notion create_page needs a target (the page title)")
        parent = action.params.get("parent", "")
        if not parent:
            raise ValueError(
                "Notion create_page needs params.parent — the id of the page to create it under"
            )
        return create_page(action.target, body or action.description, parent, token)

    if not action.target:
        raise ValueError(f"Notion {action.type} needs a target (the page id)")

    if action.type == "comment_page":
        if not body:
            raise ValueError("Notion comment_page needs params.value")
        return comment_on_page(action.target.strip(), body, token)

    raise NotImplementedError(f"Notion action not implemented: {action.type}")


def create_page(title: str, text: str, parent_page_id: str, token: str) -> str:
    page = _post(
        "/pages",
        {
            "parent": {"page_id": parent_page_id},
            "properties": {"title": {"title": [{"text": {"content": title}}]}},
            "children": [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"text": {"content": line}}]},
                }
                for line in text.split("\n")
                if line.strip()
            ],
        },
        token,
    )
    return f"Created \"{title}\" — {page.get('url', '')}".strip()


def comment_on_page(page_id: str, text: str, token: str) -> str:
    _post("/comments", {"parent": {"page_id": page_id},
                        "rich_text": [{"text": {"content": text}}]}, token)
    return f"Commented on Notion page {page_id}"


# --- normalization -----------------------------------------------------------


def _to_evidence(page: dict, text: str) -> Evidence:
    title = _title_of(page)
    return Evidence(
        source="notion",
        type="document",
        title=title,
        content=f"{title}\n\n{text}".strip(),
        url=page.get("url"),
        timestamp=page.get("last_edited_time"),
        metadata={
            "page_id": page.get("id"),
            "created": page.get("created_time"),
            "edited_by": (page.get("last_edited_by") or {}).get("id"),
            "in_trash": bool(page.get("in_trash")),
        },
    )


def _title_of(page: dict) -> str:
    """A page's title is whichever property happens to be of type `title`. Notion does
    not promise what it is called, so it is found by type, not by name."""
    for prop in (page.get("properties") or {}).values():
        if prop.get("type") == "title":
            return _rich_text(prop.get("title")) or "Untitled"
    return "Untitled"


def _block_text(block: dict) -> str:
    """One block as a line. Every text-bearing block type keeps its content under its
    own name, so the type is the key."""
    kind = block.get("type", "")
    content = block.get(kind) or {}
    text = _rich_text(content.get("rich_text"))
    if not text:
        return ""

    if kind == "to_do":
        return f"[{'x' if content.get('checked') else ' '}] {text}"
    if kind in ("bulleted_list_item", "numbered_list_item"):
        return f"- {text}"
    if kind.startswith("heading"):
        return f"\n{text}"
    return text


def _rich_text(parts: object) -> str:
    if not isinstance(parts, list):
        return ""
    return "".join(part.get("plain_text") or "" for part in parts if isinstance(part, dict))


# --- http --------------------------------------------------------------------


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _get(path: str, token: str, params: dict | None = None) -> dict:
    return _read(httpx.get(f"{API}{path}", params=params or {}, headers=_headers(token),
                           timeout=TIMEOUT), path)


def _post(path: str, payload: dict, token: str) -> dict:
    return _read(httpx.post(f"{API}{path}", json=payload, headers=_headers(token),
                            timeout=TIMEOUT), path)


def _read(response, path: str) -> dict:
    if response.status_code >= 400:
        try:
            detail = response.json().get("message", "")
        except Exception:  # noqa: BLE001
            detail = ""
        raise NotionError(
            f"Notion {path} failed ({response.status_code}): {detail or response.text[:200]}"
        )
    return response.json()
