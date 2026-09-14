"""The plan half of the analysis: what to do about what the risk agent found.

Not a node. This was a second LLM call until the free-tier quota made the cost of that
visible — it re-sent the project, the findings and every cited evidence title to ask a
question the model had the evidence for the first time. Naming a blocker and saying how
to unblock it is one judgement anyway, so `risk` now asks for both in one request.

What stays here is the half of that request this file owns: the menu of what can
actually be run, the rules for choosing from it, the shape a step comes back in, and
the mapping from a step to a `PlannedAction`.

The plan is never executed here. It is saved as pending actions and waits for the user
to approve it.
"""

from pydantic import BaseModel

from app.agents import executor
from app.agents.state import Finding, PlannedAction, Source


def _action_menu() -> str:
    """The step types, written from `executor.ACTION_TYPES` rather than kept in step with
    it by hand. A type the executor cannot run must never appear in this prompt."""
    width = max(len(action.type) for action in executor.ACTION_TYPES)
    return "\n".join(
        f"- {action.integration} / {action.type.ljust(width)}  {action.guidance}"
        for action in executor.ACTION_TYPES
    )


PLAN_RULES = f"""Then write the recovery plan: the steps that address what you just found.

Each step must be a single concrete action of one of these types:
{_action_menu()}

Rules:
- Every step must address exactly one of the findings you wrote above. Cite its index in
  `finding_index`. No generic project advice, and no step for a problem nobody found.
- Return no steps at all when you found nothing. An empty plan is a valid answer, and a
  plan for a problem you invented is worse than no plan.
- The description says what will happen and why that unblocks the finding, naming the
  people, issues and dates from the evidence rather than speaking in general terms.
- Order the steps so the most urgent blocker is unblocked first.
- Use the app the work actually lives in: the issue tracker for work, Slack for telling
  people, Calendar for a decision that needs the room, email for someone outside the team.
- Set `params` only for the optional extras a step's own line names, as a list of
  {{"name": ..., "value": ...}} pairs. Leave it empty otherwise; never invent a
  parameter that is not offered.
- Keep the plan short. Four or five steps is usually enough."""


class PlanParam(BaseModel):
    """One optional extra a step needs — team, assignee, due_date, subject, start.

    A list of name/value pairs rather than a dict. A dict of arbitrary keys becomes an
    open-ended map in the generated JSON schema, and the Gemini Developer API rejects
    any schema containing one — a failure that appears only on a real call, never in a
    test with a stubbed model. `test_llm_schemas.py` is the guard for that.
    """

    name: str
    value: str


class PlanStep(BaseModel):
    integration: Source
    type: str
    description: str
    target: str
    value: str
    params: list[PlanParam] = []
    finding_index: int


def to_action(step: PlanStep, findings: list[Finding], project_id: str) -> PlannedAction:
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
