"""Linear. Reads project evidence; write actions live in execute_action().

Each project connects its own personal API key from the frontend (see
projects/service.py connect_integration), so every function here takes the key
explicitly rather than reading one shared value off app.config.settings.
"""

import logging

import httpx

from app.agents.state import Evidence, PlannedAction

logger = logging.getLogger(__name__)

API = "https://api.linear.app/graphql"
TIMEOUT = 20.0
MAX_ISSUES = 50

ISSUE_FIELDS = """
  identifier
  title
  description
  url
  priority
  dueDate
  createdAt
  updatedAt
  state { name type }
  assignee { name email }
  project { name }
  team { key name }
"""


class LinearError(RuntimeError):
    """Linear answers 200 with an `errors` array — the reason is in the body."""


def collect_evidence(project_id: str, project_name: str) -> list[Evidence]:
    """The Linear project and its issues: status, assignee and due date for each."""
    from app.projects import service

    credential = service.get_integration_credential(project_id, "linear")
    if credential is None:
        logger.warning("Linear skipped: project %s has not connected Linear", project_id)
        return []

    token = credential["token"]
    evidence = [_project_evidence(project) for project in find_projects(project_name, token)]
    evidence += [_issue_evidence(issue) for issue in find_issues(project_name, token)]
    return evidence


def verify_token(token: str) -> dict:
    """Confirm the key actually works before it is stored. Called by the connect flow."""
    query = "query { viewer { name email } }"
    viewer = graphql(query, {}, token)["viewer"]
    return {"user": viewer.get("name", ""), "email": viewer.get("email", "")}


def find_projects(project_name: str, token: str) -> list[dict]:
    """Linear projects whose name contains the project name."""
    query = """
      query($name: String!) {
        projects(filter: { name: { containsIgnoreCase: $name } }, first: 3) {
          nodes {
            id name description url state progress startDate targetDate
            lead { name email }
          }
        }
      }
    """
    return graphql(query, {"name": project_name}, token)["projects"]["nodes"]


def find_issues(project_name: str, token: str) -> list[dict]:
    """Issues in a matching project, or whose own title or description names it."""
    query = """
      query($name: String!, $limit: Int!) {
        issues(
          filter: {
            or: [
              { project: { name: { containsIgnoreCase: $name } } }
              { title: { containsIgnoreCase: $name } }
              { description: { containsIgnoreCase: $name } }
            ]
          }
          first: $limit
          orderBy: updatedAt
        ) {
          nodes { %s }
        }
      }
    """ % ISSUE_FIELDS
    return graphql(query, {"name": project_name, "limit": MAX_ISSUES}, token)["issues"]["nodes"]


# --- write actions -----------------------------------------------------------


def update_issue_state(identifier: str, state_name: str, token: str) -> str:
    """Move an issue to a workflow state by name, e.g. "In Progress" or "Done"."""
    issue = fetch_issue(identifier, token)
    states = issue["team"]["states"]["nodes"]
    state = next((s for s in states if s["name"].lower() == state_name.lower()), None)
    if state is None:
        available = ", ".join(s["name"] for s in states)
        raise LinearError(f"{identifier}: no state called '{state_name}'. Team states are: {available}")

    updated = _update(issue["id"], {"stateId": state["id"]}, token)
    return f"{identifier} moved to {updated['state']['name']} — {updated['url']}"


def assign_issue(identifier: str, person: str, token: str) -> str:
    """Assign an issue to a teammate, found by email or by name."""
    issue = fetch_issue(identifier, token)
    user = find_user(person, token)
    if user is None:
        raise LinearError(f"{identifier}: no active Linear user matching '{person}'")

    updated = _update(issue["id"], {"assigneeId": user["id"]}, token)
    return f"{identifier} assigned to {updated['assignee']['name']} — {updated['url']}"


def update_due_date(identifier: str, due_date: str, token: str) -> str:
    """Set an issue's due date. `due_date` is an ISO date: 2026-10-01."""
    issue = fetch_issue(identifier, token)
    updated = _update(issue["id"], {"dueDate": due_date}, token)
    return f"{identifier} due {updated['dueDate']} — {updated['url']}"


def comment_on_issue(identifier: str, body: str, token: str) -> str:
    """Post a comment on an issue."""
    issue = fetch_issue(identifier, token)
    mutation = """
      mutation($input: CommentCreateInput!) {
        commentCreate(input: $input) { success comment { url } }
      }
    """
    result = graphql(mutation, {"input": {"issueId": issue["id"], "body": body}}, token)["commentCreate"]
    if not result["success"]:
        raise LinearError(f"{identifier}: Linear rejected the comment")
    return f"Commented on {identifier} — {result['comment']['url']}"


def fetch_issue(identifier: str, token: str) -> dict:
    """One issue by its identifier ("PAY-124"), with its team's workflow states."""
    query = """
      query($id: String!) {
        issue(id: $id) {
          id identifier title url dueDate
          state { name }
          assignee { name }
          team { id states(first: 60) { nodes { id name type } } }
        }
      }
    """
    issue = graphql(query, {"id": identifier}, token)["issue"]
    if issue is None:
        raise LinearError(f"No Linear issue called '{identifier}'")
    return issue


def find_user(person: str, token: str) -> dict | None:
    """An active Linear user matched on email first, then on name."""
    query = "query { users(first: 250) { nodes { id name displayName email active } } }"
    users = [user for user in graphql(query, {}, token)["users"]["nodes"] if user["active"]]

    term = person.strip().lower()
    by_email = next((user for user in users if (user["email"] or "").lower() == term), None)
    if by_email:
        return by_email
    return next(
        (
            user
            for user in users
            if term in user["name"].lower() or term in (user["displayName"] or "").lower()
        ),
        None,
    )


def execute_action(action: PlannedAction) -> str:
    """Perform one approved action and return a short human-readable result.

    `target` is the issue identifier. A plan that carries structured params
    (`state`, `assignee`, `due_date`) applies them directly; a plan that only
    describes the change in `value` has that text posted as a comment on the
    issue rather than guessed at.
    """
    from app.projects import service

    credential = service.get_integration_credential(action.project_id, "linear")
    if credential is None:
        raise RuntimeError("Linear is not connected for this project")
    token = credential["token"]

    if not action.target:
        raise ValueError(f"Linear {action.type} needs a target (the issue identifier)")

    if action.type == "assign_task":
        return assign_issue(action.target, _required(action, "value"), token)
    if action.type == "update_due_date":
        return update_due_date(action.target, _required(action, "value"), token)
    if action.type == "update_issue":
        return _apply_issue_update(action, action.target, token)

    raise NotImplementedError(f"Linear action not implemented: {action.type}")


def _apply_issue_update(action: PlannedAction, identifier: str, token: str) -> str:
    results = []
    if state := action.params.get("state"):
        results.append(update_issue_state(identifier, state, token))
    if assignee := action.params.get("assignee"):
        results.append(assign_issue(identifier, assignee, token))
    if due_date := action.params.get("due_date"):
        results.append(update_due_date(identifier, due_date, token))

    if results:
        return " · ".join(results)
    return comment_on_issue(identifier, _required(action, "value"), token)


def _update(issue_id: str, fields: dict, token: str) -> dict:
    mutation = """
      mutation($id: String!, $input: IssueUpdateInput!) {
        issueUpdate(id: $id, input: $input) {
          success
          issue { identifier url dueDate state { name } assignee { name } }
        }
      }
    """
    result = graphql(mutation, {"id": issue_id, "input": fields}, token)["issueUpdate"]
    if not result["success"]:
        raise LinearError(f"Linear rejected the update: {fields}")
    return result["issue"]


# --- normalization -----------------------------------------------------------


def _project_evidence(project: dict) -> Evidence:
    lead = (project.get("lead") or {}).get("name", "unassigned")
    content = "\n".join(
        [
            f"State: {project.get('state', 'unknown')}",
            f"Lead: {lead}",
            f"Progress: {round((project.get('progress') or 0) * 100)}%",
            f"Starts: {project.get('startDate') or 'not set'}",
            f"Target date: {project.get('targetDate') or 'not set'}",
            "",
            project.get("description") or "",
        ]
    ).strip()
    return Evidence(
        source="linear",
        type="project",
        title=f"Linear project: {project['name']}",
        content=content,
        url=project.get("url"),
        timestamp=None,
        metadata={
            "state": project.get("state"),
            "progress": project.get("progress"),
            "target_date": project.get("targetDate"),
            "lead": lead,
        },
    )


def _issue_evidence(issue: dict) -> Evidence:
    state = (issue.get("state") or {}).get("name", "unknown")
    assignee = (issue.get("assignee") or {}).get("name", "unassigned")
    due_date = issue.get("dueDate") or "not set"
    content = "\n".join(
        [
            f"State: {state}",
            f"Assignee: {assignee}",
            f"Due: {due_date}",
            f"Priority: {issue.get('priority', 0)}",
            f"Last updated: {issue.get('updatedAt')}",
            "",
            issue.get("description") or "",
        ]
    ).strip()
    return Evidence(
        source="linear",
        type="issue",
        title=f"{issue['identifier']} {issue['title']} [{state}]",
        content=content,
        url=issue.get("url"),
        timestamp=issue.get("updatedAt"),
        metadata={
            "identifier": issue["identifier"],
            "state": state,
            "state_type": (issue.get("state") or {}).get("type"),
            "assignee": assignee,
            "due_date": issue.get("dueDate"),
            "priority": issue.get("priority"),
            "project": (issue.get("project") or {}).get("name"),
            "team": (issue.get("team") or {}).get("key"),
        },
    )


def _required(action: PlannedAction, key: str) -> str:
    value = action.params.get(key)
    if not value:
        raise ValueError(f"Linear {action.type} needs params.{key}")
    return str(value)


def graphql(query: str, variables: dict, token: str) -> dict:
    """One GraphQL call. Linear reports failures in the body, not the status code."""
    response = httpx.post(
        API,
        json={"query": query, "variables": variables},
        headers={"Authorization": token, "Content-Type": "application/json"},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    body = response.json()
    if "errors" in body:
        raise LinearError(f"Linear API error: {body['errors'][0].get('message', body['errors'])}")
    return body["data"]
