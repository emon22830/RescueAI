"""The analysis flow, end to end: API → service → LangGraph → database → API.

The integrations and the LLM are the only things stubbed. Everything between them —
the graph, the persistence, and what the read endpoints hand back — is the real code.
"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.agents import executor, risk
from app.agents.state import Evidence

# Every app the workflow investigates, from the one place that lists them — so adding a
# connector does not mean hand-editing counts in this file.
APPS = sorted(executor.INTEGRATIONS)

SUMMARY = "Payments is blocked on a vendor sandbox key; PAY-124 has not moved since Sep 2."


@pytest.fixture
def apps(monkeypatch):
    """Each connected app returns one piece of evidence, as a live workspace would."""
    for source, module in executor.INTEGRATIONS.items():
        monkeypatch.setattr(
            module,
            "collect_evidence",
            lambda _project_id, _name, source=source: [
                Evidence(
                    source=source,
                    type="message",
                    title=f"{source} item",
                    content=f"what {source} said",
                    url=f"https://example.test/{source}",
                    timestamp=datetime(2026, 9, 2, tzinfo=UTC),
                )
            ],
        )


@pytest.fixture
def agent(monkeypatch):
    """One critical finding, one recovery step, and a project state to persist."""

    def fake_ask_for(schema, system, prompt):
        return schema(
            findings=[
                {
                    "title": "Payment API blocked",
                    "severity": "critical",
                    "confidence": 0.9,
                    "description": "Slack and Linear disagree about PAY-124.",
                    "evidence_indexes": [0, 1],
                }
            ],
            summary=SUMMARY,
            progress=40,
            steps=[
                {
                    "integration": "linear",
                    "type": "update_issue",
                    "description": "Reassign PAY-124 to Dana",
                    "target": "PAY-124",
                    "value": "assign to Dana",
                    "finding_index": 0,
                }
            ],
        )

    monkeypatch.setattr(risk.llm, "ask_for", fake_ask_for)


def create_project(client: TestClient) -> str:
    response = client.post(
        "/projects", json={"name": "SaaS Product Launch", "goal": "Launch by Oct 1"}
    )
    return response.json()["id"]


def analyze(client, project_id: str, path: str = "analyze") -> dict:
    """Start a run and hand back the finished one.

    /analyze only queues the run — the work happens in a background task, which
    TestClient runs before it returns the response. So the run at the top of the
    history by the time this returns is the completed one.
    """
    response = client.post(f"/projects/{project_id}/{path}")
    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    return client.get(f"/projects/{project_id}/runs").json()[0]


def test_analyze_is_accepted_and_finishes_in_the_background(client, apps, agent):
    """The request returns a queued run; the result arrives on that same run."""
    project_id = create_project(client)

    response = client.post(f"/projects/{project_id}/analyze")

    assert response.status_code == 202
    queued = response.json()
    assert queued["status"] == "queued"
    assert queued["completed_at"] is None

    finished = client.get(f"/projects/{project_id}/runs").json()[0]
    assert finished["id"] == queued["id"]
    assert finished["status"] == "completed"


def test_analyze_persists_the_run_and_the_project_state(client, apps, agent):
    project_id = create_project(client)

    run = analyze(client, project_id)

    assert run["status"] == "completed"
    assert run["triggered_by"] == "analyze"
    assert run["evidence_count"] == len(APPS)
    assert run["finding_count"] == 1
    assert run["health"] == "at_risk"
    assert run["summary"] == SUMMARY
    assert run["progress"] == 40
    assert run["completed_at"]


def test_analyze_persists_evidence_findings_and_actions(client, db, apps, agent):
    project_id = create_project(client)
    run = analyze(client, project_id)

    for table in ("evidence", "findings", "actions"):
        rows = db.tables[table]
        assert rows, f"nothing was saved to {table}"
        assert all(row["run_id"] == run["id"] for row in rows)
        assert all(row["project_id"] == project_id for row in rows)

    assert len(db.tables["evidence"]) == len(APPS)
    assert db.tables["actions"][0]["status"] == "pending"


def test_the_project_summary_shows_what_the_agent_concluded(client, apps, agent):
    project_id = create_project(client)
    client.post(f"/projects/{project_id}/analyze")

    summary = client.get(f"/projects/{project_id}").json()["summary"]

    assert summary["health"] == "at_risk"
    assert summary["summary"] == SUMMARY
    assert summary["progress"] == 40
    assert (summary["blockers"], summary["risks"], summary["findings"]) == (1, 0, 1)


def test_findings_come_back_with_the_evidence_that_supports_them(client, apps, agent):
    project_id = create_project(client)
    client.post(f"/projects/{project_id}/analyze")

    findings = client.get(f"/projects/{project_id}/findings").json()

    assert len(findings) == 1
    assert findings[0]["title"] == "Payment API blocked"
    evidence = findings[0]["evidence"]
    assert len(evidence) == 2
    assert all(item["url"] for item in evidence), "a finding must stay checkable"


def test_actions_are_proposed_but_not_executed(client, apps, agent):
    project_id = create_project(client)
    client.post(f"/projects/{project_id}/analyze")

    actions = client.get(f"/projects/{project_id}/actions").json()

    assert len(actions) == 1
    assert actions[0]["status"] == "pending"
    assert actions[0]["result"] is None
    assert actions[0]["type"] == "update_issue"
    assert actions[0]["target"] == "PAY-124"
    assert actions[0]["reason"] == "Payment API blocked"


def test_sync_replaces_the_project_state_with_what_is_true_now(client, apps, agent, monkeypatch):
    project_id = create_project(client)
    client.post(f"/projects/{project_id}/analyze")

    # The blocker was cleared in the real apps, so the next collection finds nothing wrong.
    monkeypatch.setattr(
        risk.llm,
        "ask_for",
        lambda schema, system, prompt: (
            schema(findings=[], summary="PAY-124 shipped; nothing is blocking the launch.")
            if "findings" in schema.model_fields
            else schema(steps=[])
        ),
    )

    run = analyze(client, project_id, "sync")

    assert run["triggered_by"] == "sync"
    assert run["finding_count"] == 0

    summary = client.get(f"/projects/{project_id}").json()["summary"]
    assert summary["health"] == "on_track"
    assert summary["findings"] == 0
    assert summary["progress"] is None

    assert client.get(f"/projects/{project_id}/findings").json() == []
    assert client.get(f"/projects/{project_id}/actions").json() == []


def test_runs_lists_every_pass_newest_first(client, apps, agent):
    project_id = create_project(client)
    client.post(f"/projects/{project_id}/analyze")
    client.post(f"/projects/{project_id}/sync")

    runs = client.get(f"/projects/{project_id}/runs").json()

    assert [run["triggered_by"] for run in runs] == ["sync", "analyze"]
    assert all(run["status"] == "completed" for run in runs)


def test_a_run_records_which_app_gave_what(client, apps, agent):
    project_id = create_project(client)
    client.post(f"/projects/{project_id}/analyze")

    activity = client.get(f"/projects/{project_id}/runs").json()[0]["activity"]

    from app.agents import supervisor

    agents = {entry["agent"] for entry in activity}
    assert agents == {"supervisor", *supervisor.AGENTS, "risk", "recovery"}
    assert sum(entry["evidence_count"] for entry in activity) == len(APPS)


def test_an_unconnected_workspace_produces_no_findings(client):
    """No credentials means no evidence, and no evidence must never mean invented findings."""
    project_id = create_project(client)

    run = analyze(client, project_id)

    assert run["evidence_count"] == 0
    assert run["finding_count"] == 0
    assert run["health"] == "on_track"
    assert run["progress"] is None
    assert client.get(f"/projects/{project_id}/findings").json() == []
    assert client.get(f"/projects/{project_id}/actions").json() == []


def test_a_failed_run_is_recorded_and_surfaced(client, apps, monkeypatch):
    project_id = create_project(client)

    def boom(*_args, **_kwargs):
        raise RuntimeError("Gemini is down")

    monkeypatch.setattr(risk.llm, "ask_for", boom)

    # The run was accepted, so the failure has to be visible on the run itself —
    # there is no request left to return 500 to once the work has been handed off.
    response = TestClient(client.app, raise_server_exceptions=False).post(
        f"/projects/{project_id}/analyze"
    )
    assert response.status_code == 202

    run = client.get(f"/projects/{project_id}/runs").json()[0]
    assert run["status"] == "failed"
    assert "Gemini is down" in run["error"]

    # A failed run must not become the project state.
    assert client.get(f"/projects/{project_id}").json()["summary"]["health"] == "on_track"


@pytest.mark.parametrize("path", ["findings", "runs", "actions"])
def test_reads_404_for_an_unknown_project(client, path):
    """An empty list would read as "analyzed, found nothing" and hide the typo."""
    response = client.get(f"/projects/does-not-exist/{path}")

    assert response.status_code == 404
    assert "does-not-exist" in response.json()["detail"]


@pytest.mark.parametrize("path", ["analyze", "sync"])
def test_runs_404_for_an_unknown_project(client, path):
    assert client.post(f"/projects/does-not-exist/{path}").status_code == 404
