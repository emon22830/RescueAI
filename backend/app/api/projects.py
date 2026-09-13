"""Project endpoints."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.projects import service

router = APIRouter(prefix="/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    goal: str = Field(min_length=1, max_length=500)


class ProjectSummary(BaseModel):
    """What the dashboard shows at a glance, from the latest completed run.

    `summary` and `progress` are the agent's own words and number, stored on that run.
    `progress` is null whenever the evidence did not measure it.
    """

    health: Literal["on_track", "watch", "at_risk"]
    summary: str = ""
    progress: int | None = None
    blockers: int
    risks: int
    findings: int


class ProjectResponse(BaseModel):
    id: str
    name: str
    goal: str
    created_at: datetime
    summary: ProjectSummary


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(body: CreateProjectRequest) -> dict:
    return service.create_project(body.name, body.goal)


@router.get("", response_model=list[ProjectResponse])
def list_projects() -> list[dict]:
    return service.list_projects()


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str) -> dict:
    return service.get_project(project_id)
