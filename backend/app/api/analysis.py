"""Running the agent and reading what it found."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.state import AgentActivity, Evidence, Health, Severity
from app.projects import service

router = APIRouter(prefix="/projects/{project_id}", tags=["analysis"])


class AgentRunResponse(BaseModel):
    """One pass of the workflow, and the project state it concluded with."""

    id: str
    status: Literal["running", "completed", "failed"]
    triggered_by: Literal["analyze", "sync"] = "analyze"
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


@router.post("/analyze", response_model=AgentRunResponse)
def analyze_project(project_id: str) -> dict:
    """Collect evidence from every connected app, analyze it, and save the result."""
    return service.analyze_project(project_id, triggered_by="analyze")


@router.post("/sync", response_model=AgentRunResponse)
def sync_project(project_id: str) -> dict:
    """Re-collect from the connected apps and replace the project state with what is true now.

    The work is the same investigation as /analyze — a sync is a fresh collection, not a
    cheaper one — so the difference is only which button the history says was pressed.
    """
    return service.analyze_project(project_id, triggered_by="sync")


@router.get("/findings", response_model=list[FindingResponse])
def get_findings(project_id: str) -> list[dict]:
    return service.get_findings(project_id)


@router.get("/runs", response_model=list[AgentRunResponse])
def get_runs(project_id: str) -> list[dict]:
    return service.get_runs(project_id)
