"""Project business logic: create projects, run an analysis, store what came back.

Findings and actions are always read from the most recent completed run, so a
re-sync replaces what the dashboard shows instead of piling up on top of it.
The older rows stay in the tables as history.
"""

from collections import defaultdict
from datetime import datetime, timezone

from app.agents import executor
from app.agents.graph import analyze
from app.agents.state import PlannedAction
from app.db.supabase import get_db

BLOCKER_SEVERITIES = ("high", "critical")


class ProjectNotFound(Exception):
    """No project with that id."""


# --- projects ----------------------------------------------------------------


def create_project(name: str, goal: str) -> dict:
    db = get_db()
    project = db.table("projects").insert({"name": name, "goal": goal}).execute().data[0]
    project["summary"] = _empty_summary()
    return project


def list_projects() -> list[dict]:
    db = get_db()
    projects = db.table("projects").select("*").order("created_at", desc=True).execute().data

    summaries = _summaries_for([project["id"] for project in projects])
    for project in projects:
        project["summary"] = summaries.get(project["id"], _empty_summary())
    return projects


def get_project(project_id: str) -> dict:
    db = get_db()
    rows = db.table("projects").select("*").eq("id", project_id).execute().data
    if not rows:
        raise ProjectNotFound(f"No project with id {project_id}")

    project = rows[0]
    project["summary"] = _summaries_for([project_id]).get(project_id, _empty_summary())
    return project


# --- analysis ----------------------------------------------------------------


def analyze_project(project_id: str) -> dict:
    """Run the agent workflow and save the run, evidence, findings and proposed actions."""
    project = get_project(project_id)
    db = get_db()

    run = (
        db.table("agent_runs")
        .insert({"project_id": project_id, "status": "running"})
        .execute()
        .data[0]
    )

    try:
        result = analyze(project_id, project["name"], project["goal"])
    except Exception as error:
        db.table("agent_runs").update(
            {"status": "failed", "error": str(error), "completed_at": _now()}
        ).eq("id", run["id"]).execute()
        raise

    _save_results(project_id, run["id"], result)

    return (
        db.table("agent_runs")
        .update(
            {
                "status": "completed",
                "completed_at": _now(),
                "evidence_count": len(result["evidence"]),
                "finding_count": len(result["findings"]),
            }
        )
        .eq("id", run["id"])
        .execute()
        .data[0]
    )


def _save_results(project_id: str, run_id: str, result: dict) -> None:
    db = get_db()
    base = {"project_id": project_id, "run_id": run_id}

    if result["evidence"]:
        db.table("evidence").insert(
            [{**base, **item.model_dump(mode="json")} for item in result["evidence"]]
        ).execute()

    if result["findings"]:
        db.table("findings").insert(
            [{**base, **finding.model_dump(mode="json")} for finding in result["findings"]]
        ).execute()

    if result["plan"]:
        db.table("actions").insert(
            [
                {**base, "status": "pending", **action.model_dump(mode="json")}
                for action in result["plan"]
            ]
        ).execute()


# --- reading what the agent produced -----------------------------------------


def get_findings(project_id: str) -> list[dict]:
    run_id = _latest_run_ids([project_id]).get(project_id)
    if run_id is None:
        return []

    db = get_db()
    return db.table("findings").select("*").eq("run_id", run_id).execute().data


def get_runs(project_id: str) -> list[dict]:
    db = get_db()
    return (
        db.table("agent_runs")
        .select("*")
        .eq("project_id", project_id)
        .order("started_at", desc=True)
        .execute()
        .data
    )


def get_actions(project_id: str) -> list[dict]:
    run_id = _latest_run_ids([project_id]).get(project_id)
    if run_id is None:
        return []

    db = get_db()
    return db.table("actions").select("*").eq("run_id", run_id).execute().data


# --- approval ----------------------------------------------------------------


def approve_actions(project_id: str, action_ids: list[str]) -> list[dict]:
    """Execute the actions the user approved, and record what happened to each."""
    if not action_ids:
        return []

    db = get_db()
    rows = (
        db.table("actions")
        .select("*")
        .eq("project_id", project_id)
        .eq("status", "pending")
        .in_("id", action_ids)
        .execute()
        .data
    )

    executed = []
    for row in rows:
        update = {"approved_at": _now(), "executed_at": _now()}
        try:
            update["result"] = executor.execute(_to_planned_action(row))
            update["status"] = "executed"
        except Exception as error:
            update["result"] = str(error)
            update["status"] = "failed"
        executed.append(db.table("actions").update(update).eq("id", row["id"]).execute().data[0])
    return executed


# --- helpers -----------------------------------------------------------------


def _latest_run_ids(project_ids: list[str]) -> dict[str, str]:
    """Most recent completed run per project, in one query."""
    if not project_ids:
        return {}

    db = get_db()
    runs = (
        db.table("agent_runs")
        .select("id,project_id,started_at")
        .in_("project_id", project_ids)
        .eq("status", "completed")
        .order("started_at", desc=True)
        .execute()
        .data
    )

    latest: dict[str, str] = {}
    for run in runs:
        latest.setdefault(run["project_id"], run["id"])
    return latest


def _summaries_for(project_ids: list[str]) -> dict[str, dict]:
    """Blocker and risk counts per project, from each project's latest run."""
    run_ids = _latest_run_ids(project_ids)
    if not run_ids:
        return {}

    db = get_db()
    findings = (
        db.table("findings")
        .select("project_id,severity")
        .in_("run_id", list(run_ids.values()))
        .execute()
        .data
    )

    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"blockers": 0, "risks": 0})
    for finding in findings:
        key = "blockers" if finding["severity"] in BLOCKER_SEVERITIES else "risks"
        counts[finding["project_id"]][key] += 1

    return {project_id: _summary(**count) for project_id, count in counts.items()}


def _summary(blockers: int, risks: int) -> dict:
    if blockers:
        health = "at_risk"
    elif risks:
        health = "watch"
    else:
        health = "on_track"
    return {"health": health, "blockers": blockers, "risks": risks, "findings": blockers + risks}


def _empty_summary() -> dict:
    return _summary(blockers=0, risks=0)


def _to_planned_action(row: dict) -> PlannedAction:
    return PlannedAction(
        integration=row["integration"],
        action=row["action"],
        description=row["description"],
        params=row["params"],
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
