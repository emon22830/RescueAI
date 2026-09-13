"""Project business logic: create projects, run an analysis, store what came back.

Findings and actions are always read from the most recent completed run, so a
re-sync replaces what the dashboard shows instead of piling up on top of it.
The older rows stay in the tables as history.
"""

from collections import defaultdict
from datetime import datetime, timezone

from app.agents import executor
from app.agents.graph import analyze
from app.agents.state import BLOCKER_SEVERITIES, PlannedAction, health_for
from app.db.supabase import get_db


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


def analyze_project(project_id: str, triggered_by: str = "analyze") -> dict:
    """Run the agent workflow and save everything it produced.

    The run row is written first with status "running" so a crash leaves a trace
    instead of nothing. `triggered_by` separates a first analysis from a re-sync in
    the run history; the work itself is identical, because a sync *is* a fresh
    collection from every connected app.
    """
    project = get_project(project_id)
    db = get_db()

    run = (
        db.table("agent_runs")
        .insert({"project_id": project_id, "status": "running", "triggered_by": triggered_by})
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
                "health": result["health"],
                "summary": result["summary"],
                "progress": result["progress"],
                "activity": [entry.model_dump(mode="json") for entry in result["agent_activity"]],
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
    """Findings from the latest completed run — a re-sync replaces them, never appends."""
    _ensure_project_exists(project_id)

    run = _latest_runs([project_id]).get(project_id)
    if run is None:
        return []

    db = get_db()
    return db.table("findings").select("*").eq("run_id", run["id"]).execute().data


def get_runs(project_id: str) -> list[dict]:
    """Every run for this project, newest first — including failed and still-running ones."""
    _ensure_project_exists(project_id)

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
    """The recovery plan from the latest completed run, in the order the agent wrote it.

    That order is the plan: the agent puts the most urgent blocker first, so the
    steps must not come back shuffled.
    """
    _ensure_project_exists(project_id)

    run = _latest_runs([project_id]).get(project_id)
    if run is None:
        return []

    db = get_db()
    return (
        db.table("actions")
        .select("*")
        .eq("run_id", run["id"])
        .order("created_at")
        .execute()
        .data
    )


# --- approval and execution --------------------------------------------------


def approve_actions(project_id: str, action_ids: list[str]) -> list[dict]:
    """Approve the actions the user picked, then run them one after another.

    Approval and execution are a single request on purpose: no queue, no worker,
    no polling. Each action still moves through its real states in the database —
    approved, executing, then completed or failed — so a dashboard reading the
    table while this runs sees the truth, and an action interrupted mid-flight is
    left as "executing" instead of silently going back to pending.

    Ids that are not pending — already run, already approved, or belonging to
    another project — are skipped rather than run twice.
    """
    return [_execute(action) for action in _approve(project_id, action_ids)]


def _approve(project_id: str, action_ids: list[str]) -> list[dict]:
    """Record the human approval. This is the only thing that unlocks execution."""
    if not action_ids:
        return []

    db = get_db()
    pending = (
        db.table("actions")
        .select("*")
        .eq("project_id", project_id)
        .eq("status", "pending")
        .in_("id", action_ids)
        .execute()
        .data
    )
    if not pending:
        return []

    return (
        db.table("actions")
        .update({"status": "approved", "approved_at": _now()})
        .in_("id", [action["id"] for action in pending])
        .execute()
        .data
    )


def _execute(action: dict) -> dict:
    """Run one approved action and record what the integration said back.

    The status is read before the row is marked "executing", because the thing that
    unlocks the integration is the approval that was just recorded. A failure is a
    result too: the message is stored and shown, because "Linear rejected the due
    date" is something the user needs to read.
    """
    status = action["status"]
    _mark(action["id"], {"status": "executing"})
    try:
        result = executor.execute(_to_planned_action(action), status=status)
        return _mark(action["id"], {"status": "completed", "result": result, "executed_at": _now()})
    except Exception as error:
        return _mark(
            action["id"], {"status": "failed", "result": str(error), "executed_at": _now()}
        )


def _mark(action_id: str, changes: dict) -> dict:
    db = get_db()
    return db.table("actions").update(changes).eq("id", action_id).execute().data[0]


# --- helpers -----------------------------------------------------------------


def _ensure_project_exists(project_id: str) -> None:
    """An unknown id must be a 404, not an empty list that reads like "nothing found yet"."""
    db = get_db()
    if not db.table("projects").select("id").eq("id", project_id).execute().data:
        raise ProjectNotFound(f"No project with id {project_id}")


def _latest_runs(project_ids: list[str]) -> dict[str, dict]:
    """Most recent completed run per project, in one query."""
    if not project_ids:
        return {}

    db = get_db()
    runs = (
        db.table("agent_runs")
        .select("id,project_id,started_at,health,summary,progress")
        .in_("project_id", project_ids)
        .eq("status", "completed")
        .order("started_at", desc=True)
        .execute()
        .data
    )

    latest: dict[str, dict] = {}
    for run in runs:
        latest.setdefault(run["project_id"], run)
    return latest


def _summaries_for(project_ids: list[str]) -> dict[str, dict]:
    """What the dashboard shows per project, from each project's latest completed run.

    Health, summary and progress are read back exactly as the agent wrote them; only
    the blocker and risk counts are tallied here, from the findings of that same run.
    """
    runs = _latest_runs(project_ids)
    if not runs:
        return {}

    db = get_db()
    findings = (
        db.table("findings")
        .select("project_id,severity")
        .in_("run_id", [run["id"] for run in runs.values()])
        .execute()
        .data
    )

    severities: dict[str, list[str]] = defaultdict(list)
    for finding in findings:
        severities[finding["project_id"]].append(finding["severity"])

    return {project_id: _summary(severities[project_id], run) for project_id, run in runs.items()}


def _summary(severities: list[str], run: dict | None = None) -> dict:
    """Counts from the findings; health, summary and progress from the run that found them.

    A run written before health was stored still gets the right answer: the same rule
    the risk agent used is applied to the severities it produced.
    """
    run = run or {}
    blockers = sum(1 for severity in severities if severity in BLOCKER_SEVERITIES)
    return {
        "health": run.get("health") or health_for(severities),
        "summary": run.get("summary") or "",
        "progress": run.get("progress"),
        "blockers": blockers,
        "risks": len(severities) - blockers,
        "findings": len(severities),
    }


def _empty_summary() -> dict:
    return _summary([])


def _to_planned_action(row: dict) -> PlannedAction:
    return PlannedAction(
        integration=row["integration"],
        type=row["type"],
        description=row["description"],
        target=row.get("target", ""),
        reason=row.get("reason", ""),
        params=row.get("params") or {},
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
