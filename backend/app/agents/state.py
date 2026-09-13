"""Shared data shapes: what evidence looks like, what a finding looks like,
and the state LangGraph passes between nodes."""

import operator
from datetime import UTC, datetime
from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, Field

Source = Literal["slack", "gmail", "drive", "linear", "github", "calendar"]
Severity = Literal["low", "medium", "high", "critical"]
Health = Literal["on_track", "watch", "at_risk"]

# An action's life: proposed by the agent, approved by a human, run, then done or not.
# Nothing reaches an external app in any state but "approved".
ActionStatus = Literal["pending", "approved", "executing", "completed", "failed"]

BLOCKER_SEVERITIES = ("high", "critical")


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
    """One step of a recovery plan, executed only after the user approves it.

    `target` is what the step acts on — the Linear issue, the meeting's attendees,
    the email's recipient — and `params` carries whatever else that action type
    needs: `value` (the change, the body, the purpose) plus extras like `due_date`,
    `subject` or `start`.

    `project_id` says whose stored credential to execute it with — required because
    every project can connect a different Slack/Linear/GitHub token.
    """

    project_id: str = ""
    integration: Source
    type: str  # "update_issue", "assign_task", "update_due_date", "create_event", "send_email"
    description: str
    target: str = ""
    reason: str = ""  # the finding this step is meant to fix
    params: dict = Field(default_factory=dict)


class AgentActivity(BaseModel):
    """One line of the agent's own log: which node ran and what it came back with.

    This is how a user sees that Gmail returned nothing because it is not connected,
    rather than silently wondering why no email shows up in the findings.
    """

    agent: str
    status: Literal["ok", "failed"]
    detail: str
    evidence_count: int = 0
    at: datetime = Field(default_factory=lambda: datetime.now(UTC))


def activity(agent: str, status: str, detail: str, evidence_count: int = 0) -> AgentActivity:
    return AgentActivity(agent=agent, status=status, detail=detail, evidence_count=evidence_count)


def health_for(severities: list[str]) -> Health:
    """One rule for project health, used by the risk node and by the project summary."""
    if any(severity in BLOCKER_SEVERITIES for severity in severities):
        return "at_risk"
    if severities:
        return "watch"
    return "on_track"


class AgentState(TypedDict):
    """LangGraph state. `evidence` and `agent_activity` use operator.add so the three
    investigation branches can append in parallel without overwriting each other.

    `health`, `summary` and `progress` together are the project state the risk node
    writes: where the project stands, said once, in the agent's own words.
    """

    project_id: str
    project_name: str
    project_goal: str
    evidence: Annotated[list[Evidence], operator.add]
    findings: list[Finding]
    health: Health
    summary: str
    progress: int | None
    plan: list[PlannedAction]
    agent_activity: Annotated[list[AgentActivity], operator.add]
