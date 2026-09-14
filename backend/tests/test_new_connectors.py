"""Jira, Notion, Asana and Trello — the four connectors added after the first six.

The unconnected contract is covered for all ten in test_integrations.py. This file
covers what is particular to these four: the request each one actually sends, and the
three shapes that are easy to get wrong and impossible to notice until a live token is
in play — Jira's Atlassian Document Format, Jira's replacement search endpoint, and
Trello's credential riding in the query string.
"""

import httpx
import pytest

from app.agents.state import PlannedAction
from app.integrations import asana, jira, notion, trello
from app.projects import service

PROJECT = "11111111-2222-3333-4444-555555555555"
NAME = "SaaS Product Launch"


@pytest.fixture
def wire(monkeypatch):
    """Record every request instead of making it, and answer as each API would."""
    calls: list[dict] = []

    def record(method):
        def call(url, params=None, json=None, headers=None, timeout=None, **_kwargs):
            calls.append(
                {"method": method, "url": url, "params": params or {}, "body": json,
                 "headers": headers or {}}
            )
            return _Response(_reply_for(url, json))

        return call

    for method in ("get", "post", "put", "delete"):
        monkeypatch.setattr(httpx, method, record(method.upper()))
    return calls


class _Response:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200
        self.content = b"{}"
        self.text = "{}"

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


def _reply_for(url: str, body: dict | None):
    # --- Jira ---
    if "/search/jql" in url:
        return {
            "issues": [
                {
                    "key": "PAY-124",
                    "fields": {
                        "summary": "Payment sandbox key missing",
                        "status": {"name": "In Progress", "statusCategory": {"key": "indeterminate"}},
                        "assignee": {"displayName": "Dana"},
                        "duedate": "2026-09-20",
                        "updated": "2026-09-10T09:00:00.000+0000",
                        "issuetype": {"name": "Bug"},
                        "project": {"key": "PAY"},
                        "description": {
                            "type": "doc", "version": 1,
                            "content": [
                                {"type": "paragraph",
                                 "content": [{"type": "text", "text": "Vendor has not issued it."}]}
                            ],
                        },
                    },
                }
            ],
            "nextPageToken": None,
        }
    if "/myself" in url:
        return {"displayName": "Dana", "accountId": "acc-1"}
    if "/transitions" in url:
        return {"transitions": [
            {"id": "31", "name": "Done", "to": {"statusCategory": {"key": "done"}}},
            {"id": "11", "name": "In Progress", "to": {"statusCategory": {"key": "indeterminate"}}},
        ]}
    if "/user/search" in url:
        return [{"accountId": "acc-2", "displayName": "Dana", "emailAddress": "dana@acme.test"}]
    if "/rest/api/3/issue" in url:
        return {"key": "PAY-200"}

    # --- Notion ---
    if "notion.com/v1/search" in url:
        return {"results": [{
            "id": "page-1",
            "url": "https://notion.so/page-1",
            "last_edited_time": "2026-09-09T10:00:00.000Z",
            "properties": {"Name": {"type": "title", "title": [{"plain_text": "Spec v3"}]}},
        }]}
    if "/blocks/" in url:
        return {"results": [
            {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Scope changed."}]}},
            {"type": "to_do", "to_do": {"checked": False,
                                        "rich_text": [{"plain_text": "Confirm with vendor"}]}},
        ]}
    if "notion.com/v1/users/me" in url:
        return {"name": "RescueAI", "bot": {"workspace_name": "Acme"}}
    if "notion.com/v1/comments" in url:
        return {"id": "comment-1"}
    if "notion.com/v1/pages" in url:
        return {"id": "page-2", "url": "https://notion.so/page-2"}

    # --- Asana ---
    if "/users/me" in url:
        return {"data": {"name": "Dana", "workspaces": [{"gid": "ws1", "name": "Acme"}]}}
    if "/typeahead" in url:
        return {"data": [{"gid": "proj1", "name": NAME}]}
    if "/tasks" in url and "/stories" not in url:
        return {"data": [{
            "gid": "task1", "name": "Wire the sandbox key", "notes": "Blocked on vendor",
            "completed": False, "due_on": "2026-09-20", "modified_at": "2026-09-10T09:00:00.000Z",
            "permalink_url": "https://app.asana.com/0/proj1/task1",
            "assignee": {"name": "Dana"},
        }]}
    if "/stories" in url:
        return {"data": {"gid": "story1"}}

    # --- Trello ---
    if "api.trello.com/1/search" in url:
        return {"cards": [{
            "id": "card1", "name": "Sandbox key", "desc": "Waiting on vendor",
            "url": "https://trello.com/c/card1", "due": "2026-09-20", "dueComplete": False,
            "closed": False, "dateLastActivity": "2026-09-10T09:00:00.000Z",
            "idBoard": "board1", "labels": [{"name": "blocked"}],
        }]}
    if "/boards/" in url:
        return {"name": "Launch board"}
    if "/members/me" in url:
        return {"fullName": "Dana", "username": "dana"}
    if "/cards" in url:
        return {"id": "card2", "name": "New card", "url": "https://trello.com/c/card2"}

    return {}


@pytest.fixture
def connected(monkeypatch):
    credentials = {
        "jira": {"token": "tok", "site": "https://acme.atlassian.net", "email": "me@acme.test"},
        "notion": {"token": "ntn_tok"},
        "asana": {"token": "asana_tok", "workspace": "ws1"},
        "trello": {"token": "trello_tok", "key": "trello_key"},
    }
    monkeypatch.setattr(
        service, "get_integration_credential", lambda project_id, provider: credentials.get(provider)
    )


def action(integration: str, type_: str, target: str, value: str, **params) -> PlannedAction:
    return PlannedAction(
        project_id=PROJECT, integration=integration, type=type_, description="a step",
        target=target, params={"value": value, **params},
    )


# --- Jira --------------------------------------------------------------------


def test_jira_uses_the_endpoint_that_replaced_the_removed_one(wire, connected):
    """/rest/api/3/search was removed from Jira Cloud in 2025. Using it collects nothing."""
    jira.collect_evidence(PROJECT, NAME)

    search = [call for call in wire if "search" in call["url"]][0]
    assert search["url"].endswith("/rest/api/3/search/jql")
    assert search["method"] == "POST"


def test_jira_asks_for_fields_because_the_endpoint_returns_none_by_default(wire, connected):
    """Without `fields` this endpoint hands back an id and a key — and no evidence."""
    jira.collect_evidence(PROJECT, NAME)

    search = [call for call in wire if "search" in call["url"]][0]
    assert "summary" in search["body"]["fields"]
    assert "status" in search["body"]["fields"]


def test_jira_normalizes_an_issue_into_checkable_evidence(wire, connected):
    [item] = jira.collect_evidence(PROJECT, NAME)

    assert item.source == "jira"
    assert item.title == "PAY-124: Payment sandbox key missing"
    assert item.url == "https://acme.atlassian.net/browse/PAY-124"
    assert item.timestamp is not None
    assert "In Progress" in item.content
    # The description is Atlassian Document Format — a tree, not a string.
    assert "Vendor has not issued it." in item.content


def test_jira_sends_a_comment_as_a_document_not_a_string(wire, connected):
    """A plain string in `body` is rejected by the v3 API."""
    jira.execute_action(action("jira", "comment_issue", "PAY-124", "Still blocked."))

    comment = [call for call in wire if call["url"].endswith("/comment")][0]
    assert comment["body"]["body"]["type"] == "doc"
    assert comment["body"]["body"]["content"][0]["content"][0]["text"] == "Still blocked."


def test_jira_closes_through_a_transition_not_a_status_field(wire, connected):
    """Jira has no settable status; closing means finding the transition into Done."""
    result = jira.execute_action(action("jira", "close_issue", "PAY-124", ""))

    posted = [call for call in wire if call["url"].endswith("/transitions")
              and call["method"] == "POST"][0]
    assert posted["body"] == {"transition": {"id": "31"}}
    assert "Done" in result


def test_jira_names_the_available_transitions_when_the_one_asked_for_is_missing(wire, connected):
    with pytest.raises(jira.JiraError, match="In Progress"):
        jira.execute_action(action("jira", "close_issue", "PAY-124", "Shipped"))


@pytest.mark.parametrize(
    "pasted", ["acme.atlassian.net", "https://acme.atlassian.net", "https://acme.atlassian.net/jira/software/projects/PAY"]
)
def test_a_jira_site_is_recognised_however_it_was_pasted(pasted):
    assert jira.base_url(pasted) == "https://acme.atlassian.net"


def test_jql_escapes_a_project_name_containing_a_quote(wire, connected):
    """An unescaped quote closes the JQL string literal and the query is rejected."""
    jira.collect_evidence(PROJECT, 'The "Big" Launch')

    search = [call for call in wire if "search" in call["url"]][0]
    assert '\\"Big\\"' in search["body"]["jql"]


def test_jira_create_issue_says_what_is_missing_without_a_project_key(wire, connected):
    with pytest.raises(ValueError, match="params.project"):
        jira.execute_action(action("jira", "create_issue", "Fix the key", "body"))


# --- Notion ------------------------------------------------------------------


def test_notion_always_sends_its_version_header(wire, connected):
    """Notion refuses any request without it."""
    notion.collect_evidence(PROJECT, NAME)

    assert all(call["headers"].get("Notion-Version") for call in wire)


def test_notion_reads_the_page_body_not_just_its_title(wire, connected):
    """Search returns properties and a URL; the prose is in the blocks."""
    [item] = notion.collect_evidence(PROJECT, NAME)

    assert item.title == "Spec v3"
    assert "Scope changed." in item.content
    assert "[ ] Confirm with vendor" in item.content
    assert item.url == "https://notion.so/page-1"


def test_notion_still_lists_a_page_whose_body_will_not_load(wire, connected, monkeypatch):
    """A title and a link are worth keeping even when the blocks are unreadable."""
    monkeypatch.setattr(
        notion, "_get", lambda *a, **k: (_ for _ in ()).throw(notion.NotionError("no access"))
    )

    [item] = notion.collect_evidence(PROJECT, NAME)
    assert item.title == "Spec v3"


def test_notion_create_page_says_what_is_missing_without_a_parent(wire, connected):
    with pytest.raises(ValueError, match="params.parent"):
        notion.execute_action(action("notion", "create_page", "New spec", "text"))


# --- Asana -------------------------------------------------------------------


def test_asana_finds_the_project_then_reads_its_tasks(wire, connected):
    """Asana's own task search is a paid feature, so this goes project-first."""
    [item] = asana.collect_evidence(PROJECT, NAME)

    assert "/typeahead" in wire[0]["url"]
    assert item.source == "asana"
    assert item.title == "Wire the sandbox key"
    assert item.url == "https://app.asana.com/0/proj1/task1"
    assert "Dana" in item.content


def test_asana_wraps_what_it_sends_in_a_data_envelope(wire, connected):
    asana.execute_action(action("asana", "comment_task", "task1", "Still blocked."))

    story = [call for call in wire if "/stories" in call["url"]][0]
    assert story["body"] == {"data": {"text": "Still blocked."}}


def test_asana_discovers_the_workspace_when_the_token_is_verified(wire):
    """One fewer thing to paste, and one fewer thing to paste wrong."""
    assert asana.verify_token("asana_tok") == {
        "workspace": "ws1", "workspace_name": "Acme", "account": "Dana"
    }


# --- Trello ------------------------------------------------------------------


def test_trello_sends_its_credential_in_the_query_string(wire, connected):
    """Trello takes key and token as parameters, not as a header."""
    trello.collect_evidence(PROJECT, NAME)

    search = [call for call in wire if "/search" in call["url"]][0]
    assert search["params"]["key"] == "trello_key"
    assert search["params"]["token"] == "trello_tok"
    assert search["params"]["modelTypes"] == "cards"


def test_trello_names_the_board_a_card_is_on(wire, connected):
    """A card without its board is a sentence; which board it is on is the context."""
    [item] = trello.collect_evidence(PROJECT, NAME)

    assert "Board: Launch board" in item.content
    assert item.url == "https://trello.com/c/card1"
    assert item.metadata["labels"] == ["blocked"]


def test_trello_reads_each_board_once_not_once_per_card(wire, connected, monkeypatch):
    cards = [{"id": f"c{n}", "name": f"Card {n}", "idBoard": "board1", "url": "u",
              "labels": [], "dateLastActivity": "2026-09-10T09:00:00.000Z"} for n in range(5)]
    monkeypatch.setattr(trello, "search_cards", lambda *a, **k: cards)

    trello.collect_evidence(PROJECT, NAME)

    assert len([call for call in wire if "/boards/" in call["url"]]) == 1


def test_trello_create_card_says_what_is_missing_without_a_list(wire, connected):
    with pytest.raises(ValueError, match="params.list"):
        trello.execute_action(action("trello", "create_card", "New card", "body"))


def test_trello_refuses_a_token_with_no_key(wire):
    with pytest.raises(trello.TrelloError, match="API key"):
        trello.verify_token("trello_tok")
