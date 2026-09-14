"""Trello. Reads project evidence; write actions live in execute_action().

Trello authenticates with a pair: an API key that identifies the application and a
token that authorizes it, both sent as query parameters rather than a header. The key
is not the secret half — Trello's own docs put it in client-side code — so it is stored
as metadata alongside `repo` and `site`, while the token is encrypted like every other
credential in this system.
"""

import logging

import httpx

from app.agents.state import Evidence, PlannedAction

logger = logging.getLogger(__name__)

API = "https://api.trello.com/1"
TIMEOUT = 30.0
MAX_CARDS = 40

CARD_FIELDS = "name,desc,url,due,dueComplete,closed,dateLastActivity,idList,idBoard,idMembers,labels"


class TrelloError(RuntimeError):
    """Trello refused the request — usually a bad key/token pair, or a missing board."""


def collect_evidence(project_id: str, project_name: str) -> list[Evidence]:
    """Cards that mention the project, newest activity first."""
    from app.projects import service

    credential = service.get_integration_credential(project_id, "trello")
    if credential is None:
        logger.warning("Trello skipped: project %s has not connected Trello", project_id)
        return []

    key = credential.get("key", "")
    token = credential["token"]
    if not key:
        logger.warning("Trello skipped: project %s stored no API key", project_id)
        return []

    cards = search_cards(project_name, key, token)
    boards = _board_names(cards, key, token)
    return [_to_evidence(card, boards) for card in cards[:MAX_CARDS]]


def verify_token(token: str, key: str = "") -> dict:
    """Confirm the key and token work together before either is stored."""
    if not key:
        raise TrelloError("Trello needs the API key that goes with this token")

    me = _get("/members/me", {"fields": "username,fullName"}, key, token)
    return {"key": key, "account": me.get("fullName") or me.get("username", "")}


def search_cards(project_name: str, key: str, token: str) -> list[dict]:
    body = _get(
        "/search",
        {
            "query": project_name,
            "modelTypes": "cards",
            "card_fields": CARD_FIELDS,
            "cards_limit": MAX_CARDS,
            "partial": "true",
        },
        key,
        token,
    )
    return body.get("cards", [])


# --- write actions -----------------------------------------------------------


def execute_action(action: PlannedAction) -> str:
    """Perform one approved action and return a short human-readable result."""
    from app.projects import service

    credential = service.get_integration_credential(action.project_id, "trello")
    if credential is None:
        raise RuntimeError("Trello is not connected for this project")

    key, token = credential.get("key", ""), credential["token"]
    if not key:
        raise RuntimeError("This project connected Trello without its API key")

    body = action.params.get("value", "")

    if action.type == "create_card":
        if not action.target:
            raise ValueError("Trello create_card needs a target (the card name)")
        list_id = action.params.get("list", "")
        if not list_id:
            raise ValueError(
                "Trello create_card needs params.list — the id of the list to add it to"
            )
        return create_card(action.target, body or action.description, list_id, key, token,
                           due_date=action.params.get("due_date", ""))

    if not action.target:
        raise ValueError(f"Trello {action.type} needs a target (the card id)")
    card_id = action.target.strip()

    if action.type == "comment_card":
        return comment_on_card(card_id, _required(body, "comment_card"), key, token)
    if action.type == "update_due_date":
        return update_due_date(card_id, _required(body, "update_due_date"), key, token)
    if action.type == "close_card":
        return close_card(card_id, key, token)

    raise NotImplementedError(f"Trello action not implemented: {action.type}")


def create_card(
    name: str, description: str, list_id: str, key: str, token: str, due_date: str = ""
) -> str:
    params = {"idList": list_id, "name": name, "desc": description}
    if due_date:
        params["due"] = due_date

    card = _post("/cards", params, key, token)
    return f"Created \"{card.get('name', name)}\" — {card.get('url', '')}".strip()


def comment_on_card(card_id: str, text: str, key: str, token: str) -> str:
    _post(f"/cards/{card_id}/actions/comments", {"text": text}, key, token)
    return f"Commented on Trello card {card_id}"


def update_due_date(card_id: str, due_date: str, key: str, token: str) -> str:
    card = _put(f"/cards/{card_id}", {"due": due_date}, key, token)
    return f"Due {due_date} — {card.get('url', '')}".strip()


def close_card(card_id: str, key: str, token: str) -> str:
    """Archive the card and mark its due date done — on a board, "closed" is both."""
    card = _put(f"/cards/{card_id}", {"closed": "true", "dueComplete": "true"}, key, token)
    return f"Archived \"{card.get('name', card_id)}\" — {card.get('url', '')}".strip()


# --- normalization -----------------------------------------------------------


def _board_names(cards: list[dict], key: str, token: str) -> dict[str, str]:
    """Board id → name, one request per distinct board rather than one per card.

    A card without its board is just a sentence; which board it is on is half of what
    makes it evidence. A board we cannot read is not worth failing the collection over.
    """
    names: dict[str, str] = {}
    for board_id in {card.get("idBoard") for card in cards if card.get("idBoard")}:
        try:
            names[board_id] = _get(f"/boards/{board_id}", {"fields": "name"}, key, token)["name"]
        except TrelloError as error:
            logger.warning("Trello board %s unreadable: %s", board_id, error)
    return names


def _to_evidence(card: dict, boards: dict[str, str]) -> Evidence:
    board = boards.get(card.get("idBoard", ""), "unknown board")
    due = card.get("due") or "no due date"
    state = "archived" if card.get("closed") else "open"
    labels = [label.get("name") for label in card.get("labels", []) if label.get("name")]

    return Evidence(
        source="trello",
        type="card",
        title=card.get("name", "Untitled card"),
        content=(
            f"Board: {board}\nStatus: {state}\nDue: {due}"
            f"{' (done)' if card.get('dueComplete') else ''}\n"
            f"{'Labels: ' + ', '.join(labels) if labels else ''}\n\n{card.get('desc', '')}"
        ).strip(),
        url=card.get("url"),
        timestamp=card.get("dateLastActivity"),
        metadata={
            "card_id": card.get("id"),
            "board": board,
            "closed": bool(card.get("closed")),
            "due_date": card.get("due"),
            "due_complete": bool(card.get("dueComplete")),
            "labels": labels,
        },
    )


def _required(value: str, action_type: str) -> str:
    if not value:
        raise ValueError(f"Trello {action_type} needs params.value")
    return value


# --- http --------------------------------------------------------------------
#
# The credential rides in the query string, so it is added here once and never at a
# call site — which is also what keeps it out of a logged URL built by hand.


def _auth(params: dict, key: str, token: str) -> dict:
    return {**params, "key": key, "token": token}


def _get(path: str, params: dict, key: str, token: str):
    return _read(httpx.get(f"{API}{path}", params=_auth(params, key, token), timeout=TIMEOUT), path)


def _post(path: str, params: dict, key: str, token: str) -> dict:
    return _read(httpx.post(f"{API}{path}", params=_auth(params, key, token), timeout=TIMEOUT), path)


def _put(path: str, params: dict, key: str, token: str) -> dict:
    return _read(httpx.put(f"{API}{path}", params=_auth(params, key, token), timeout=TIMEOUT), path)


def _read(response, path: str):
    if response.status_code >= 400:
        raise TrelloError(f"Trello {path} failed ({response.status_code}): {response.text[:200]}")
    return response.json()
