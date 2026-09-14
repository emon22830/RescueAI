"""Project endpoints."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth import CurrentUser, get_current_user
from app.agents.state import Source
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
    # How often the agent re-analyses this project on its own; null means manual only.
    sync_interval_minutes: int | None = None
    last_synced_at: datetime | None = None
    summary: ProjectSummary
    # The apps this project can reach right now, so a card can show its connectors
    # without a request per project.
    connected: list[Source] = []


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(body: CreateProjectRequest, user: CurrentUser = Depends(get_current_user)) -> dict:
    return service.create_project(body.name, body.goal, user.id)


@router.get("", response_model=list[ProjectResponse])
def list_projects(user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    return service.list_projects(user.id)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, user: CurrentUser = Depends(get_current_user)) -> dict:
    return service.get_project(project_id, user.id)


class SetScheduleRequest(BaseModel):
    """Minutes between automatic re-analyses, or null to turn the schedule off."""

    sync_interval_minutes: int | None = Field(default=None, ge=service.MIN_SYNC_MINUTES)


@router.put("/{project_id}/schedule", response_model=ProjectResponse)
def set_schedule(
    project_id: str, body: SetScheduleRequest, user: CurrentUser = Depends(get_current_user)
) -> dict:
    """Turn continuous monitoring on or off for this project."""
    return service.set_schedule(project_id, user.id, body.sync_interval_minutes)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str, user: CurrentUser = Depends(get_current_user)) -> None:
    service.delete_project(project_id, user.id)
