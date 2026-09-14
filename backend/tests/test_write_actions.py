"""The half of the loop that touches somebody else's workspace.

Reading is useless on its own: a recovery plan is only worth approving if the steps in
it can actually be carried out. These tests pin the two write paths that were missing —
posting the update into Slack, and opening or commenting on a GitHub issue — down to the
request that goes over the wire, because that request is the part nobody can see.
"""

import httpx
import pytest

from app.agents.state import PlannedAction
from app.integrations import calendar, github, gmail, slack
from app.projects import service

PROJECT = "11111111-2222-3333-4444-555555555555"


@pytest.fixture
def sent(monkeypatch):
    """Capture the write instead of making it, and answer as the real API would."""
    calls: list[dict] = []

    def fake_post(url, json=None, headers=None, timeout=None, **_kwargs):
        calls.append({"url": url, "body": json})
        return _Response(_reply_for(url))

    def fake_get(url, params=None, headers=None, timeout=None, **_kwargs):
        return _Response(_reply_for(url, params))

    def fake_patch(url, json=None, headers=None, timeout=None, **_kwargs):
        calls.append({"url": url, "body": json, "method": "PATCH"})
        return _Response(_reply_for(url))

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(httpx, "patch", fake_patch)
    return calls


class _Response:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


def _reply_for(url: str, params: dict | None = None):
    if "chat.postMessage" in url:
        return {"ok": True, "ts": "1726300000.001", "channel": "payments"}
    if "users.conversations" in url:
        return {"ok": True, "channels": [{"id": "C0PAYMENTS", "name": "payments"}]}
    if "/comments" in url:
        return {"html_url": "https://github.com/acme/api/issues/124#issuecomment-1"}
    if "/assignees" in url:
        return {
            "number": 124,
            "html_url": "https://github.com/acme/api/issues/124",
            "assignees": [{"login": "dana"}],
        }
    if "/issues/" in url:  # a single issue — the close PATCH
        return {"number": 124, "html_url": "https://github.com/acme/api/issues/124"}
    if "/issues" in url:
        return {"number": 321, "html_url": "https://github.com/acme/api/issues/321"}
    return {"ok": True}


@pytest.fixture
def connected(monkeypatch):
    """Both apps connected for this project, as a real workspace would be."""
    credentials = {
        "slack": {"token": "xoxb-test", "channel_ids": ""},
        "github": {"token": "ghp-test", "repo": "acme/api"},
    }
    monkeypatch.setattr(
        service, "get_integration_credential", lambda project_id, provider: credentials.get(provider)
    )


def action(integration: str, type_: str, target: str, value: str) -> PlannedAction:
    return PlannedAction(
        project_id=PROJECT,
        integration=integration,
        type=type_,
        description="a step of the recovery plan",
        target=target,
        params={"value": value},
    )


# --- Slack -------------------------------------------------------------------


def test_slack_posts_the_message_and_says_where_it_landed(sent, connected):
    result = slack.execute_action(
        action("slack", "post_message", "#payments", "PAY-124 is blocked on the sandbox key.")
    )

    post = [call for call in sent if "chat.postMessage" in call["url"]][0]
    assert post["body"]["channel"] == "C0PAYMENTS"
    assert post["body"]["text"] == "PAY-124 is blocked on the sandbox key."
    assert "#payments" in result
    assert "slack.com/archives/C0PAYMENTS" in result


def test_slack_takes_a_channel_id_without_looking_it_up(sent, connected):
    slack.execute_action(action("slack", "post_message", "C0PAYMENTS", "shipped"))

    assert not [call for call in sent if "users.conversations" in call["url"]]


def test_slack_refuses_a_channel_the_bot_cannot_see(sent, connected):
    """Better a failed action with the reason than a message posted somewhere else."""
    with pytest.raises(slack.SlackError, match="no channel named #legal"):
        slack.execute_action(action("slack", "post_message", "#legal", "hello"))


def test_slack_will_not_post_an_empty_message(sent, connected):
    with pytest.raises(ValueError, match="params.value"):
        slack.execute_action(action("slack", "post_message", "#payments", ""))


def test_slack_refuses_to_write_for_a_project_that_never_connected_it(monkeypatch):
    monkeypatch.setattr(service, "get_integration_credential", lambda project_id, provider: None)

    with pytest.raises(RuntimeError, match="not connected"):
        slack.execute_action(action("slack", "post_message", "#payments", "hello"))


# --- GitHub ------------------------------------------------------------------


def test_github_opens_an_issue_in_the_connected_repository(sent, connected):
    result = github.execute_action(
        action("github", "create_issue", "Payment sandbox key is missing", "Blocks PAY-124.")
    )

    post = [call for call in sent if call["url"].endswith("/issues")][0]
    assert post["url"] == "https://api.github.com/repos/acme/api/issues"
    assert post["body"] == {
        "title": "Payment sandbox key is missing",
        "body": "Blocks PAY-124.",
    }
    assert "acme/api#321" in result


def test_github_comments_on_an_existing_issue(sent, connected):
    result = github.execute_action(
        action("github", "comment_issue", "#124", "Still blocked as of today.")
    )

    post = [call for call in sent if "/comments" in call["url"]][0]
    assert post["url"] == "https://api.github.com/repos/acme/api/issues/124/comments"
    assert post["body"] == {"body": "Still blocked as of today."}
    assert "acme/api#124" in result


def test_github_refuses_an_issue_number_that_is_not_a_number(sent, connected):
    with pytest.raises(ValueError, match="issue number"):
        github.execute_action(action("github", "comment_issue", "PAY-124", "a comment"))


def test_github_refuses_to_write_for_a_project_that_never_connected_it(monkeypatch):
    monkeypatch.setattr(service, "get_integration_credential", lambda project_id, provider: None)

    with pytest.raises(RuntimeError, match="not connected"):
        github.execute_action(action("github", "create_issue", "a title", "a body"))


# --- the shape the executor relies on ----------------------------------------


@pytest.mark.parametrize(
    "integration,module", [("slack", slack), ("github", github)]
)
def test_an_unknown_action_type_is_refused_by_name(integration, module, connected):
    with pytest.raises(NotImplementedError, match="delete_everything"):
        module.execute_action(action(integration, "delete_everything", "x", "y"))


# --- GitHub: delegate and close ----------------------------------------------


def test_github_assigns_an_issue_to_a_person(sent, connected):
    result = github.execute_action(action("github", "assign_issue", "124", "dana"))

    post = [call for call in sent if "/assignees" in call["url"]][0]
    assert post["body"] == {"assignees": ["dana"]}
    assert "dana" in result


def test_github_says_so_when_nobody_could_be_assigned(sent, connected, monkeypatch):
    """GitHub answers 200 and silently assigns nobody for a username it will not take."""
    monkeypatch.setattr(
        github, "_post", lambda path, payload, token: {"number": 124, "html_url": "u", "assignees": []}
    )

    with pytest.raises(github.GitHubError, match="cannot be assigned"):
        github.execute_action(action("github", "assign_issue", "124", "ghost"))


def test_github_closes_an_issue_with_its_reason_first(sent, connected):
    """The comment has to land before the close, or it explains a decision already made."""
    result = github.execute_action(
        action("github", "close_issue", "124", "Superseded by the new sandbox key.")
    )

    urls = [call["url"] for call in sent]
    assert urls.index("https://api.github.com/repos/acme/api/issues/124/comments") < urls.index(
        "https://api.github.com/repos/acme/api/issues/124"
    )
    patch = [call for call in sent if call.get("method") == "PATCH"][0]
    assert patch["body"] == {"state": "closed"}
    assert "Closed acme/api#124" in result


def test_github_closes_without_a_comment_when_none_was_given(sent, connected):
    github.execute_action(action("github", "close_issue", "124", ""))

    assert not [call for call in sent if "/comments" in call["url"]]


# --- the catalog is the contract ---------------------------------------------


@pytest.fixture
def all_apps_connected(monkeypatch):
    """Every write target reachable, so a dispatch test reaches the type check instead
    of stopping at a missing credential."""
    credentials = {
        "slack": {"token": "xoxb", "channel_ids": ""},
        "github": {"token": "ghp", "repo": "acme/api"},
        "linear": {"token": "lin"},
    }
    monkeypatch.setattr(
        service, "get_integration_credential", lambda project_id, provider: credentials.get(provider)
    )
    for module in (gmail, calendar):
        monkeypatch.setattr(module.google_auth, "headers", lambda project_id: {"Authorization": "t"})
        monkeypatch.setattr(module.google_auth, "is_connected", lambda project_id: True)


def test_every_catalogued_action_type_is_actually_dispatchable(sent, all_apps_connected):
    """A type in the catalog that no integration handles would be offered in the UI and
    proposed by the planner, then fail only when somebody approved it. Catch it here.

    Each type is called with an empty target and value, which every handler rejects on
    its arguments — so reaching *any* error other than NotImplementedError proves the
    type was recognised and dispatched.
    """
    from app.agents import executor

    for entry in executor.ACTION_TYPES:
        module = executor.INTEGRATIONS[entry.integration]
        try:
            module.execute_action(action(entry.integration, entry.type, "", ""))
        except NotImplementedError as error:
            raise AssertionError(
                f"{entry.integration}/{entry.type} is in ACTION_TYPES but execute_action "
                f"does not handle it: {error}"
            ) from None
        except (ValueError, RuntimeError, KeyError, TypeError, AttributeError):
            pass  # recognised, then refused on its arguments — exactly right


def test_a_type_missing_from_an_integration_is_caught(sent, all_apps_connected):
    """The guard above only works if a missing type really does raise NotImplementedError."""
    with pytest.raises(NotImplementedError):
        slack.execute_action(action("slack", "not_a_real_type", "#payments", "hi"))


def test_the_recovery_prompt_offers_exactly_what_can_be_run():
    from app.agents import executor, risk

    for entry in executor.ACTION_TYPES:
        assert f"{entry.integration} / {entry.type}" in risk.SYSTEM
