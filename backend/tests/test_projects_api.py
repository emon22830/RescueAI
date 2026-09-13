"""The project endpoints, exercised through the real FastAPI app."""

import pytest
from fastapi.testclient import TestClient

from app.config import ConfigurationError
from app.main import app
from app.projects import service


def create_project(client: TestClient) -> dict:
    response = client.post(
        "/projects", json={"name": "SaaS Product Launch", "goal": "Launch by Oct 1"}
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_health(client: TestClient):
    assert client.get("/health").json() == {"status": "ok"}


def test_create_project_returns_the_saved_project(client: TestClient):
    project = create_project(client)

    assert project["name"] == "SaaS Product Launch"
    assert project["goal"] == "Launch by Oct 1"
    assert project["id"]
    assert project["summary"] == {
        "health": "on_track",
        "blockers": 0,
        "risks": 0,
        "findings": 0,
    }


def test_list_projects_returns_newest_first(client: TestClient):
    create_project(client)
    client.post("/projects", json={"name": "Second", "goal": "Ship it"})

    names = [project["name"] for project in client.get("/projects").json()]
    assert names == ["Second", "SaaS Product Launch"]


def test_get_project_by_id(client: TestClient):
    created = create_project(client)

    response = client.get(f"/projects/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_unknown_project_is_404(client: TestClient):
    response = client.get("/projects/does-not-exist")

    assert response.status_code == 404
    assert "does-not-exist" in response.json()["detail"]


@pytest.mark.parametrize(
    "body",
    [{"name": "", "goal": "Launch"}, {"name": "Launch"}, {}],
    ids=["empty name", "missing goal", "empty body"],
)
def test_invalid_project_is_rejected(client: TestClient, body: dict):
    assert client.post("/projects", json=body).status_code == 422


def test_health_summary_reflects_the_latest_run(client: TestClient, db):
    project = create_project(client)

    _seed_run(db, project["id"], severities=["critical", "medium"])

    summary = client.get(f"/projects/{project['id']}").json()["summary"]
    assert summary == {"health": "at_risk", "blockers": 1, "risks": 1, "findings": 2}


def test_resync_replaces_the_previous_findings(client: TestClient, db):
    project = create_project(client)
    _seed_run(db, project["id"], severities=["critical", "high", "low"])
    _seed_run(db, project["id"], severities=["low"])

    summary = client.get(f"/projects/{project['id']}").json()["summary"]
    assert summary == {"health": "watch", "blockers": 0, "risks": 1, "findings": 1}

    findings = client.get(f"/projects/{project['id']}/findings").json()
    assert len(findings) == 1


def test_missing_configuration_is_503(monkeypatch):
    def unconfigured():
        raise ConfigurationError("Missing environment variable(s): SUPABASE_URL.")

    monkeypatch.setattr(service, "get_db", unconfigured)
    response = TestClient(app, raise_server_exceptions=False).get("/projects")

    assert response.status_code == 503
    assert "SUPABASE_URL" in response.json()["detail"]


def _seed_run(db, project_id: str, severities: list[str]) -> str:
    """Write a completed run with one finding per severity, as the agent would."""
    run = (
        db.table("agent_runs")
        .insert({"project_id": project_id, "status": "completed"})
        .execute()
        .data[0]
    )
    db.table("findings").insert(
        [
            {
                "project_id": project_id,
                "run_id": run["id"],
                "title": f"Finding {index}",
                "severity": severity,
                "confidence": 0.9,
                "description": "…",
                "evidence": [],
            }
            for index, severity in enumerate(severities)
        ]
    ).execute()
    return run["id"]
