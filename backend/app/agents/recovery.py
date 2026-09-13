"""Turns findings into a concrete recovery plan.

The plan is never executed here — it is saved as pending actions and waits
for the user to approve it.
"""

from pydantic import BaseModel

from app.agents.state import AgentState, Finding, PlannedAction, Source
from app.ai import llm

SYSTEM = """You are a delivery lead writing a recovery plan for a project that is at risk.

Each step must be a single concrete action in one of these tools:
- linear: update_issue (target = issue identifier, value = the change, e.g. a new due date or assignee)
- calendar: create_event (target = attendees, value = the meeting title and purpose)
- gmail: send_email (target = recipient, value = what to tell them)

Rules:
- Every step must address a finding you were given. No generic project advice.
- Order the steps so the most urgent blocker is unblocked first.
- Keep the plan short. Four or five steps is usually enough."""


class _PlanStep(BaseModel):
    integration: Source
    action: str
    description: str
    target: str
    value: str


class _RecoveryPlan(BaseModel):
    steps: list[_PlanStep]


def run(state: AgentState) -> dict:
    findings = state["findings"]
    if not findings:
        return {"plan": []}

    plan = llm.ask_for(_RecoveryPlan, SYSTEM, _build_prompt(state, findings))
    return {"plan": [_to_action(step) for step in plan.steps]}


def _build_prompt(state: AgentState, findings: list[Finding]) -> str:
    lines = [
        f"PROJECT: {state['project_name']}",
        f"GOAL: {state['project_goal']}",
        "",
        "FINDINGS:",
    ]
    for finding in findings:
        lines.append(f"- [{finding.severity.upper()}] {finding.title}")
        lines.append(f"  {finding.description}")
        for item in finding.evidence:
            lines.append(f"  evidence: {item.source} · {item.title}")
    return "\n".join(lines)


def _to_action(step: _PlanStep) -> PlannedAction:
    return PlannedAction(
        integration=step.integration,
        action=step.action,
        description=step.description,
        params={"target": step.target, "value": step.value},
    )
