"""Jira Cloud. Reads project evidence; write actions live in execute_action().

Each project connects its own site, account email and API token from the frontend
(see projects/service.py connect_integration), so every function here takes them
explicitly rather than reading one shared value off app.config.settings.

Two things about Jira Cloud that shape this file:

- **Search moved.** `/rest/api/3/search` was deprecated in May 2025 and fully removed
  from Jira Cloud by the end of October 2025. The endpoint is `/rest/api/3/search/jql`,
  it pages on `nextPageToken` rather than `startAt`, and it returns *only* `id` and
  `key` unless `fields` is given explicitly.
- **Text is not text.** The v3 API speaks Atlassian Document Format: a description or a
  comment is a nested document, not a string. `_adf` builds one and `_adf_text` flattens
  one back, because the agent reasons over plain prose.
"""

import base64
import logging
from datetime import UTC, datetime, timedelta

import httpx

from app.agents.state import Evidence, PlannedAction

logger = logging.getLogger(__name__)

TIMEOUT = 30.0
LOOKBACK_DAYS = 30
MAX_ISSUES = 40


class JiraError(RuntimeError):
    """Jira refused the request — a bad token, a site that is not there, or bad JQL."""


def collect_evidence(project_id: str, project_name: str) -> list[Evidence]:
    """Issues that name the project, or sit in a Jira project of the same name."""
    from app.projects import service

    credential = service.get_integration_credential(project_id, "jira")
    if credential is None:
        logger.warning("Jira skipped: project %s has not connected Jira", project_id)
        return []

    site = credential.get("site", "")
    email = credential.get("email", "")
    token = credential["token"]
    if not site or not email:
        logger.warning("Jira skipped: project %s stored no site or email", project_id)
        return []

    issues = search_issues(project_name, site, email, token, credential.get("project_key", ""))
    return [_to_evidence(issue, site) for issue in issues]


def verify_token(token: str, site: str = "", email: str = "", project_key: str = "") -> dict:
    """Confirm the credential works against this site before it is stored."""
    if not site:
        raise JiraError("Jira needs the site it belongs to, e.g. acme.atlassian.net")
    if not email:
        raise JiraError("Jira needs the account email the API token was issued for")

    me = _get("/rest/api/3/myself", {}, base_url(site), email, token)
    return {
        "site": base_url(site),
        "email": email,
        "account": me.get("displayName", ""),
        "account_id": me.get("accountId", ""),
    }


def base_url(site: str) -> str:
    """People paste the host, the full URL, or the URL of whatever page they were on.
    All three mean the same site."""
    cleaned = site.strip().rstrip("/")
    cleaned = cleaned.removeprefix("https://").removeprefix("http://")
    host = cleaned.split("/")[0]
    if not host:
        raise JiraError(f"'{site}' is not a Jira site. It looks like acme.atlassian.net")
    return f"https://{host}"


def search_issues(
    project_name: str, site: str, email: str, token: str, project_key: str = ""
) -> list[dict]:
    """Recently updated issues matching the project, newest first.

    `fields` is not optional in practice: without it this endpoint returns an issue
    with nothing but an id and a key, and there is no evidence in that.
    """
    since = (datetime.now(UTC) - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    match = f'text ~ "{_escape(project_name)}"'
    if project_key:
        match = f'(project = "{_escape(project_key)}" OR {match})'

    body = _post(
        "/rest/api/3/search/jql",
        {
            "jql": f"{match} AND updated >= '{since}' ORDER BY updated DESC",
            "fields": [
                "summary", "status", "assignee", "reporter", "duedate",
                "updated", "created", "priority", "issuetype", "project", "description",
            ],
            "maxResults": MAX_ISSUES,
        },
        site,
        email,
        token,
    )
    return body.get("issues", [])


# --- write actions -----------------------------------------------------------


def execute_action(action: PlannedAction) -> str:
    """Perform one approved action and return a short human-readable result."""
    from app.projects import service

    credential = service.get_integration_credential(action.project_id, "jira")
    if credential is None:
        raise RuntimeError("Jira is not connected for this project")

    site, email, token = credential.get("site", ""), credential.get("email", ""), credential["token"]
    if not site or not email:
        raise RuntimeError("This project connected Jira without a site or account email")

    body = action.params.get("value", "")
    args = (site, email, token)

    if action.type == "create_issue":
        if not action.target:
            raise ValueError("Jira create_issue needs a target (the issue summary)")
        key = action.params.get("project") or credential.get("project_key", "")
        if not key:
            raise ValueError(
                "Jira create_issue needs params.project — the project key the issue "
                "belongs in, e.g. PAY"
            )
        return create_issue(key, action.target, body or action.description, *args,
                            issue_type=action.params.get("issue_type", "Task"),
                            due_date=action.params.get("due_date", ""))

    if not action.target:
        raise ValueError(f"Jira {action.type} needs a target (the issue key, e.g. PAY-124)")
    key = action.target.strip().upper()

    if action.type == "comment_issue":
        return comment_on_issue(key, _required(body, "comment_issue"), *args)
    if action.type == "assign_task":
        return assign_issue(key, _required(body, "assign_task"), *args)
    if action.type == "update_due_date":
        return update_due_date(key, _required(body, "update_due_date"), *args)
    if action.type == "close_issue":
        return close_issue(key, body.strip(), *args)

    raise NotImplementedError(f"Jira action not implemented: {action.type}")


def create_issue(
    project_key: str, summary: str, description: str, site: str, email: str, token: str,
    issue_type: str = "Task", due_date: str = "",
) -> str:
    fields: dict = {
        "project": {"key": project_key.strip().upper()},
        "summary": summary,
        "issuetype": {"name": issue_type},
        "description": _adf(description),
    }
    if due_date:
        fields["duedate"] = due_date

    created = _post("/rest/api/3/issue", {"fields": fields}, site, email, token)
    key = created["key"]
    return f"Created {key} — {site}/browse/{key}"


def comment_on_issue(key: str, body: str, site: str, email: str, token: str) -> str:
    _post(f"/rest/api/3/issue/{key}/comment", {"body": _adf(body)}, site, email, token)
    return f"Commented on {key} — {site}/browse/{key}"


def assign_issue(key: str, person: str, site: str, email: str, token: str) -> str:
    """Assign by name or email. Jira wants an accountId, never a username."""
    user = find_user(person, site, email, token)
    if user is None:
        raise JiraError(f"{key}: no Jira user matching '{person}' on this site")

    _put(f"/rest/api/3/issue/{key}/assignee", {"accountId": user["accountId"]}, site, email, token)
    return f"{key} assigned to {user.get('displayName', person)} — {site}/browse/{key}"


def update_due_date(key: str, due_date: str, site: str, email: str, token: str) -> str:
    _put(f"/rest/api/3/issue/{key}", {"fields": {"duedate": due_date}}, site, email, token)
    return f"{key} due {due_date} — {site}/browse/{key}"


def close_issue(key: str, status_name: str, site: str, email: str, token: str) -> str:
    """Close by transition, because Jira has no settable "status" field.

    Which transition means "closed" is a per-workflow question, so the named one wins
    and otherwise the first transition into the `done` status category is used.
    """
    available = _get(f"/rest/api/3/issue/{key}/transitions", {}, site, email, token)
    transitions = available.get("transitions", [])
    if not transitions:
        raise JiraError(f"{key}: no transitions are available to this account")

    if status_name:
        wanted = status_name.strip().lower()
        chosen = next((t for t in transitions if t["name"].lower() == wanted), None)
        if chosen is None:
            names = ", ".join(t["name"] for t in transitions)
            raise JiraError(f"{key}: no transition called '{status_name}'. Available: {names}")
    else:
        chosen = next(
            (t for t in transitions
             if (t.get("to") or {}).get("statusCategory", {}).get("key") == "done"),
            None,
        )
        if chosen is None:
            names = ", ".join(t["name"] for t in transitions)
            raise JiraError(f"{key}: no transition leads to Done. Name one instead: {names}")

    _post(f"/rest/api/3/issue/{key}/transitions", {"transition": {"id": chosen["id"]}},
          site, email, token)
    return f"{key} moved to {chosen['name']} — {site}/browse/{key}"


def find_user(person: str, site: str, email: str, token: str) -> dict | None:
    users = _get("/rest/api/3/user/search", {"query": person, "maxResults": 20},
                 site, email, token)
    if not users:
        return None

    term = person.strip().lower()
    exact = next(
        (u for u in users
         if (u.get("emailAddress") or "").lower() == term
         or (u.get("displayName") or "").lower() == term),
        None,
    )
    return exact or users[0]


# --- normalization -----------------------------------------------------------


def _to_evidence(issue: dict, site: str) -> Evidence:
    fields = issue.get("fields") or {}
    key = issue["key"]
    status = (fields.get("status") or {}).get("name", "unknown")
    assignee = (fields.get("assignee") or {}).get("displayName") or "unassigned"
    due = fields.get("duedate") or "no due date"
    description = _adf_text(fields.get("description"))

    return Evidence(
        source="jira",
        type="issue",
        title=f"{key}: {fields.get('summary', '')}".strip(),
        content=(
            f"Status: {status}\nAssignee: {assignee}\nDue: {due}\n"
            f"Type: {(fields.get('issuetype') or {}).get('name', 'Issue')}\n\n{description}"
        ).strip(),
        url=f"{site}/browse/{key}",
        timestamp=fields.get("updated"),
        metadata={
            "key": key,
            "status": status,
            "status_category": (fields.get("status") or {}).get("statusCategory", {}).get("key", ""),
            "assignee": assignee,
            "due_date": fields.get("duedate"),
            "priority": (fields.get("priority") or {}).get("name"),
            "project": (fields.get("project") or {}).get("key"),
        },
    )


def _adf(text: str) -> dict:
    """Plain prose as an Atlassian document. One paragraph per line, blanks dropped —
    an empty paragraph is what makes Jira reject the whole document."""
    paragraphs = [line for line in (text or "").split("\n") if line.strip()]
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": line}]}
            for line in paragraphs
        ]
        or [{"type": "paragraph", "content": []}],
    }


def _adf_text(node: object) -> str:
    """Flatten an Atlassian document back to prose. Jira hands descriptions and comments
    back as a nested tree; a model reasons about the words, not the tree."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(_adf_text(child) for child in node)
    if not isinstance(node, dict):
        return ""

    if node.get("type") == "text":
        return node.get("text", "")
    if node.get("type") == "hardBreak":
        return "\n"

    inner = _adf_text(node.get("content"))
    return f"{inner}\n" if node.get("type") in ("paragraph", "heading", "listItem") else inner


def _escape(value: str) -> str:
    """JQL string literals are double-quoted, so a quote or backslash inside one has to
    be escaped or the whole query is rejected as a syntax error."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _required(value: str, action_type: str) -> str:
    if not value:
        raise ValueError(f"Jira {action_type} needs params.value")
    return value


# --- http --------------------------------------------------------------------


def _headers(email: str, token: str) -> dict:
    """Jira Cloud takes the API token as HTTP Basic, paired with the account's email."""
    pair = base64.b64encode(f"{email}:{token}".encode()).decode()
    return {
        "Authorization": f"Basic {pair}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _get(path: str, params: dict, site: str, email: str, token: str):
    response = httpx.get(f"{site}{path}", params=params, headers=_headers(email, token),
                         timeout=TIMEOUT)
    _raise_for(response, path)
    return response.json()


def _post(path: str, payload: dict, site: str, email: str, token: str) -> dict:
    response = httpx.post(f"{site}{path}", json=payload, headers=_headers(email, token),
                          timeout=TIMEOUT)
    _raise_for(response, path)
    return response.json() if response.content else {}


def _put(path: str, payload: dict, site: str, email: str, token: str) -> dict:
    response = httpx.put(f"{site}{path}", json=payload, headers=_headers(email, token),
                         timeout=TIMEOUT)
    _raise_for(response, path)
    return response.json() if response.content else {}


def _raise_for(response, path: str) -> None:
    """Jira puts the real reason in `errorMessages`, and a raw 400 tells nobody anything."""
    if response.status_code < 400:
        return
    try:
        body = response.json()
        reasons = body.get("errorMessages") or list((body.get("errors") or {}).values())
    except Exception:  # noqa: BLE001 - an HTML error page, which has no reasons in it
        reasons = []
    detail = "; ".join(reasons) or response.text[:200]
    raise JiraError(f"Jira {path} failed ({response.status_code}): {detail}")
