"""What the agent concluded while the user was away."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import CurrentUser, get_current_user
from app.projects import service

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationResponse(BaseModel):
    id: str
    project_id: str
    run_id: str | None = None
    kind: Literal["health_changed", "blockers_found", "run_failed"]
    severity: Literal["info", "warn", "danger"]
    title: str
    body: str = ""
    read_at: datetime | None = None
    created_at: datetime


class MarkReadRequest(BaseModel):
    notification_ids: list[str]


@router.get("", response_model=list[NotificationResponse])
def list_notifications(
    unread_only: bool = False, user: CurrentUser = Depends(get_current_user)
) -> list[dict]:
    return service.list_notifications(user.id, unread_only=unread_only)


@router.post("/read", response_model=list[NotificationResponse])
def mark_read(
    body: MarkReadRequest, user: CurrentUser = Depends(get_current_user)
) -> list[dict]:
    return service.mark_notifications_read(user.id, body.notification_ids)
