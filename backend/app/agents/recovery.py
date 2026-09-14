"""Turns findings into a concrete recovery plan.

The plan is never executed here — it is saved as pending actions and waits
for the user to approve it.
"""

from pydantic import BaseModel

from app.agents import executor
from app.agents.state import AgentState, Finding, PlannedAction, Source, activity
from app.ai import llm


def _action_menu() -> str:
    """The step types, written from `executor.ACTION_TYPES` rather than kept in step with
    it by hand. A type the executor cannot run must never appear in this prompt."""
    width = max(len(action.type) for action in executor.ACTION_TYPES)
    return "\n".join(
        f"- {action.integration} / {action.type.ljust(width)}  {action.guidance}"
        for action in executor.ACTION_TYPES
    )


SYSTEM = f"""You are a delivery lead writing a recovery plan for a project that is at risk.

Each step must be a single concrete action of one of these types:
{_action_menu()}

Rules:
- Every step must address exactly one of the findings you were given. Cite it by index.
  No generic project advice, and no step for a problem nobody found.
- The description says what will happen and why that unblocks the finding, naming the
  people, issues and dates from the evidence rather than speaking in general terms.
- Order the steps so the most urgent blocker is unblocked first.
- Use the app the work actually lives in: the issue tracker for work, Slack for telling
  people, Calendar for a decision that needs the room, email for someone outside the team.
- Set `params` only for the optional extras a step's own line names, as a list of
  {{"name": ..., "value": ...}} pairs. Leave it empty otherwise; never invent a
  parameter that is not offered.
- Keep the plan short. Four or five steps is usually enough."""


class _PlanParam(BaseModel):
    """One optional extra a step needs — team, assignee, due_date, subject, start.

    A list of name/value pairs rather than a dict. A dict of arbitrary keys becomes an
    open-ended map in the generated JSON schema, and the Gemini Developer API rejects
    any schema containing one — a failure that appears only on a real call, never in a
    test with a stubbed model. `test_llm_schemas.py` is the guard for that.
    """

    name: str
    value: str


class _PlanStep(BaseModel):
    integration: Source
    type: str
    description: str
    target: str
    value: str
    params: list[_PlanParam] = []
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
        # `value` is written last so a model that also named it in params cannot
        # shadow the field the integrations actually read.
        params={**{param.name: param.value for param in step.params}, "value": step.value},
    )
