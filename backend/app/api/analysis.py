"""Running the agent and reading what it found."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.state import Evidence, Severity
from app.projects import service

router = APIRouter(prefix="/projects/{project_id}", tags=["analysis"])


class AgentRunResponse(BaseModel):
    id: str
    status: Literal["running", "completed", "failed"]
    started_at: datetime
    completed_at: datetime | None = None
    evidence_count: int | None = None
    finding_count: int | None = None
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
    return service.analyze_project(project_id)


@router.post("/sync", response_model=AgentRunResponse)
def sync_project(project_id: str) -> dict:
    """Same investigation, run again to pick up what changed in the connected apps."""
    return service.analyze_project(project_id)


@router.get("/findings", response_model=list[FindingResponse])
def get_findings(project_id: str) -> list[dict]:
    return service.get_findings(project_id)


@router.get("/runs", response_model=list[AgentRunResponse])
def get_runs(project_id: str) -> list[dict]:
    return service.get_runs(project_id)
