"""Human approval and execution, end to end: API → service → executor → integration.

Only the integrations are stubbed — they stand in for the real Linear, Calendar and
Gmail calls and record exactly what they were handed, so these tests prove what would
have been sent to somebody's workspace.
"""

import pytest
from fastapi.testclient import TestClient

from app.agents import executor, risk
from app.agents.state import Evidence, PlannedAction
from app.integrations import calendar, gmail, linear, slack

PLAN = [
    {
        "integration": "linear",
        "type": "update_due_date",
        "description": "Move PAY-124 to Oct 8 so the sandbox key has time to land",
        "target": "PAY-124",
        "value": "2026-10-08",
        "finding_index": 0,
    },
    {
        "integration": "calendar",
        "type": "create_event",
        "description": "Book a 30 minute payments review with Dana and Sam",
        "target": "dana@example.test, sam@example.test",
        "value": "Payments unblock review",
        "finding_index": 0,
    },
    {
        "integration": "gmail",
        "type": "send_email",
        "description": "Tell the vendor the sandbox key is blocking the launch",
        "target": "support@vendor.test",
        "value": "We are blocked on the sandbox key for PAY-124.",
        "finding_index": 0,
    },
]


@pytest.fixture
def apps(monkeypatch):
    """One piece of Slack evidence, so the agent has something to reason over."""
    monkeypatch.setattr(
        slack,
        "collect_evidence",
        lambda _project_id, _name: [
            Evidence(
                source="slack",
                type="message",
                title="PAY-124 is blocked",
                content="Still waiting on the vendor sandbox key.",
                url="https://example.test/slack/1",
            )
        ],
    )


@pytest.fixture
def agent(monkeypatch):
    """One critical finding and the three-step recovery plan above."""

    def fake_ask_for(schema, system, prompt):
        if "findings" in schema.model_fields:
            return schema(
                findings=[
                    {
                        "title": "Payment API blocked",
                        "severity": "critical",
                        "confidence": 0.9,
                        "description": "PAY-124 has not moved since Sep 2.",
                        "evidence_indexes": [0],
                    }
                ],
                summary="Payments is blocked on a vendor sandbox key.",
                progress=40,
            )
        return schema(steps=PLAN)

    monkeypatch.setattr(risk.llm, "ask_for", fake_ask_for)


@pytest.fixture
def workspaces(monkeypatch) -> dict[str, list[PlannedAction]]:
    """Stand-ins for the three apps that accept writes; each records what it was sent."""
    sent: dict[str, list[PlannedAction]] = {"linear": [], "calendar": [], "gmail": []}

    def record(name: str, answer: str):
        def execute_action(action: PlannedAction) -> str:
            sent[name].append(action)
            return answer

        return execute_action

    monkeypatch.setattr(linear, "execute_action", record("linear", "PAY-124 due 2026-10-08"))
    monkeypatch.setattr(calendar, "execute_action", record("calendar", "Booked the review"))
    monkeypatch.setattr(gmail, "execute_action", record("gmail", "Emailed support@vendor.test"))
    return sent


def plan_for(client: TestClient) -> tuple[str, list[dict]]:
    """A project with a fresh analysis, and the pending actions it proposed."""
    project_id = client.post(
        "/projects", json={"name": "SaaS Product Launch", "goal": "Launch by Oct 1"}
    ).json()["id"]
    client.post(f"/projects/{project_id}/analyze")
    return project_id, client.get(f"/projects/{project_id}/actions").json()


def test_a_proposed_action_carries_what_it_will_do_and_why(client, apps, agent):
    _, actions = plan_for(client)

    assert len(actions) == 3
    linear_action = actions[0]
    assert linear_action["type"] == "update_due_date"
    assert linear_action["target"] == "PAY-124"
    assert linear_action["reason"] == "Payment API blocked"
    assert linear_action["status"] == "pending"
    assert linear_action["approved_at"] is None


def test_approving_executes_against_the_real_apps(client, apps, agent, workspaces):
    project_id, actions = plan_for(client)

    executed = client.post(
        f"/projects/{project_id}/actions/approve",
        json={"action_ids": [action["id"] for action in actions]},
    ).json()

    assert [action["status"] for action in executed] == ["completed"] * 3
    assert [action["result"] for action in executed] == [
        "PAY-124 due 2026-10-08",
        "Booked the review",
        "Emailed support@vendor.test",
    ]

    # Each app was handed its own step, with the target the plan named.
    assert workspaces["linear"][0].target == "PAY-124"
    assert workspaces["linear"][0].params["value"] == "2026-10-08"
    assert workspaces["calendar"][0].target == "dana@example.test, sam@example.test"
    assert workspaces["gmail"][0].target == "support@vendor.test"


def test_every_action_and_its_result_is_recorded(client, db, apps, agent, workspaces):
    project_id, actions = plan_for(client)

    client.post(
        f"/projects/{project_id}/actions/approve",
        json={"action_ids": [action["id"] for action in actions]},
    )

    stored = db.tables["actions"]
    assert len(stored) == 3
    for row in stored:
        assert row["status"] == "completed"
        assert row["result"]
        assert row["approved_at"] and row["executed_at"]

    # And it is what the API hands back afterwards, not just what is in the table.
    assert all(
        action["status"] == "completed"
        for action in client.get(f"/projects/{project_id}/actions").json()
    )


def test_an_action_is_marked_executing_while_the_app_is_written_to(client, db, apps, agent, monkeypatch):
    """The status is not cosmetic: whoever reads the table mid-request sees the truth."""
    seen: list[str] = []

    def watch(action):
        seen.extend(
            row["status"] for row in db.tables["actions"] if row["target"] == action.target
        )
        return "PAY-124 due 2026-10-08"

    monkeypatch.setattr(linear, "execute_action", watch)
    project_id, actions = plan_for(client)

    client.post(
        f"/projects/{project_id}/actions/approve", json={"action_ids": [actions[0]["id"]]}
    )

    assert seen == ["executing"]


def test_an_action_nobody_approved_is_never_executed(client, apps, agent, workspaces):
    project_id, actions = plan_for(client)

    approved = client.post(
        f"/projects/{project_id}/actions/approve",
        json={"action_ids": [actions[0]["id"]]},
    ).json()

    assert len(approved) == 1
    assert workspaces["calendar"] == [] and workspaces["gmail"] == []

    remaining = client.get(f"/projects/{project_id}/actions").json()
    assert [action["status"] for action in remaining] == ["completed", "pending", "pending"]


def test_approving_the_same_action_twice_does_not_run_it_twice(client, apps, agent, workspaces):
    project_id, actions = plan_for(client)
    body = {"action_ids": [actions[0]["id"]]}

    client.post(f"/projects/{project_id}/actions/approve", json=body)
    second = client.post(f"/projects/{project_id}/actions/approve", json=body).json()

    assert second == []
    assert len(workspaces["linear"]) == 1


def test_a_failed_action_records_why(client, apps, agent, monkeypatch):
    project_id, actions = plan_for(client)

    def refuse(_action):
        raise RuntimeError("Linear rejected the due date: 2026-10-08 is in the past")

    monkeypatch.setattr(linear, "execute_action", refuse)

    executed = client.post(
        f"/projects/{project_id}/actions/approve",
        json={"action_ids": [actions[0]["id"]]},
    ).json()

    assert executed[0]["status"] == "failed"
    assert "Linear rejected the due date" in executed[0]["result"]
    assert executed[0]["executed_at"], "a failed attempt still happened at a time"


def test_one_failure_does_not_stop_the_rest_of_the_plan(client, apps, agent, workspaces, monkeypatch):
    project_id, actions = plan_for(client)

    def boom(_action):
        raise RuntimeError("Linear is down")

    monkeypatch.setattr(linear, "execute_action", boom)

    executed = client.post(
        f"/projects/{project_id}/actions/approve",
        json={"action_ids": [action["id"] for action in actions]},
    ).json()

    assert [action["status"] for action in executed] == ["failed", "completed", "completed"]
    assert len(workspaces["gmail"]) == 1


def test_approving_nothing_executes_nothing(client, apps, agent, workspaces):
    project_id, _ = plan_for(client)

    assert client.post(f"/projects/{project_id}/actions/approve", json={"action_ids": []}).json() == []
    assert workspaces["linear"] == []


def test_the_executor_refuses_anything_that_is_not_approved():
    """The last gate before somebody else's workspace, checked on its own."""
    action = PlannedAction(
        integration="linear", type="update_issue", description="Move PAY-124", target="PAY-124"
    )

    for status in ("pending", "executing", "completed", "failed"):
        with pytest.raises(executor.NotApproved):
            executor.execute(action, status=status)
