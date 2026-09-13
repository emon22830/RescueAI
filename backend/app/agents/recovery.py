"""Turns findings into a concrete recovery plan.

The plan is never executed here — it is saved as pending actions and waits
for the user to approve it.
"""

from pydantic import BaseModel

from app.agents.state import AgentState, Finding, PlannedAction, Source, activity
from app.ai import llm

SYSTEM = """You are a delivery lead writing a recovery plan for a project that is at risk.

Each step must be a single concrete action of one of these types:
- linear / update_issue      target = issue identifier (PAY-124), value = the change to record
- linear / assign_task       target = issue identifier, value = the person's name or email
- linear / update_due_date   target = issue identifier, value = the new date as YYYY-MM-DD
- calendar / create_event    target = attendee emails, comma separated, value = title and purpose
- gmail / send_email         target = the recipient's email address, value = what to tell them

Rules:
- Every step must address exactly one of the findings you were given. Cite it by index.
  No generic project advice, and no step for a problem nobody found.
- The description says what will happen and why that unblocks the finding, naming the
  people, issues and dates from the evidence rather than speaking in general terms.
- Order the steps so the most urgent blocker is unblocked first.
- Keep the plan short. Four or five steps is usually enough."""


class _PlanStep(BaseModel):
    integration: Source
    type: str
    description: str
    target: str
    value: str
    finding_index: int


class _RecoveryPlan(BaseModel):
    steps: list[_PlanStep]


def run(state: AgentState) -> dict:
    findings = state["findings"]
    if not findings:
        return {
            "plan": [],
            "agent_activity": [activity("recovery", "ok", "No findings — no plan needed")],
        }

    plan = llm.ask_for(_RecoveryPlan, SYSTEM, _build_prompt(state, findings))
    actions = [_to_action(step, findings, state["project_id"]) for step in plan.steps]

    return {
        "plan": actions,
        "agent_activity": [
            activity("recovery", "ok", f"{len(actions)} actions proposed, awaiting approval")
        ],
    }


def _build_prompt(state: AgentState, findings: list[Finding]) -> str:
    lines = [
        f"PROJECT: {state['project_name']}",
        f"GOAL: {state['project_goal']}",
        "",
        "FINDINGS:",
    ]
    for index, finding in enumerate(findings):
        lines.append(f"[{index}] [{finding.severity.upper()}] {finding.title}")
        lines.append(f"    {finding.description}")
        for item in finding.evidence:
            lines.append(f"    evidence: {item.source} · {item.title}")
    return "\n".join(lines)


def _to_action(step: _PlanStep, findings: list[Finding], project_id: str) -> PlannedAction:
    """The reason is the finding's own title, never the model's retelling of it."""
    index = step.finding_index
    reason = findings[index].title if 0 <= index < len(findings) else ""
    return PlannedAction(
        project_id=project_id,
        integration=step.integration,
        type=step.type,
        description=step.description,
        target=step.target,
        reason=reason,
        params={"value": step.value},
    )
