"""The recovery plan: read the proposed actions, approve the ones to execute.

Approving is the only way an action ever reaches an external app, and it is a
plain request: the approved actions run in it and come back with their results.
"""

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.state import ActionStatus, Source
from app.projects import service

router = APIRouter(prefix="/projects/{project_id}/actions", tags=["actions"])


class ActionResponse(BaseModel):
    """One step of the recovery plan and where it has got to."""

    id: str
    integration: Source
    type: str  # "update_issue", "assign_task", "create_event", "send_email"
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


@router.get("", response_model=list[ActionResponse])
def get_actions(project_id: str) -> list[dict]:
    return service.get_actions(project_id)


@router.post("/approve", response_model=list[ActionResponse])
def approve_actions(project_id: str, body: ApproveActionsRequest) -> list[dict]:
    """Approve the given actions and execute them. Anything not pending is skipped."""
    return service.approve_actions(project_id, body.action_ids)
