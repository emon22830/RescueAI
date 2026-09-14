"""Actions: the recovery plan the agent proposed, and the ones a user takes directly.

Approving is the only way an action ever reaches an external app, and it is a plain
request: the approved actions run in it and come back with their results. An action a
user writes here is approved by the writing of it — same row, same states, same guard.
"""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.agents.executor import Verb
from app.agents.state import ActionStatus, Source
from app.auth import CurrentUser, get_current_user
from app.projects import service

router = APIRouter(prefix="/projects/{project_id}/actions", tags=["actions"])


class ActionResponse(BaseModel):
    """One step of the recovery plan and where it has got to."""

    id: str
    integration: Source
    type: str  # one of executor.ACTION_TYPES — see GET /actions/types
    # "agent" = proposed in a plan then approved. "user" = written at the dashboard.
    origin: Literal["agent", "user"] = "agent"
    description: str
    target: str = ""  # the issue, the attendees, the recipient
    reason: str = ""  # the finding this action is meant to fix
    params: dict = {}
    status: ActionStatus
    result: str | None = None  # what the app said back, or why it failed
    approved_at: datetime | None = None
    executed_at: datetime | None = None


class ApproveActionsRequest(BaseModel):
    action_ids: list[str]


class ActionTypeResponse(BaseModel):
    """One thing this project can be asked to do, and what its two fields mean.

    The dashboard builds its composer from these rather than hardcoding a list that
    would drift from what the executor can actually run.
    """

    integration: Source
    type: str
    verb: Verb  # add · update · delegate · close · message
    label: str
    target_label: str
    value_label: str


class CreateActionRequest(BaseModel):
    """An action a person is taking themselves, not one the agent proposed."""

    integration: Source
    type: str = Field(min_length=1, max_length=60)
    target: str = Field(min_length=1, max_length=500)
    value: str = Field(default="", max_length=8000)
    description: str = Field(default="", max_length=500)
    params: dict[str, str] = {}


@router.get("", response_model=list[ActionResponse])
def get_actions(project_id: str, user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    return service.get_actions(project_id, user.id)


@router.get("/types", response_model=list[ActionTypeResponse])
def get_action_types(project_id: str, user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    """What this project can be asked to do, limited to the apps it has connected."""
    return service.action_types(project_id, user.id)


@router.post("", response_model=ActionResponse, status_code=201)
def create_action(
    project_id: str, body: CreateActionRequest, user: CurrentUser = Depends(get_current_user)
) -> dict:
    """Take one action against a connected app, straight from the dashboard.

    It runs in this request and comes back with its result, the same way approving a
    proposed action does.
    """
    return service.create_action(
        project_id=project_id,
        owner_id=user.id,
        integration=body.integration,
        type=body.type,
        target=body.target,
        value=body.value,
        description=body.description,
        params=body.params,
    )


@router.post("/approve", response_model=list[ActionResponse])
def approve_actions(
    project_id: str, body: ApproveActionsRequest, user: CurrentUser = Depends(get_current_user)
) -> list[dict]:
    """Approve the given actions and execute them. Anything not pending is skipped."""
    return service.approve_actions(project_id, user.id, body.action_ids)
