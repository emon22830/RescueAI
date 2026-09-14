"""Continuous monitoring: the project re-analyses itself, and says what changed.

A rescue tool that only looks when somebody clicks is not monitoring anything. These
tests cover the three pieces that make it run on its own — the per-project schedule,
the tick that acts on it, and the notification that is the whole point of running while
nobody is watching.
"""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app import scheduler
from app.agents.state import Evidence
from app.integrations import calendar, drive, github, gmail, linear, slack
from app.projects import service
from tests.conftest import OWNER_ID


@pytest.fixture
def apps(monkeypatch):
    for module in (slack, gmail, github, linear, drive, calendar):
        source = module.__name__.rsplit(".", 1)[-1]
        monkeypatch.setattr(
            module,
            "collect_evidence",
            lambda _project_id, _name, source=source: [
                Evidence(source=source, type="message", title=f"{source} item", content="x")
            ],
        )


@pytest.fixture
def at_risk(monkeypatch):
    """An agent that finds one critical blocker."""

    def fake_ask_for(schema, system, prompt):
        if "findings" in schema.model_fields:
            return schema(
                findings=[
                    {
                        "title": "Payment API blocked",
                        "severity": "critical",
                        "confidence": 0.9,
                        "description": "PAY-124 has not moved.",
                        "evidence_indexes": [0],
                    }
                ],
                summary="Payments is blocked on a vendor sandbox key.",
                progress=40,
            )
        return schema(steps=[])

    from app.agents import recovery, risk

    monkeypatch.setattr(risk.llm, "ask_for", fake_ask_for)
    monkeypatch.setattr(recovery.llm, "ask_for", fake_ask_for)


def create_project(client, name: str = "SaaS Product Launch") -> str:
    return client.post("/projects", json={"name": name, "goal": "Ship it"}).json()["id"]


# --- the schedule -------------------------------------------------------------


def test_a_project_starts_on_no_schedule(client):
    """Monitoring is opt-in: nothing runs against someone's workspace unasked."""
    project = client.get(f"/projects/{create_project(client)}").json()

    assert project["sync_interval_minutes"] is None
    assert project["last_synced_at"] is None


def test_turning_monitoring_on_is_visible_on_the_project(client):
    project_id = create_project(client)

    response = client.put(f"/projects/{project_id}/schedule", json={"sync_interval_minutes": 60})

    assert response.status_code == 200
    assert response.json()["sync_interval_minutes"] == 60
    assert client.get(f"/projects/{project_id}").json()["sync_interval_minutes"] == 60


def test_turning_monitoring_off_again(client):
    project_id = create_project(client)
    client.put(f"/projects/{project_id}/schedule", json={"sync_interval_minutes": 60})

    client.put(f"/projects/{project_id}/schedule", json={"sync_interval_minutes": None})

    assert client.get(f"/projects/{project_id}").json()["sync_interval_minutes"] is None


def test_a_schedule_faster_than_the_floor_is_refused(client):
    """Below the floor costs more in API calls than it buys in freshness."""
    project_id = create_project(client)

    response = client.put(f"/projects/{project_id}/schedule", json={"sync_interval_minutes": 5})

    assert response.status_code == 422


def test_scheduling_someone_elses_project_is_a_404(client, db):
    db.tables.setdefault("projects", []).append(
        {"id": "not-mine", "owner_id": "someone-else", "name": "Theirs", "goal": "x"}
    )

    response = client.put("/projects/not-mine/schedule", json={"sync_interval_minutes": 60})

    assert response.status_code == 404


# --- what is due --------------------------------------------------------------


def project_row(**overrides) -> dict:
    return {
        "id": "p1",
        "owner_id": OWNER_ID,
        "name": "SaaS Product Launch",
        "goal": "Ship it",
        "sync_interval_minutes": None,
        "last_synced_at": None,
        **overrides,
    }


def test_an_unscheduled_project_is_never_due(db):
    db.tables.setdefault("projects", []).append(project_row())

    assert service.due_projects() == []


def test_a_scheduled_project_that_has_never_run_is_due_now(db):
    db.tables.setdefault("projects", []).append(project_row(sync_interval_minutes=60))

    assert [project["id"] for project in service.due_projects()] == ["p1"]


def test_a_project_synced_within_its_interval_is_not_due(db):
    recent = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    db.tables.setdefault("projects", []).append(project_row(sync_interval_minutes=60, last_synced_at=recent))

    assert service.due_projects() == []


def test_a_project_past_its_interval_is_due_again(db):
    stale = (datetime.now(UTC) - timedelta(minutes=61)).isoformat()
    db.tables.setdefault("projects", []).append(project_row(sync_interval_minutes=60, last_synced_at=stale))

    assert [project["id"] for project in service.due_projects()] == ["p1"]


# --- the tick -----------------------------------------------------------------


def test_a_tick_analyses_every_due_project_and_records_why_it_ran(client, db, apps, at_risk):
    project_id = create_project(client)
    client.put(f"/projects/{project_id}/schedule", json={"sync_interval_minutes": 60})

    assert asyncio.run(scheduler.tick()) == 1

    run = client.get(f"/projects/{project_id}/runs").json()[0]
    assert run["triggered_by"] == "schedule"
    assert run["status"] == "completed"
    assert run["health"] == "at_risk"


def test_a_tick_leaves_unscheduled_projects_alone(client, db, apps, at_risk):
    project_id = create_project(client)

    assert asyncio.run(scheduler.tick()) == 0
    assert client.get(f"/projects/{project_id}/runs").json() == []


def test_a_project_is_not_analysed_twice_in_one_interval(client, db, apps, at_risk):
    project_id = create_project(client)
    client.put(f"/projects/{project_id}/schedule", json={"sync_interval_minutes": 60})

    asyncio.run(scheduler.tick())
    asyncio.run(scheduler.tick())

    assert len(client.get(f"/projects/{project_id}/runs").json()) == 1


def test_a_failing_project_does_not_stop_the_rest_of_the_tick(client, db, apps, at_risk, monkeypatch):
    """One bad token must not mean every other project stops being monitored."""
    first = create_project(client, "Broken")
    second = create_project(client, "Healthy")
    for project_id in (first, second):
        client.put(f"/projects/{project_id}/schedule", json={"sync_interval_minutes": 60})

    original = service.run_analysis

    def explode(project_id, run_id):
        if project_id == first:
            raise RuntimeError("Slack token expired")
        return original(project_id, run_id)

    monkeypatch.setattr(service, "run_analysis", explode)

    assert asyncio.run(scheduler.tick()) == 2
    assert client.get(f"/projects/{second}/runs").json()[0]["status"] == "completed"


# --- notifications ------------------------------------------------------------


def test_a_project_turning_at_risk_notifies_its_owner(client, db, apps, at_risk):
    project_id = create_project(client)
    client.put(f"/projects/{project_id}/schedule", json={"sync_interval_minutes": 60})

    asyncio.run(scheduler.tick())

    notifications = client.get("/notifications").json()
    assert len(notifications) == 1
    assert notifications[0]["severity"] == "danger"
    assert notifications[0]["project_id"] == project_id
    assert "At risk" in notifications[0]["title"]
    assert notifications[0]["read_at"] is None


def test_the_same_verdict_twice_is_not_news(client, db, apps, at_risk):
    """A notification per tick would train the user to ignore all of them."""
    project_id = create_project(client)
    client.put(f"/projects/{project_id}/schedule", json={"sync_interval_minutes": 60})

    asyncio.run(scheduler.tick())
    db.tables["projects"][0]["last_synced_at"] = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    asyncio.run(scheduler.tick())

    assert len(client.get(f"/projects/{project_id}/runs").json()) == 2
    assert len(client.get("/notifications").json()) == 1


def test_a_failed_scheduled_run_is_notified_not_silent(client, db, apps, monkeypatch):
    from app.agents import risk

    monkeypatch.setattr(
        risk.llm, "ask_for", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("Gemini is down"))
    )
    project_id = create_project(client)
    client.put(f"/projects/{project_id}/schedule", json={"sync_interval_minutes": 60})

    asyncio.run(scheduler.tick())

    notification = client.get("/notifications").json()[0]
    assert notification["kind"] == "run_failed"
    assert "Gemini is down" in notification["body"]


def test_notifications_can_be_marked_read(client, db, apps, at_risk):
    project_id = create_project(client)
    client.put(f"/projects/{project_id}/schedule", json={"sync_interval_minutes": 60})
    asyncio.run(scheduler.tick())

    notification = client.get("/notifications").json()[0]
    response = client.post("/notifications/read", json={"notification_ids": [notification["id"]]})

    assert response.status_code == 200
    assert response.json()[0]["read_at"] is not None
    assert client.get("/notifications", params={"unread_only": True}).json() == []


def test_a_user_never_sees_another_users_notifications(client, db):
    db.tables.setdefault("notifications", []).append(
        {
            "id": "n1",
            "project_id": "p1",
            "owner_id": "someone-else",
            "run_id": None,
            "kind": "health_changed",
            "severity": "warn",
            "title": "Their project is now At risk",
            "body": "",
            "read_at": None,
        }
    )

    assert client.get("/notifications").json() == []
    assert client.post("/notifications/read", json={"notification_ids": ["n1"]}).json() == []
    assert db.tables["notifications"][0]["read_at"] is None


# --- surviving a database that has not been migrated yet ----------------------


def test_a_project_with_a_run_in_flight_is_not_due_again(client, db, apps, at_risk):
    """An analysis that outlasts its own interval must not stack runs on itself."""
    project_id = create_project(client)
    client.put(f"/projects/{project_id}/schedule", json={"sync_interval_minutes": 15})
    db.tables["agent_runs"].append(
        {"id": "r1", "project_id": project_id, "status": "running", "triggered_by": "schedule"}
    )

    assert service.due_projects() == []


def test_an_analysis_still_finishes_when_the_synced_stamp_cannot_be_written(
    client, db, apps, at_risk, monkeypatch
):
    """A database still on the pre-scheduling schema has no `last_synced_at` column.
    Losing the stamp is acceptable; losing the analysis that just ran is not."""
    project_id = create_project(client)

    real_table = db.table

    def refuse_the_stamp(name):
        table = real_table(name)
        if name == "projects":
            original_update = table.update

            def update(payload):
                if "last_synced_at" in payload:
                    raise RuntimeError("Could not find the 'last_synced_at' column")
                return original_update(payload)

            table.update = update
        return table

    monkeypatch.setattr(db, "table", refuse_the_stamp)

    client.post(f"/projects/{project_id}/analyze")

    run = client.get(f"/projects/{project_id}/runs").json()[0]
    assert run["status"] == "completed"
    assert run["health"] == "at_risk"
