"""Running the agent and reading what it found."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel

from app.agents.state import AgentActivity, Evidence, Health, Severity
from app.auth import CurrentUser, get_current_user
from app.projects import service

router = APIRouter(prefix="/projects/{project_id}", tags=["analysis"])


class AgentRunResponse(BaseModel):
    """One pass of the workflow, and the project state it concluded with."""

    id: str
    status: Literal["queued", "running", "completed", "failed"]
    triggered_by: Literal["analyze", "sync", "schedule"] = "analyze"
    started_at: datetime
    completed_at: datetime | None = None
    evidence_count: int | None = None
    finding_count: int | None = None
    health: Health | None = None
    summary: str | None = None
    progress: int | None = None
    activity: list[AgentActivity] = []
    error: str | None = None


class FindingResponse(BaseModel):
    id: str
    title: str
    severity: Severity
    confidence: float
    description: str
    evidence: list[Evidence]
    created_at: datetime


@router.post("/analyze", response_model=AgentRunResponse, status_code=202)
def analyze_project(
    project_id: str,
    background: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Start collecting evidence from every connected app and analyzing it.

    Returns as soon as the run is queued, because the work behind it is six external
    APIs and two LLM calls — far longer than a request should hold the browser. The
    returned run is the handle: poll `/runs` until its status leaves "queued"/"running".
    """
    return _queue(project_id, user.id, background, triggered_by="analyze")


@router.post("/sync", response_model=AgentRunResponse, status_code=202)
def sync_project(
    project_id: str,
    background: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Re-collect from the connected apps and replace the project state with what is true now.

    The work is the same investigation as /analyze — a sync is a fresh collection, not a
    cheaper one — so the difference is only which button the history says was pressed.
    """
    return _queue(project_id, user.id, background, triggered_by="sync")


def _queue(project_id: str, owner_id: str, background: BackgroundTasks, triggered_by: str) -> dict:
    """Write the queued run inside the request — so ownership is checked while there is
    still someone to return 404 to — and hand the work itself to the background."""
    run = service.start_analysis(project_id, owner_id, triggered_by=triggered_by)
    background.add_task(service.run_analysis, project_id, run["id"])
    return run


@router.get("/findings", response_model=list[FindingResponse])
def get_findings(project_id: str, user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    return service.get_findings(project_id, user.id)


@router.get("/runs", response_model=list[AgentRunResponse])
def get_runs(project_id: str, user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    return service.get_runs(project_id, user.id)
