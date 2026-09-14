"""Taking an action from the dashboard, without waiting for the agent to propose one.

A project manager who can see the problem should not have to run an analysis to answer
it. These actions are authored and approved in the same gesture — but they are the same
row, in the same states, through the same guard, so the audit trail does not care which
of the two wrote them.
"""

import pytest

from app.agents import executor
from app.projects import service

CHANNEL = "#payments"


@pytest.fixture
def project_id(client, db) -> str:
    return client.post("/projects", json={"name": "SaaS Product Launch", "goal": "Ship"}).json()["id"]


@pytest.fixture
def slack_connected(client, project_id, monkeypatch):
    """Slack connected the way the connect flow leaves it, token verified and stored."""
    monkeypatch.setattr(
        service.slack, "verify_token", lambda token, **extra: {"team": "Acme", "bot_user": "rescue"}
    )
    client.post(
        f"/projects/{project_id}/integrations/slack/connect", json={"token": "xoxb-test"}
    )


@pytest.fixture
def executes(monkeypatch):
    """Capture what reached the integration instead of calling out."""
    performed: list = []

    def fake_execute(action, status):
        performed.append({"action": action, "status": status})
        return "Posted to #payments — https://slack.com/archives/C0/p1"

    monkeypatch.setattr(service.executor, "execute", fake_execute)
    return performed


def post_message(client, project_id, **overrides) -> dict:
    body = {
        "integration": "slack",
        "type": "post_message",
        "target": CHANNEL,
        "value": "PAY-124 is blocked on the vendor sandbox key.",
        **overrides,
    }
    return client.post(f"/projects/{project_id}/actions", json=body).json()


# --- what a project can be asked to do ----------------------------------------


def test_an_unconnected_project_can_be_asked_to_do_nothing(client, project_id):
    """The composer must not offer an app the project cannot reach."""
    assert client.get(f"/projects/{project_id}/actions/types").json() == []


def test_connecting_an_app_offers_its_actions(client, project_id, slack_connected):
    types = client.get(f"/projects/{project_id}/actions/types").json()

    assert {entry["type"] for entry in types} == {"post_message"}
    assert types[0]["integration"] == "slack"
    assert types[0]["verb"] == "message"
    assert types[0]["target_label"]  # the composer labels its own fields from this
    assert types[0]["value_label"]


def test_the_catalog_covers_every_verb_a_manager_needs():
    """add · update · delegate · close · message — the whole vocabulary, not a subset."""
    assert {entry.verb for entry in executor.ACTION_TYPES} == {
        "add",
        "update",
        "delegate",
        "close",
        "message",
    }


def test_action_types_are_404_for_someone_elses_project(client, db):
    db.tables.setdefault("projects", []).append(
        {"id": "not-mine", "owner_id": "someone-else", "name": "Theirs", "goal": "x"}
    )

    assert client.get("/projects/not-mine/actions/types").status_code == 404


# --- taking one ---------------------------------------------------------------


def test_an_action_written_here_runs_and_reports_back(client, project_id, slack_connected, executes):
    response = client.post(
        f"/projects/{project_id}/actions",
        json={"integration": "slack", "type": "post_message", "target": CHANNEL, "value": "Heads up"},
    )

    assert response.status_code == 201
    action = response.json()
    assert action["status"] == "completed"
    assert action["origin"] == "user"
    assert "#payments" in action["result"]
    assert action["executed_at"]


def test_it_reaches_the_integration_as_an_approved_action(client, project_id, slack_connected, executes):
    """The executor's guard is the last line before somebody's workspace. A dashboard
    action must arrive at it already approved, not bypass it."""
    post_message(client, project_id)

    assert executes[0]["status"] == "approved"
    assert executes[0]["action"].target == CHANNEL
    assert executes[0]["action"].params["value"].startswith("PAY-124")


def test_it_is_recorded_as_the_users_own(client, db, project_id, slack_connected, executes):
    post_message(client, project_id)

    row = db.tables["actions"][0]
    assert row["origin"] == "user"
    assert row["run_id"] is None
    assert row["approved_at"] and row["executed_at"]


def test_it_shows_up_in_the_project_without_any_analysis(client, project_id, slack_connected, executes):
    """There is no run to hang it off — it must still be listed."""
    post_message(client, project_id)

    actions = client.get(f"/projects/{project_id}/actions").json()
    assert [a["origin"] for a in actions] == ["user"]


def test_an_app_the_project_has_not_connected_is_refused(client, project_id):
    response = client.post(
        f"/projects/{project_id}/actions",
        json={"integration": "linear", "type": "create_issue", "target": "Fix it", "value": "x"},
    )

    assert response.status_code == 400
    assert "not connected" in response.json()["detail"]


def test_an_action_type_that_does_not_exist_is_refused(client, project_id, slack_connected):
    response = client.post(
        f"/projects/{project_id}/actions",
        json={"integration": "slack", "type": "delete_workspace", "target": "x", "value": "y"},
    )

    assert response.status_code == 400
    assert "delete_workspace" in response.json()["detail"]


def test_a_failure_is_recorded_on_the_action_not_thrown_away(
    client, project_id, slack_connected, monkeypatch
):
    def refuse(action, status):
        raise RuntimeError("channel_not_found")

    monkeypatch.setattr(service.executor, "execute", refuse)

    action = post_message(client, project_id)

    assert action["status"] == "failed"
    assert "channel_not_found" in action["result"]


def test_taking_an_action_on_someone_elses_project_is_a_404(client, db):
    db.tables.setdefault("projects", []).append(
        {"id": "not-mine", "owner_id": "someone-else", "name": "Theirs", "goal": "x"}
    )

    response = client.post(
        "/projects/not-mine/actions",
        json={"integration": "slack", "type": "post_message", "target": "#x", "value": "y"},
    )

    assert response.status_code == 404


def test_an_empty_target_is_refused_before_anything_runs(client, project_id, slack_connected, executes):
    response = client.post(
        f"/projects/{project_id}/actions",
        json={"integration": "slack", "type": "post_message", "target": "", "value": "hi"},
    )

    assert response.status_code == 422
    assert executes == []
