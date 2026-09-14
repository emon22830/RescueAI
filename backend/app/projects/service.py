"""Project business logic: create projects, run an analysis, store what came back.

Findings and actions are always read from the most recent completed run, so a
re-sync replaces what the dashboard shows instead of piling up on top of it.
The older rows stay in the tables as history.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel

from app.auth import security
from app.agents import executor
from app.agents.graph import analyze
from app.agents.state import BLOCKER_SEVERITIES, Evidence, PlannedAction, health_for
from app.ai import llm
from app.db.supabase import get_db
from app.integrations import asana, github, google_auth, jira, linear, notion, slack, trello

# The apps a project connects its own credential for, from the frontend, verified
# before the token is stored. Gmail/Drive/Calendar stay on the shared backend/.env
# Google app until Phase 2 makes them per-project too.
TOKEN_INTEGRATIONS = {
    "slack": slack,
    "linear": linear,
    "github": github,
    "jira": jira,
    "asana": asana,
    "trello": trello,
    "notion": notion,
}

# The shortest schedule a project may set. Anything faster costs more in API calls than
# it buys in freshness — nothing in Slack or Linear changes meaningfully in ten minutes.
MIN_SYNC_MINUTES = 15

HEALTH_WORDS = {"on_track": "On track", "watch": "Watch", "at_risk": "At risk"}

logger = logging.getLogger(__name__)


class ProjectNotFound(Exception):
    """No project with that id — also raised for a project id that belongs to
    someone else, so ownership is never revealed by the error itself."""


# --- projects ----------------------------------------------------------------


def create_project(name: str, goal: str, owner_id: str) -> dict:
    db = get_db()
    project = (
        db.table("projects")
        .insert({"name": name, "goal": goal, "owner_id": owner_id})
        .execute()
        .data[0]
    )
    project["summary"] = _empty_summary()
    return project


def list_projects(owner_id: str) -> list[dict]:
    db = get_db()
    projects = (
        db.table("projects")
        .select("*")
        .eq("owner_id", owner_id)
        .order("created_at", desc=True)
        .execute()
        .data
    )

    ids = [project["id"] for project in projects]
    summaries = _summaries_for(ids)
    connected = _connected_for(ids)
    for project in projects:
        project["summary"] = summaries.get(project["id"], _empty_summary())
        project["connected"] = connected.get(project["id"], [])
    return projects


def get_project(project_id: str, owner_id: str) -> dict:
    project = _ensure_owned(project_id, owner_id)
    project["summary"] = _summaries_for([project_id]).get(project_id, _empty_summary())
    project["connected"] = _connected_for([project_id]).get(project_id, [])
    return project


def delete_project(project_id: str, owner_id: str) -> None:
    """Delete the project and everything under it — runs, evidence, findings, actions
    and connected integrations all cascade from the `projects` row in schema.sql, so
    one delete here is enough. Irreversible; the frontend is what confirms with a human
    before this is ever called."""
    _ensure_owned(project_id, owner_id)
    get_db().table("projects").delete().eq("id", project_id).execute()


# --- analysis ----------------------------------------------------------------


# An analysis takes as long as the slowest connected app plus two LLM calls, which is
# far longer than a browser should be held open. So it is two steps: the request
# accepts the run and returns it as "queued", and the work happens afterwards — from a
# background task (api/analysis.py) or from the scheduler (app/scheduler.py). The run
# row is the handle to both, which is why it is written before any work starts.


def start_analysis(project_id: str, owner_id: str, triggered_by: str = "analyze") -> dict:
    """Accept an analysis and return the queued run that will carry its result.

    Nothing is collected here. Writing the run first means the project has a visible
    pending run the moment the user clicks, instead of a silent gap until the work ends.
    """
    get_project(project_id, owner_id)
    return (
        get_db()
        .table("agent_runs")
        .insert({"project_id": project_id, "status": "queued", "triggered_by": triggered_by})
        .execute()
        .data[0]
    )


def run_analysis(project_id: str, run_id: str) -> dict:
    """Do the work for a queued run, save everything it produced, and return the run.

    No ownership check and no raising: `start_analysis` already checked the owner, and
    this runs with no request to fail — a crash is recorded on the run as `failed` and
    notified, because a background failure nobody is told about is the same as silence.
    """
    db = get_db()
    rows = db.table("projects").select("*").eq("id", project_id).execute().data
    if not rows:
        raise ProjectNotFound(f"No project with id {project_id}")
    project = rows[0]

    # Read before the run overwrites it — this is what "health changed" compares against.
    previous = _latest_runs([project_id]).get(project_id)
    db.table("agent_runs").update({"status": "running"}).eq("id", run_id).execute()

    try:
        result = analyze(project_id, project["name"], project["goal"])
    except Exception as error:  # noqa: BLE001 — recorded on the run, not swallowed
        logger.exception("Analysis failed for project %s", project_id)
        _touch_synced(project_id)
        run = (
            db.table("agent_runs")
            .update({"status": "failed", "error": str(error), "completed_at": _now()})
            .eq("id", run_id)
            .execute()
            .data[0]
        )
        _notify(
            project,
            run_id,
            kind="run_failed",
            severity="danger",
            title=f"Analysis failed for {project['name']}",
            body=str(error),
        )
        return run

    _save_results(project_id, run_id, result)
    _touch_synced(project_id)

    run = (
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
        .eq("id", run_id)
        .execute()
        .data[0]
    )

    _notify_verdict(project, run_id, previous, result)
    return run


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


# --- answering a question about the project -----------------------------------

# Gmail, Drive and Calendar share one OAuth client for the whole deployment; the rest
# are connected per project. Both kinds count as "this project can reach it".
GOOGLE_INTEGRATIONS = ("gmail", "drive", "calendar")

# A run's evidence is already bounded by each integration's own window, but the prompt
# should never be unbounded just because someone connected a very busy workspace.
MAX_EVIDENCE_IN_PROMPT = 150

ASK_SYSTEM = """You are RescueAI's analyst for one project, talking to the person who
runs it. You sound like a colleague who has just read everything the team wrote this
week: direct, specific, and never padded.

WHAT YOU KNOW
The evidence below is everything the latest run collected from the team's own Slack,
Gmail, Drive, Linear, GitHub and Calendar. It is your only knowledge of this project.
You never assume what an app "probably" says.

HOW TO WRITE
- Lead with the answer in one sentence, then support it. Never open with a preamble
  about what you are about to do.
- Then give the detail that makes it useful: what happened, who is involved, which
  dates, what it blocks. Match the length to the question — a factual one-liner gets a
  line, "where are we?" gets a proper brief.
- Markdown: **bold** for the names, issues and dates that matter; `-` bullets for a list
  of genuinely distinct items; "### " headings only when the answer has three or more
  real sections. Never bullet a single thought, never head a two-line answer.
- Cite the index of every piece of evidence you used. Do not restate an item verbatim as
  though it were your conclusion — the reader can open it. Tell them what it means.
- Close a substantial answer with the one thing you would do next, when the evidence
  supports one.
- Suggest up to three follow-up questions this same evidence could answer. Leave the
  list empty when none would add anything.

THE THREE KINDS OF REPLY
- kind "answer" — the evidence answers the question. answered = true, indexes cited.
- kind "gap" — it does not. answered = false. Say plainly what is missing and which app
  would hold it. Never fill a gap with a guess, and never soften it into a vague answer.
- kind "chat" — the message is a greeting, a thank-you, or a question about you rather
  than about the project ("hi", "what can you do?"). answered = true, no evidence cited.
  Reply the way a person would, in a line or two, then say concretely what you can tell
  them about THIS project, using what you can see in the evidence to make the offer real
  rather than generic."""

ASK_NO_EVIDENCE_SYSTEM = """You are RescueAI's analyst for one project, talking to the
person who runs it.

The latest run collected NO evidence at all: no Slack message, no issue, no email, no
document. So you know the project's name and goal and nothing else whatsoever.

- If the message is a greeting, a thank-you, or a question about you ("hi", "what can
  you do?"), reply the way a person would — a friendly line or two — then explain in
  plain terms what you do: you read the team's Slack, Gmail, Drive, Linear, GitHub and
  Calendar, and answer only from what is actually there. Set kind "chat", answered true.
- For anything about the project itself, set kind "gap" and answered false. Say that the
  last run found nothing, name which app would hold the answer they asked for, and tell
  them what to fix: connect the project's apps on the Connections page, then run an
  investigation. Never guess at a status, a date, a name or a blocker.
- Never invent evidence, and always leave evidence_indexes empty.
- Markdown is available: **bold** and `-` bullets. Keep it short."""


class _Answer(BaseModel):
    answer: str
    evidence_indexes: list[int]
    answered: bool
    # Why the answer looks the way it does, so the UI can stop flagging a friendly
    # hello as a hole in the evidence. Defaults to the ordinary grounded case.
    kind: Literal["answer", "gap", "chat"] = "answer"
    # Questions this same evidence could answer next. The panel offers them as chips.
    follow_ups: list[str] = []


def answer_question(project_id: str, owner_id: str, question: str) -> dict:
    """Answer from the latest completed run's evidence, citing what it used.

    A project that has never run has nothing to talk about, so it is refused without
    spending a model call. A run that collected nothing still gets one: "hi" and "what
    can you do?" deserve a real reply, and the prompt for that case forbids every claim
    about the project itself.
    """
    _ensure_owned(project_id, owner_id)

    run = _latest_runs([project_id]).get(project_id)
    if run is None:
        return {
            "question": question,
            "answer": "This project has not been analyzed yet, so there is no evidence to "
            "answer from. Connect the apps it runs on and run an investigation first.",
            "answered": False,
            "kind": "gap",
            "follow_ups": [],
            "evidence": [],
        }

    evidence = _evidence_for_run(run["id"])
    system = ASK_SYSTEM if evidence else ASK_NO_EVIDENCE_SYSTEM

    result = llm.ask_for(_Answer, system, _ask_prompt(project_id, question, evidence))
    cited = [evidence[i] for i in result.evidence_indexes if 0 <= i < len(evidence)]

    return {
        "question": question,
        "answer": result.answer,
        "answered": result.answered,
        "kind": result.kind,
        "follow_ups": result.follow_ups[:3],
        "evidence": [item.model_dump(mode="json") for item in cited],
    }


def _evidence_for_run(run_id: str) -> list[Evidence]:
    """This run's evidence, newest first, capped for the prompt.

    Ordered here rather than in the query because `timestamp` is nullable and Postgres
    sorts NULLs first on DESC — which would fill the cap with undated items and drop the
    recent ones. A single run's evidence is already bounded by each integration's own
    collection window, so there is nothing to paginate.
    """
    rows = get_db().table("evidence").select("*").eq("run_id", run_id).execute().data
    evidence = [Evidence(**row) for row in rows]
    evidence.sort(key=lambda item: (item.timestamp is not None, item.timestamp), reverse=True)
    return evidence[:MAX_EVIDENCE_IN_PROMPT]


def _ask_prompt(project_id: str, question: str, evidence: list[Evidence]) -> str:
    project = get_db().table("projects").select("name,goal").eq("id", project_id).execute().data[0]
    lines = [
        f"TODAY: {datetime.now(timezone.utc).date().isoformat()}",
        f"PROJECT: {project['name']}",
        f"GOAL: {project['goal']}",
        "",
        "EVIDENCE:",
    ]
    if not evidence:
        lines.append("(none — the latest run collected nothing)")
    for index, item in enumerate(evidence):
        when = item.timestamp.date().isoformat() if item.timestamp else "unknown date"
        lines.append(f"[{index}] {item.source} · {item.type} · {when} · {item.title}")
        lines.append(f"    {item.content}")
    lines += ["", f"QUESTION: {question}"]
    return "\n".join(lines)


# --- reading what the agent produced -----------------------------------------


def get_findings(project_id: str, owner_id: str) -> list[dict]:
    """Findings from the latest completed run — a re-sync replaces them, never appends."""
    _ensure_owned(project_id, owner_id)

    run = _latest_runs([project_id]).get(project_id)
    if run is None:
        return []

    db = get_db()
    return db.table("findings").select("*").eq("run_id", run["id"]).execute().data


def get_runs(project_id: str, owner_id: str) -> list[dict]:
    """Every run for this project, newest first — including failed and still-running ones."""
    _ensure_owned(project_id, owner_id)

    db = get_db()
    return (
        db.table("agent_runs")
        .select("*")
        .eq("project_id", project_id)
        .order("started_at", desc=True)
        .execute()
        .data
    )


def get_actions(project_id: str, owner_id: str) -> list[dict]:
    """The recovery plan from the latest completed run, plus anything the user did
    themselves — in the order it was written.

    That order is the plan: the agent puts the most urgent blocker first, so the steps
    must not come back shuffled. Actions a person wrote at the dashboard carry no
    `run_id`, so they survive a re-sync instead of disappearing with the run they
    happened to be contemporary with.
    """
    _ensure_owned(project_id, owner_id)

    run = _latest_runs([project_id]).get(project_id)
    latest_run_id = run["id"] if run else None

    rows = (
        get_db()
        .table("actions")
        .select("*")
        .eq("project_id", project_id)
        .order("created_at")
        .execute()
        .data
    )
    # Filtered here rather than in SQL: "this run, or no run at all" is two conditions
    # PostgREST expresses awkwardly, and this is one small list per project either way.
    return [row for row in rows if row.get("run_id") in (latest_run_id, None)]


def create_action(
    project_id: str,
    owner_id: str,
    integration: str,
    type: str,
    target: str,
    value: str,
    description: str = "",
    params: dict | None = None,
) -> dict:
    """Take one action against a connected app, written by a person at the dashboard.

    Authored and approved in the same gesture — the user filled in what to send, to
    what, and pressed the button that says so; there is no second human left to ask.
    It still goes through the same row, the same states and the same guard in
    `executor.execute` as anything the agent proposed, so the audit trail does not
    care which of the two wrote it.
    """
    _ensure_owned(project_id, owner_id)

    known = executor.find_type(integration, type)
    if known is None:
        raise ValueError(f"There is no '{type}' action for {integration}")

    connected = _connected_for([project_id]).get(project_id, [])
    if integration not in connected:
        raise ValueError(f"{integration.title()} is not connected for this project")

    if not target:
        raise ValueError(f"{known.label} needs {known.target_label.lower()}")

    action = (
        get_db()
        .table("actions")
        .insert(
            {
                "project_id": project_id,
                "run_id": None,
                "origin": "user",
                "integration": integration,
                "type": type,
                "description": description or known.label,
                "target": target,
                "reason": "Taken from the dashboard",
                "params": {**(params or {}), "value": value},
                "status": "pending",
            }
        )
        .execute()
        .data[0]
    )

    approved = _approve(project_id, [action["id"]])
    return _execute(approved[0])


def action_types(project_id: str, owner_id: str) -> list[dict]:
    """What this project can actually be asked to do, given what it has connected."""
    _ensure_owned(project_id, owner_id)
    connected = _connected_for([project_id]).get(project_id, [])
    return [action.model_dump() for action in executor.types_for(connected)]


# --- scheduling ---------------------------------------------------------------
#
# A project can re-analyse itself on an interval. The loop that acts on this lives in
# app/scheduler.py; everything here is just the reading and writing it needs.


def set_schedule(project_id: str, owner_id: str, minutes: int | None) -> dict:
    """Set how often this project re-analyses itself, or None to turn it off."""
    _ensure_owned(project_id, owner_id)

    if minutes is not None and minutes < MIN_SYNC_MINUTES:
        raise ValueError(f"The shortest schedule is every {MIN_SYNC_MINUTES} minutes")

    get_db().table("projects").update({"sync_interval_minutes": minutes}).eq(
        "id", project_id
    ).execute()
    return get_project(project_id, owner_id)


def due_projects(now: datetime | None = None) -> list[dict]:
    """Every scheduled project whose next run is due, for any owner.

    Two queries for all projects, filtered here rather than in SQL: at this scale that
    is a pair of small scans per tick, where a per-project query would be an N+1 on a
    timer. A project whose previous run is still going is never due — an analysis that
    takes longer than its own interval would otherwise stack runs on top of each other.
    """
    now = now or datetime.now(timezone.utc)
    projects = get_db().table("projects").select("*").execute().data
    busy = _projects_with_a_run_in_flight([project["id"] for project in projects])
    return [
        project
        for project in projects
        if project["id"] not in busy and _is_due(project, now)
    ]


def _projects_with_a_run_in_flight(project_ids: list[str]) -> set[str]:
    if not project_ids:
        return set()

    runs = (
        get_db()
        .table("agent_runs")
        .select("project_id,status")
        .in_("project_id", project_ids)
        .execute()
        .data
    )
    return {run["project_id"] for run in runs if run["status"] in ("queued", "running")}


def _is_due(project: dict, now: datetime) -> bool:
    interval = project.get("sync_interval_minutes")
    if not interval:
        return False

    last = project.get("last_synced_at")
    if not last:
        return True
    return _as_datetime(last) + timedelta(minutes=interval) <= now


def _touch_synced(project_id: str) -> None:
    """Stamp the project as synced. Written whether the run succeeded or failed, so a
    project whose Slack token has expired retries on its schedule instead of every tick.

    Never allowed to fail the run around it. This is the one write that a database still
    on the pre-scheduling schema does not have a column for, and an analysis that
    finished is worth more than the timestamp saying when — the run itself already
    records that. `due_projects` skips anything still in flight, so a missing stamp
    cannot turn into a project re-analysing itself every tick.
    """
    try:
        get_db().table("projects").update({"last_synced_at": _now()}).eq(
            "id", project_id
        ).execute()
    except Exception:  # noqa: BLE001
        logger.exception(
            "Could not stamp last_synced_at on project %s — has migration "
            "0002_scheduling_and_notifications.sql been run?",
            project_id,
        )


# --- notifications -------------------------------------------------------------
#
# What the agent concluded while nobody was watching. These are in-app only: posting a
# change into Slack would be writing to someone's workspace without approval, which is
# what the approval flow exists to prevent.


def list_notifications(owner_id: str, unread_only: bool = False) -> list[dict]:
    query = (
        get_db()
        .table("notifications")
        .select("*")
        .eq("owner_id", owner_id)
        .order("created_at", desc=True)
        .limit(50)
    )
    rows = query.execute().data
    return [row for row in rows if row.get("read_at") is None] if unread_only else rows


def mark_notifications_read(owner_id: str, notification_ids: list[str]) -> list[dict]:
    """Mark the given notifications read. Ids belonging to someone else are ignored
    rather than refused, so one stale id cannot fail the whole request."""
    if not notification_ids:
        return []

    db = get_db()
    mine = [
        row["id"]
        for row in db.table("notifications")
        .select("id")
        .eq("owner_id", owner_id)
        .in_("id", notification_ids)
        .execute()
        .data
    ]
    for notification_id in mine:
        db.table("notifications").update({"read_at": _now()}).eq("id", notification_id).execute()
    return list_notifications(owner_id)


def _notify_verdict(project: dict, run_id: str, previous: dict | None, result: dict) -> None:
    """Tell the owner what changed, and only what changed.

    A run that concluded the same thing as the one before it is not news, so the only
    notification worth writing is a health change — plus the first time a project is
    found at risk, which is the moment somebody needs to look.
    """
    health = result["health"]
    was = (previous or {}).get("health")
    if was == health:
        return

    severity = {"at_risk": "danger", "watch": "warn"}.get(health, "info")
    blockers = sum(
        1 for finding in result["findings"] if finding.severity in BLOCKER_SEVERITIES
    )
    kind = "blockers_found" if health == "at_risk" and blockers else "health_changed"
    moved = f"{HEALTH_WORDS.get(was, 'Not yet analysed')} → {HEALTH_WORDS[health]}"

    _notify(
        project,
        run_id,
        kind=kind,
        severity=severity,
        title=f"{project['name']} is now {HEALTH_WORDS[health]}",
        body=result["summary"] or moved,
    )


def _notify(project: dict, run_id: str, kind: str, severity: str, title: str, body: str) -> None:
    """One notification. Never allowed to fail a run — the analysis already succeeded,
    and losing the alert is better than losing the result it was about."""
    try:
        get_db().table("notifications").insert(
            {
                "project_id": project["id"],
                "owner_id": project["owner_id"],
                "run_id": run_id,
                "kind": kind,
                "severity": severity,
                "title": title,
                "body": body[:1000],
            }
        ).execute()
    except Exception:  # noqa: BLE001
        logger.exception("Could not write notification for project %s", project["id"])


def _as_datetime(value: str | datetime) -> datetime:
    """Supabase hands timestamps back as ISO strings; the fake database keeps them as
    whatever was written. Either way the comparison needs an aware datetime."""
    if isinstance(value, datetime):
        moment = value
    else:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


# --- approval and execution --------------------------------------------------


def approve_actions(project_id: str, owner_id: str, action_ids: list[str]) -> list[dict]:
    """Approve the actions the user picked, then run them one after another.

    Approval and execution are a single request on purpose: no queue, no worker,
    no polling. Each action still moves through its real states in the database —
    approved, executing, then completed or failed — so a dashboard reading the
    table while this runs sees the truth, and an action interrupted mid-flight is
    left as "executing" instead of silently going back to pending.

    Ids that are not pending — already run, already approved, or belonging to
    another project — are skipped rather than run twice.
    """
    _ensure_owned(project_id, owner_id)
    return [_execute(action) for action in _approve(project_id, action_ids)]


# --- connected apps ------------------------------------------------------------
#
# Each project connects its own Slack/Linear/GitHub credential from the frontend.
# The token is verified against the real API before it is ever stored, so "connected"
# always means "we checked this token actually works", never just "something was typed
# into a field". Gmail/Drive/Calendar are not here yet — see TOKEN_INTEGRATIONS.


def list_integration_status(project_id: str, owner_id: str) -> dict[str, dict]:
    """provider -> {metadata, connected_at} for every token-based app this project has
    connected. A provider missing from the result has no row — it is not connected."""
    _ensure_owned(project_id, owner_id)
    db = get_db()
    rows = (
        db.table("integrations")
        .select("provider,metadata,connected_at")
        .eq("project_id", project_id)
        .execute()
        .data
    )
    return {row["provider"]: row for row in rows}


def _connected_for(project_ids: list[str]) -> dict[str, list[str]]:
    """Which apps each project can actually reach, in one query for all of them.

    Every app here is this project's own: a pasted Slack/Linear/GitHub token, or the
    Google grant a user gave from the Connections page. One 'google' row means all
    three Google apps, since they are three APIs behind a single consent.
    """
    if not project_ids:
        return {}

    rows = (
        get_db()
        .table("integrations")
        .select("project_id,provider")
        .in_("project_id", project_ids)
        .execute()
        .data
    )

    connected: dict[str, list[str]] = {project_id: [] for project_id in project_ids}
    for row in rows:
        # 'google' is how the grant is stored, but it is not an app the agent
        # investigates — it stands for the three that are.
        if row["provider"] == "google":
            connected[row["project_id"]].extend(GOOGLE_INTEGRATIONS)
        else:
            connected[row["project_id"]].append(row["provider"])
    return connected


def connect_integration(
    project_id: str, owner_id: str, provider: str, token: str, extra: dict | None = None
) -> dict:
    """Verify the token against the real app, then store it encrypted for this project.

    A bad token fails right here, on whatever error the app itself gave — never saved,
    never discovered later as a mysterious empty investigation.
    """
    _ensure_owned(project_id, owner_id)
    integration = TOKEN_INTEGRATIONS[provider]
    verified = integration.verify_token(token, **(extra or {}))

    db = get_db()
    row = {
        "project_id": project_id,
        "provider": provider,
        "encrypted_token": security.encrypt(token),
        "metadata": {**(extra or {}), **verified},
        "connected_by": owner_id,
        "connected_at": _now(),
    }
    return (
        db.table("integrations")
        .upsert(row, on_conflict="project_id,provider")
        .execute()
        .data[0]
    )


def connect_google(project_id: str, owner_id: str, code: str) -> dict:
    """Finish the Google OAuth round trip: trade the code for a refresh token and store
    it encrypted for this project.

    One row, provider 'google', serves Gmail, Drive and Calendar — a single consent
    covers all three, and storing it three times would mean three things to revoke.
    """
    _ensure_owned(project_id, owner_id)
    granted = google_auth.exchange_code(code)

    db = get_db()
    row = {
        "project_id": project_id,
        "provider": "google",
        "encrypted_token": security.encrypt(granted["refresh_token"]),
        "metadata": {"email": granted["email"], "apps": list(GOOGLE_INTEGRATIONS)},
        "connected_by": owner_id,
        "connected_at": _now(),
    }
    saved = db.table("integrations").upsert(row, on_conflict="project_id,provider").execute().data[0]
    # A reconnect must not keep serving access tokens minted from the old grant.
    google_auth.forget(project_id)
    return saved


def disconnect_integration(project_id: str, owner_id: str, provider: str) -> None:
    _ensure_owned(project_id, owner_id)
    db = get_db()
    db.table("integrations").delete().eq("project_id", project_id).eq("provider", provider).execute()
    if provider == "google":
        # Otherwise a cached access token keeps working for up to an hour after the
        # user believes they disconnected.
        google_auth.forget(project_id)


def get_integration_credential(project_id: str, provider: str) -> dict | None:
    """This project's decrypted token and any extra fields (repo, channel_ids) for
    `provider`, or None if it was never connected.

    No ownership check here: this is called from inside collect_evidence/execute_action,
    deep in the agent workflow, where project_id already came from a request that an API
    route checked ownership on.
    """
    db = get_db()
    rows = (
        db.table("integrations")
        .select("encrypted_token,metadata")
        .eq("project_id", project_id)
        .eq("provider", provider)
        .execute()
        .data
    )
    if not rows or not rows[0]["encrypted_token"]:
        return None

    row = rows[0]
    return {"token": security.decrypt(row["encrypted_token"]), **row["metadata"]}


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


def _ensure_owned(project_id: str, owner_id: str) -> dict:
    """The project, if `owner_id` owns it. An unknown id and someone else's project both
    come back as the same 404 — an id that isn't yours must not confirm that it exists."""
    db = get_db()
    rows = db.table("projects").select("*").eq("id", project_id).execute().data
    if not rows or rows[0]["owner_id"] != owner_id:
        raise ProjectNotFound(f"No project with id {project_id}")
    return rows[0]


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
        project_id=row["project_id"],
        integration=row["integration"],
        type=row["type"],
        description=row["description"],
        target=row.get("target", ""),
        reason=row.get("reason", ""),
        params=row.get("params") or {},
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
