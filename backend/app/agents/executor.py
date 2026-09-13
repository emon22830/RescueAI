"""Runs approved actions against the real integrations. No LLM involved.

This is the last code that runs before we touch somebody else's workspace, so the
approval check lives here rather than only in the caller: an action that is not
`approved` never reaches an integration.
"""

from app.agents.state import PlannedAction
from app.integrations import calendar, drive, github, gmail, linear, slack

INTEGRATIONS = {
    "slack": slack,
    "gmail": gmail,
    "drive": drive,
    "linear": linear,
    "github": github,
    "calendar": calendar,
}


class NotApproved(RuntimeError):
    """Someone tried to execute an action a human has not approved."""


def execute(action: PlannedAction, status: str) -> str:
    """Perform one approved action and return the integration's own result line.

    `status` is the action's status in the database at the moment of execution.
    """
    if status != "approved":
        raise NotApproved(f"Action is '{status}', not approved — nothing was executed")

    integration = INTEGRATIONS[action.integration]
    return integration.execute_action(action)
