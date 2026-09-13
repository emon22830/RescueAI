"""GitHub. Reads project evidence; write actions live in execute_action()."""

import logging
from datetime import UTC, datetime, timedelta

import httpx

from app.agents.state import Evidence, PlannedAction
from app.config import settings

logger = logging.getLogger(__name__)

API = "https://api.github.com"
TIMEOUT = 20.0
LOOKBACK_DAYS = 30
MAX_COMMITS = 30
MAX_PULL_REQUESTS = 20
MAX_ISSUES = 20


def collect_evidence(project_name: str) -> list[Evidence]:
    """Recent activity in the project's repository: commits, pull requests, issues.

    The repository named by GITHUB_REPO *is* the project, so activity is bounded
    by a recent window rather than filtered by name.
    """
    if not (settings.github_token and settings.github_repo):
        logger.warning("GitHub skipped: GITHUB_TOKEN or GITHUB_REPO is empty in backend/.env")
        return []

    repo = settings.github_repo
    since = datetime.now(UTC) - timedelta(days=LOOKBACK_DAYS)

    evidence = [_commit_evidence(repo, commit) for commit in recent_commits(repo, since)]
    evidence += [_pull_request_evidence(pull) for pull in recent_pull_requests(repo, since)]
    evidence += [_issue_evidence(issue) for issue in recent_issues(repo, since)]
    return evidence


def recent_commits(repo: str, since: datetime) -> list[dict]:
    """Commits pushed to the default branch since `since`."""
    return _get(
        f"/repos/{repo}/commits",
        {"since": _iso(since), "per_page": MAX_COMMITS},
    )


def recent_pull_requests(repo: str, since: datetime) -> list[dict]:
    """Pull requests touched since `since`, open and closed — a stalled PR is a signal."""
    pulls = _get(
        f"/repos/{repo}/pulls",
        {"state": "all", "sort": "updated", "direction": "desc", "per_page": MAX_PULL_REQUESTS},
    )
    return [pull for pull in pulls if _parse(pull["updated_at"]) >= since]


def recent_issues(repo: str, since: datetime) -> list[dict]:
    """Issues updated since `since`. GitHub returns PRs here too, so they are dropped."""
    issues = _get(
        f"/repos/{repo}/issues",
        {"state": "all", "sort": "updated", "direction": "desc", "since": _iso(since), "per_page": MAX_ISSUES},
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


def _get(path: str, params: dict) -> list[dict]:
    response = httpx.get(
        f"{API}{path}",
        params=params,
        headers={
            "Authorization": f"Bearer {settings.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def _iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(timestamp: str) -> datetime:
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
