"""Asana. Reads project evidence; write actions live in execute_action().

Each project connects its own personal access token from the frontend, and the
workspace is discovered when that token is verified rather than asked for — one
fewer thing to paste, and one fewer thing to get wrong.

Asana's own search (`/workspaces/{gid}/tasks/search`) is a paid feature, so this
finds the project by typeahead and then reads that project's tasks. Typeahead is
explicitly "fast, not exhaustive" in Asana's docs, which is fine for locating a
project by name and would not be fine for collecting the evidence itself.
"""

import logging

import httpx

from app.agents.state import Evidence, PlannedAction

logger = logging.getLogger(__name__)

API = "https://app.asana.com/api/1.0"
TIMEOUT = 30.0
MAX_PROJECTS = 3
MAX_TASKS = 40

TASK_FIELDS = (
    "name,notes,completed,completed_at,due_on,modified_at,created_at,permalink_url,"
    "assignee.name,projects.name,memberships.section.name"
)


class AsanaError(RuntimeError):
    """Asana refused the request. The reason is in the body's `errors` list."""


def collect_evidence(project_id: str, project_name: str) -> list[Evidence]:
    """Tasks in the Asana projects whose name matches this project."""
    from app.projects import service

    credential = service.get_integration_credential(project_id, "asana")
    if credential is None:
        logger.warning("Asana skipped: project %s has not connected Asana", project_id)
        return []

    token = credential["token"]
    workspace = credential.get("workspace", "")
    if not workspace:
        logger.warning("Asana skipped: project %s stored no workspace", project_id)
        return []

    evidence: list[Evidence] = []
    for project in find_projects(project_name, workspace, token)[:MAX_PROJECTS]:
        for task in project_tasks(project["gid"], token):
            evidence.append(_to_evidence(task, project["name"]))
            if len(evidence) >= MAX_TASKS:
                return evidence
    return evidence


def verify_token(token: str, workspace: str = "") -> dict:
    """Confirm the token works and remember which workspace it belongs to."""
    me = _get("/users/me", {"opt_fields": "name,email,workspaces.name"}, token)
    workspaces = me.get("workspaces") or []
    if not workspaces:
        raise AsanaError("This Asana token can see no workspaces")

    chosen = next((w for w in workspaces if w["gid"] == workspace), None) if workspace else None
    chosen = chosen or workspaces[0]
    return {
        "workspace": chosen["gid"],
        "workspace_name": chosen.get("name", ""),
        "account": me.get("name", ""),
    }


def find_projects(project_name: str, workspace: str, token: str) -> list[dict]:
    """Asana projects whose name looks like this project's."""
    return _get(
        f"/workspaces/{workspace}/typeahead",
        {"resource_type": "project", "query": project_name, "count": 20},
        token,
    )


def project_tasks(project_gid: str, token: str) -> list[dict]:
    return _get(f"/projects/{project_gid}/tasks",
                {"opt_fields": TASK_FIELDS, "limit": MAX_TASKS}, token)


# --- write actions -----------------------------------------------------------


def execute_action(action: PlannedAction) -> str:
    """Perform one approved action and return a short human-readable result."""
    from app.projects import service

    credential = service.get_integration_credential(action.project_id, "asana")
    if credential is None:
        raise RuntimeError("Asana is not connected for this project")

    token = credential["token"]
    workspace = credential.get("workspace", "")
    body = action.params.get("value", "")

    if action.type == "create_task":
        if not action.target:
            raise ValueError("Asana create_task needs a target (the task name)")
        return create_task(action.target, body or action.description, workspace, token,
                           project=action.params.get("project", ""),
                           due_date=action.params.get("due_date", ""))

    if not action.target:
        raise ValueError(f"Asana {action.type} needs a target (the task id)")
    gid = action.target.strip()

    if action.type == "comment_task":
        return comment_on_task(gid, _required(body, "comment_task"), token)
    if action.type == "assign_task":
        return assign_task(gid, _required(body, "assign_task"), workspace, token)
    if action.type == "update_due_date":
        return update_due_date(gid, _required(body, "update_due_date"), token)
    if action.type == "close_task":
        return complete_task(gid, token)

    raise NotImplementedError(f"Asana action not implemented: {action.type}")


def create_task(
    name: str, notes: str, workspace: str, token: str, project: str = "", due_date: str = ""
) -> str:
    fields: dict = {"name": name, "notes": notes, "workspace": workspace}
    if project:
        fields["projects"] = [_project_gid(project, workspace, token)]
    if due_date:
        fields["due_on"] = due_date

    task = _post("/tasks", fields, token)
    return f"Created \"{task.get('name', name)}\" — {task.get('permalink_url', '')}".strip()


def comment_on_task(gid: str, text: str, token: str) -> str:
    _post(f"/tasks/{gid}/stories", {"text": text}, token)
    return f"Commented on Asana task {gid}"


def assign_task(gid: str, person: str, workspace: str, token: str) -> str:
    user = find_user(person, workspace, token)
    if user is None:
        raise AsanaError(f"No Asana user matching '{person}' in this workspace")

    task = _put(f"/tasks/{gid}", {"assignee": user["gid"]}, token)
    return f"Assigned to {user.get('name', person)} — {task.get('permalink_url', '')}".strip()


def update_due_date(gid: str, due_date: str, token: str) -> str:
    task = _put(f"/tasks/{gid}", {"due_on": due_date}, token)
    return f"Due {due_date} — {task.get('permalink_url', '')}".strip()


def complete_task(gid: str, token: str) -> str:
    task = _put(f"/tasks/{gid}", {"completed": True}, token)
    return f"Completed \"{task.get('name', gid)}\" — {task.get('permalink_url', '')}".strip()


def find_user(person: str, workspace: str, token: str) -> dict | None:
    users = _get(f"/workspaces/{workspace}/typeahead",
                 {"resource_type": "user", "query": person, "count": 20}, token)
    if not users:
        return None

    term = person.strip().lower()
    return next((u for u in users if (u.get("name") or "").lower() == term), users[0])


def _project_gid(project: str, workspace: str, token: str) -> str:
    """A plan may name the project instead of knowing its id."""
    if project.isdigit():
        return project

    matches = find_projects(project, workspace, token)
    if not matches:
        raise AsanaError(f"No Asana project called '{project}' in this workspace")
    return matches[0]["gid"]


# --- normalization -----------------------------------------------------------


def _to_evidence(task: dict, project_name: str) -> Evidence:
    assignee = (task.get("assignee") or {}).get("name") or "unassigned"
    state = "completed" if task.get("completed") else "open"
    due = task.get("due_on") or "no due date"

    return Evidence(
        source="asana",
        type="task",
        title=task.get("name", "Untitled task"),
        content=(
            f"Project: {project_name}\nStatus: {state}\nAssignee: {assignee}\nDue: {due}\n\n"
            f"{task.get('notes', '')}"
        ).strip(),
        url=task.get("permalink_url"),
        timestamp=task.get("modified_at"),
        metadata={
            "gid": task.get("gid"),
            "completed": bool(task.get("completed")),
            "assignee": assignee,
            "due_date": task.get("due_on"),
            "project": project_name,
        },
    )


def _required(value: str, action_type: str) -> str:
    if not value:
        raise ValueError(f"Asana {action_type} needs params.value")
    return value


# --- http --------------------------------------------------------------------
#
# Asana wraps everything it returns in {"data": ...} and everything it is sent in
# {"data": ...}, so the wrapper is handled once here rather than at each call site.


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


def _get(path: str, params: dict, token: str):
    return _unwrap(httpx.get(f"{API}{path}", params=params, headers=_headers(token),
                             timeout=TIMEOUT), path)


def _post(path: str, fields: dict, token: str) -> dict:
    return _unwrap(httpx.post(f"{API}{path}", json={"data": fields}, headers=_headers(token),
                              timeout=TIMEOUT), path)


def _put(path: str, fields: dict, token: str) -> dict:
    return _unwrap(httpx.put(f"{API}{path}", json={"data": fields}, headers=_headers(token),
                             timeout=TIMEOUT), path)


def _unwrap(response, path: str):
    if response.status_code >= 400:
        try:
            reasons = [error.get("message", "") for error in response.json().get("errors", [])]
        except Exception:  # noqa: BLE001
            reasons = []
        detail = "; ".join(filter(None, reasons)) or response.text[:200]
        raise AsanaError(f"Asana {path} failed ({response.status_code}): {detail}")
    return response.json().get("data")
