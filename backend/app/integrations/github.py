"""GitHub. Reads project evidence; write actions live in execute_action().

Each project connects its own fine-grained token and repository from the frontend
(see projects/service.py connect_integration), so every function here takes them
explicitly rather than reading one shared value off app.config.settings.
"""

import logging
from datetime import UTC, datetime, timedelta

import httpx

from app.agents.state import Evidence, PlannedAction

logger = logging.getLogger(__name__)

API = "https://api.github.com"
TIMEOUT = 20.0
LOOKBACK_DAYS = 30
MAX_COMMITS = 30
MAX_PULL_REQUESTS = 20
MAX_ISSUES = 20


class GitHubError(RuntimeError):
    """The token could not read the repository — bad token, or it lacks access."""


def collect_evidence(project_id: str, project_name: str) -> list[Evidence]:
    """Recent activity in the project's repository: commits, pull requests, issues.

    The repository the project connected *is* the project, so activity is bounded
    by a recent window rather than filtered by name.
    """
    from app.projects import service

    credential = service.get_integration_credential(project_id, "github")
    if credential is None:
        logger.warning("GitHub skipped: project %s has not connected GitHub", project_id)
        return []

    token = credential["token"]
    repo = credential.get("repo", "")
    if not repo:
        logger.warning("GitHub skipped: project %s connected no repository", project_id)
        return []

    since = datetime.now(UTC) - timedelta(days=LOOKBACK_DAYS)

    evidence = [_commit_evidence(repo, commit) for commit in recent_commits(repo, since, token)]
    evidence += [_pull_request_evidence(pull) for pull in recent_pull_requests(repo, since, token)]
    evidence += [_issue_evidence(issue) for issue in recent_issues(repo, since, token)]
    return evidence


def verify_token(token: str, repo: str) -> dict:
    """Confirm the token can read this repository before it is stored.

    The stored form is always owner/name, but people paste what is in front of them:
    the bare name off the repository header, or the whole URL out of the address bar.
    Both are resolved here against what the token can actually see, because a 404 on
    `GET /repos/HeyAI` tells the user nothing about what they did wrong.
    """
    wanted = _clean_repo(repo)
    if not wanted:
        raise GitHubError("Enter the repository as owner/name, for example octocat/hello-world")

    if "/" not in wanted:
        return {"repo": _find_repo(wanted, token)}

    response = httpx.get(f"{API}/repos/{wanted}", headers=_headers(token), timeout=TIMEOUT)
    if response.status_code == 404:
        raise GitHubError(
            f"No repository '{wanted}' is visible with this token. Check the spelling, and "
            "that the token grants this repository read access to contents, issues and "
            "pull requests."
        )
    _raise_for_credential(response)
    return {"repo": response.json()["full_name"]}


def _clean_repo(repo: str) -> str:
    """owner/name out of whatever was pasted — a bare name, a URL, an SSH remote."""
    text = repo.strip()
    if "github.com" in text:
        # https://github.com/owner/name/tree/main, or git@github.com:owner/name.git
        text = text.split("github.com", 1)[1]
    parts = [part for part in text.strip("/:").split("/") if part]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0].removesuffix(".git")
    return f"{parts[0]}/{parts[1].removesuffix('.git')}"


def _find_repo(name: str, token: str) -> str:
    """Resolve a bare repository name against the repositories this token can read.

    The token's own account first, since that is nearly always the answer, then every
    repository it was granted — which is how one owned by an organization is found.
    """
    account = httpx.get(f"{API}/user", headers=_headers(token), timeout=TIMEOUT)
    _raise_for_credential(account)
    login = account.json()["login"]

    own = httpx.get(f"{API}/repos/{login}/{name}", headers=_headers(token), timeout=TIMEOUT)
    if own.is_success:
        return own.json()["full_name"]

    granted = httpx.get(
        f"{API}/user/repos",
        params={"per_page": 100, "sort": "updated"},
        headers=_headers(token),
        timeout=TIMEOUT,
    )
    _raise_for_credential(granted)
    for candidate in granted.json():
        if candidate["name"].lower() == name.lower():
            return candidate["full_name"]

    raise GitHubError(
        f"No repository named '{name}' is visible with this token. Enter it as owner/name "
        f"— '{login}/{name}' if it is yours — and check the token grants that repository "
        "read access."
    )


def _raise_for_credential(response: httpx.Response) -> None:
    """GitHub's own refusal, in the sentence shown under the Connect button."""
    if response.is_success:
        return
    if response.status_code == 401:
        raise GitHubError("GitHub rejected this token — it is expired, revoked or mistyped")
    if response.status_code == 403:
        raise GitHubError(f"GitHub refused this token: {_message(response)}")
    raise GitHubError(f"GitHub rejected the token: {response.status_code} {_message(response)}")


def _message(response: httpx.Response) -> str:
    """The API's own wording when it sent one, the raw body when it did not."""
    try:
        return response.json().get("message") or response.text
    except ValueError:
        return response.text


def recent_commits(repo: str, since: datetime, token: str) -> list[dict]:
    """Commits pushed to the default branch since `since`."""
    return _get(
        f"/repos/{repo}/commits",
        {"since": _iso(since), "per_page": MAX_COMMITS},
        token,
    )


def recent_pull_requests(repo: str, since: datetime, token: str) -> list[dict]:
    """Pull requests touched since `since`, open and closed — a stalled PR is a signal."""
    pulls = _get(
        f"/repos/{repo}/pulls",
        {"state": "all", "sort": "updated", "direction": "desc", "per_page": MAX_PULL_REQUESTS},
        token,
    )
    return [pull for pull in pulls if _parse(pull["updated_at"]) >= since]


def recent_issues(repo: str, since: datetime, token: str) -> list[dict]:
    """Issues updated since `since`. GitHub returns PRs here too, so they are dropped."""
    issues = _get(
        f"/repos/{repo}/issues",
        {"state": "all", "sort": "updated", "direction": "desc", "since": _iso(since), "per_page": MAX_ISSUES},
        token,
    )
    return [issue for issue in issues if "pull_request" not in issue]


def execute_action(action: PlannedAction) -> str:
    """Perform one approved action and return a short human-readable result."""
    raise NotImplementedError(f"GitHub action not implemented: {action.type}")


# --- normalization -----------------------------------------------------------


def _commit_evidence(repo: str, commit: dict) -> Evidence:
    message = commit["commit"]["message"]
    author = (commit.get("author") or {}).get("login") or commit["commit"]["author"]["name"]
    return Evidence(
        source="github",
        type="commit",
        title=f"{message.splitlines()[0]} ({commit['sha'][:7]})",
        content=f"Author: {author}\nRepository: {repo}\n\n{message}",
        url=commit["html_url"],
        timestamp=commit["commit"]["author"]["date"],
        metadata={"sha": commit["sha"], "author": author, "repo": repo},
    )


def _pull_request_evidence(pull: dict) -> Evidence:
    state = "merged" if pull.get("merged_at") else pull["state"]
    reviewers = [reviewer["login"] for reviewer in pull.get("requested_reviewers", [])]
    content = "\n".join(
        [
            f"State: {state}",
            f"Author: {pull['user']['login']}",
            f"Opened: {pull['created_at']}",
            f"Last updated: {pull['updated_at']}",
            f"Draft: {pull.get('draft', False)}",
            f"Reviewers requested: {', '.join(reviewers) or 'none'}",
            "",
            pull.get("body") or "",
        ]
    ).strip()
    return Evidence(
        source="github",
        type="pull_request",
        title=f"PR #{pull['number']} {pull['title']} [{state}]",
        content=content,
        url=pull["html_url"],
        timestamp=pull["updated_at"],
        metadata={
            "number": pull["number"],
            "state": state,
            "author": pull["user"]["login"],
            "draft": pull.get("draft", False),
            "created_at": pull["created_at"],
            "merged_at": pull.get("merged_at"),
            "reviewers": reviewers,
        },
    )


def _issue_evidence(issue: dict) -> Evidence:
    assignees = [user["login"] for user in issue.get("assignees", [])]
    labels = [label["name"] for label in issue.get("labels", [])]
    content = "\n".join(
        [
            f"State: {issue['state']}",
            f"Opened by: {issue['user']['login']}",
            f"Assignees: {', '.join(assignees) or 'unassigned'}",
            f"Labels: {', '.join(labels) or 'none'}",
            f"Comments: {issue.get('comments', 0)}",
            "",
            issue.get("body") or "",
        ]
    ).strip()
    return Evidence(
        source="github",
        type="issue",
        title=f"Issue #{issue['number']} {issue['title']} [{issue['state']}]",
        content=content,
        url=issue["html_url"],
        timestamp=issue["updated_at"],
        metadata={
            "number": issue["number"],
            "state": issue["state"],
            "assignees": assignees,
            "labels": labels,
            "comments": issue.get("comments", 0),
        },
    )


def _get(path: str, params: dict, token: str) -> list[dict]:
    response = httpx.get(
        f"{API}{path}",
        params=params,
        headers=_headers(token),
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(timestamp: str) -> datetime:
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
