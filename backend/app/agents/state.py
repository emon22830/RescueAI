"""Shared data shapes: what evidence looks like, what a finding looks like,
and the state LangGraph passes between nodes."""

import operator
from datetime import datetime
from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, Field

Source = Literal["slack", "gmail", "drive", "linear", "github", "calendar"]
Severity = Literal["low", "medium", "high", "critical"]


class Evidence(BaseModel):
    """One normalized fact pulled out of an external app."""

    source: Source
    type: str  # "message", "email", "issue", "pull_request", "document", "event"
    title: str
    content: str
    url: str | None = None
    timestamp: datetime | None = None
    metadata: dict = Field(default_factory=dict)


class Finding(BaseModel):
    """Something the agent concluded, with the evidence that supports it."""

    title: str
    severity: Severity
    confidence: float = Field(ge=0, le=1)
    description: str
    evidence: list[Evidence] = Field(default_factory=list)


class PlannedAction(BaseModel):
    """One step of a recovery plan, executed only after the user approves it."""

    integration: Source
    action: str  # "update_issue", "create_event", "send_email"
    description: str
    params: dict = Field(default_factory=dict)


class AgentState(TypedDict):
    """LangGraph state. `evidence` uses operator.add so the three investigation
    branches can append in parallel without overwriting each other."""

    project_id: str
    project_name: str
    project_goal: str
    evidence: Annotated[list[Evidence], operator.add]
    findings: list[Finding]
    plan: list[PlannedAction]
