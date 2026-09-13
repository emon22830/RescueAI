"""Slack. Reads project evidence; write actions live in execute_action()."""

import logging
import re
from datetime import UTC, datetime, timedelta

import httpx

from app.agents.state import Evidence, PlannedAction
from app.config import settings

logger = logging.getLogger(__name__)

API = "https://slack.com/api"
TIMEOUT = 20.0
LOOKBACK_DAYS = 30
MESSAGES_PER_CHANNEL = 200
MAX_MESSAGES = 40


class SlackError(RuntimeError):
    """Slack answers 200 with ok=false — the reason is in the body, not the status."""


def collect_evidence(project_name: str) -> list[Evidence]:
    """The most recent messages about this project, newest first.

    A message counts when it names the project, or when it sits in a channel
    named after the project — a whole #saas-product-launch channel is about it.
    """
    if not settings.slack_bot_token:
        logger.warning("Slack skipped: SLACK_BOT_TOKEN is empty in backend/.env")
        return []

    authors = list_user_names()
    oldest = (datetime.now(UTC) - timedelta(days=LOOKBACK_DAYS)).timestamp()

    matches: list[tuple[dict, dict]] = []
    for channel in list_channels():
        channel_is_the_project = mentions_project(channel["name"], project_name)
        for message in fetch_channel_messages(channel["id"], oldest):
            text = message.get("text", "").strip()
            if not text:
                continue
            if channel_is_the_project or mentions_project(text, project_name):
                matches.append((channel, message))

    matches.sort(key=lambda pair: float(pair[1]["ts"]), reverse=True)
    return [_to_evidence(channel, message, authors) for channel, message in matches[:MAX_MESSAGES]]


def list_channels() -> list[dict]:
    """Channels the bot can read: the ones it was invited to, or SLACK_CHANNEL_IDS."""
    scoped = [channel_id.strip() for channel_id in settings.slack_channel_ids.split(",") if channel_id.strip()]
    if scoped:
        return [_call("conversations.info", {"channel": channel_id})["channel"] for channel_id in scoped]

    body = _call(
        "users.conversations",
        {"types": "public_channel,private_channel", "exclude_archived": "true", "limit": 200},
    )
    return body["channels"]


def fetch_channel_messages(channel_id: str, oldest: float) -> list[dict]:
    """Real human messages in one channel since `oldest`, joins and file notices dropped."""
    body = _call(
        "conversations.history",
        {"channel": channel_id, "oldest": f"{oldest:.6f}", "limit": MESSAGES_PER_CHANNEL},
    )
    return [
        message
        for message in body["messages"]
        if message.get("type") == "message" and not message.get("subtype")
    ]


def list_user_names() -> dict[str, str]:
    """User id → display name, so a quote says who said it.

    Names are a nicety: if the token lacks users:read the evidence is still
    worth collecting, so this degrades to ids rather than failing the run.
    """
    try:
        members = _call("users.list", {"limit": 500})["members"]
    except SlackError as error:
        logger.warning("Slack user names unavailable, falling back to ids: %s", error)
        return {}
    return {
        member["id"]: member.get("profile", {}).get("real_name") or member.get("name", "")
        for member in members
    }


def mentions_project(text: str, project_name: str) -> bool:
    """True when the text names the project or at least half of its distinctive words."""
    haystack = text.lower()
    if project_name.lower() in haystack:
        return True

    words = [word for word in re.findall(r"[a-z0-9]+", project_name.lower()) if len(word) > 2]
    if not words:
        return False
    hits = sum(1 for word in words if word in haystack)
    return hits >= (len(words) + 1) // 2


def permalink(channel_id: str, ts: str) -> str:
    """Slack's archive URL redirects to the right workspace, so it needs no team domain."""
    return f"https://slack.com/archives/{channel_id}/p{ts.replace('.', '')}"


def execute_action(action: PlannedAction) -> str:
    """Perform one approved action and return a short human-readable result."""
    raise NotImplementedError(f"Slack action not implemented: {action.type}")


def _to_evidence(channel: dict, message: dict, authors: dict[str, str]) -> Evidence:
    user_id = message.get("user", "")
    author = authors.get(user_id) or user_id or "unknown"
    return Evidence(
        source="slack",
        type="message",
        title=f"#{channel['name']} · {author}",
        content=message["text"],
        url=permalink(channel["id"], message["ts"]),
        timestamp=datetime.fromtimestamp(float(message["ts"]), tz=UTC),
        metadata={
            "channel": channel["name"],
            "channel_id": channel["id"],
            "author": author,
            "reply_count": message.get("reply_count", 0),
            "reactions": [reaction["name"] for reaction in message.get("reactions", [])],
        },
    )


def _call(method: str, params: dict) -> dict:
    response = httpx.get(
        f"{API}/{method}",
        params=params,
        headers={"Authorization": f"Bearer {settings.slack_bot_token}"},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    body = response.json()
    if not body.get("ok"):
        raise SlackError(f"Slack {method} failed: {body.get('error', 'unknown_error')}")
    return body
