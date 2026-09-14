"""Slack. Reads project evidence; write actions live in execute_action().

Each project connects its own bot token from the frontend (see projects/service.py
connect_integration), so every function here takes the token explicitly rather than
reading one shared value off app.config.settings.
"""

import logging
import re
from datetime import UTC, datetime, timedelta

import httpx

from app.agents.state import Evidence, PlannedAction

logger = logging.getLogger(__name__)

API = "https://slack.com/api"
TIMEOUT = 20.0
LOOKBACK_DAYS = 30
MESSAGES_PER_CHANNEL = 200
MAX_MESSAGES = 40


class SlackError(RuntimeError):
    """Slack answers 200 with ok=false — the reason is in the body, not the status."""


def collect_evidence(project_id: str, project_name: str) -> list[Evidence]:
    """The most recent messages about this project, newest first.

    A message counts when it names the project, or when it sits in a channel
    named after the project — a whole #saas-product-launch channel is about it.
    """
    from app.projects import service

    credential = service.get_integration_credential(project_id, "slack")
    if credential is None:
        logger.warning("Slack skipped: project %s has not connected Slack", project_id)
        return []

    token = credential["token"]
    channel_ids = credential.get("channel_ids", "")

    authors = list_user_names(token)
    oldest = (datetime.now(UTC) - timedelta(days=LOOKBACK_DAYS)).timestamp()

    matches: list[tuple[dict, dict]] = []
    for channel in list_channels(token, channel_ids):
        channel_is_the_project = mentions_project(channel["name"], project_name)
        for message in fetch_channel_messages(channel["id"], oldest, token):
            text = message.get("text", "").strip()
            if not text:
                continue
            if channel_is_the_project or mentions_project(text, project_name):
                matches.append((channel, message))

    matches.sort(key=lambda pair: float(pair[1]["ts"]), reverse=True)
    return [_to_evidence(channel, message, authors) for channel, message in matches[:MAX_MESSAGES]]


def verify_token(token: str, channel_ids: str = "") -> dict:
    """Confirm the token actually works before it is stored. Called by the connect flow."""
    body = _call("auth.test", {}, token)
    return {"team": body.get("team", ""), "bot_user": body.get("user", "")}


def list_channels(token: str, channel_ids: str = "") -> list[dict]:
    """Channels the bot can read: the ones it was invited to, or a chosen subset."""
    scoped = [channel_id.strip() for channel_id in channel_ids.split(",") if channel_id.strip()]
    if scoped:
        return [_call("conversations.info", {"channel": channel_id}, token)["channel"] for channel_id in scoped]

    body = _call(
        "users.conversations",
        {"types": "public_channel,private_channel", "exclude_archived": "true", "limit": 200},
        token,
    )
    return body["channels"]


def fetch_channel_messages(channel_id: str, oldest: float, token: str) -> list[dict]:
    """Real human messages in one channel since `oldest`, joins and file notices dropped."""
    body = _call(
        "conversations.history",
        {"channel": channel_id, "oldest": f"{oldest:.6f}", "limit": MESSAGES_PER_CHANNEL},
        token,
    )
    return [
        message
        for message in body["messages"]
        if message.get("type") == "message" and not message.get("subtype")
    ]


def list_user_names(token: str) -> dict[str, str]:
    """User id → display name, so a quote says who said it.

    Names are a nicety: if the token lacks users:read the evidence is still
    worth collecting, so this degrades to ids rather than failing the run.
    """
    try:
        members = _call("users.list", {"limit": 500}, token)["members"]
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
    """Perform one approved action and return a short human-readable result.

    `target` is the channel the message belongs in — an id (C0123ABCD) or a name
    with or without the leading # — and `params.value` is what to say in it.
    """
    from app.projects import service

    credential = service.get_integration_credential(action.project_id, "slack")
    if credential is None:
        raise RuntimeError("Slack is not connected for this project")
    token = credential["token"]

    if action.type != "post_message":
        raise NotImplementedError(f"Slack action not implemented: {action.type}")

    text = action.params.get("value")
    if not action.target or not text:
        raise ValueError("Slack post_message needs a target (channel) and params.value (the message)")

    return post_message(action.target, text, token)


def post_message(channel: str, text: str, token: str) -> str:
    """Post one message and return where it landed, with a link to it."""
    channel_id = resolve_channel(channel, token)
    body = _post("chat.postMessage", {"channel": channel_id, "text": text}, token)
    ts = body["ts"]
    name = body.get("channel", channel_id)
    return f"Posted to #{name.lstrip('#')} — {permalink(channel_id, ts)}"


def resolve_channel(channel: str, token: str) -> str:
    """A channel id passes straight through; a name is looked up among the channels
    the bot can see, so a plan may say "#payments" the way a person would."""
    wanted = channel.strip().lstrip("#")
    if re.fullmatch(r"[CGD][A-Z0-9]{6,}", wanted):
        return wanted

    for candidate in list_channels(token):
        if candidate["name"].lower() == wanted.lower():
            return candidate["id"]
    raise SlackError(f"Slack has no channel named #{wanted} that this bot can post to")


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


def _post(method: str, payload: dict, token: str) -> dict:
    """Write calls take a JSON body; reads take query params. Same ok=false contract."""
    response = httpx.post(
        f"{API}/{method}",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    body = response.json()
    if not body.get("ok"):
        raise SlackError(f"Slack {method} failed: {body.get('error', 'unknown_error')}")
    return body


def _call(method: str, params: dict, token: str) -> dict:
    response = httpx.get(
        f"{API}/{method}",
        params=params,
        headers={"Authorization": f"Bearer {token}"},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    body = response.json()
    if not body.get("ok"):
        raise SlackError(f"Slack {method} failed: {body.get('error', 'unknown_error')}")
    return body
