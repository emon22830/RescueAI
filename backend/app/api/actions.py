"""The recovery plan: read the proposed actions, approve the ones to execute."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.state import Source
from app.projects import service

router = APIRouter(prefix="/projects/{project_id}/actions", tags=["actions"])


class ActionResponse(BaseModel):
    id: str
    integration: Source
    action: str
    description: str
    params: dict
    status: Literal["pending", "executed", "failed"]
    result: str | None = None


class ApproveActionsRequest(BaseModel):
    action_ids: list[str]


@router.get("", response_model=list[ActionResponse])
def get_actions(project_id: str) -> list[dict]:
    return service.get_actions(project_id)


@router.post("/approve", response_model=list[ActionResponse])
def approve_actions(project_id: str, body: ApproveActionsRequest) -> list[dict]:
    return service.approve_actions(project_id, body.action_ids)
