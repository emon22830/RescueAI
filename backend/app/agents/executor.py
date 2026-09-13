"""Runs approved actions against the real integrations. No LLM involved."""

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


def execute(action: PlannedAction) -> str:
    integration = INTEGRATIONS[action.integration]
    return integration.execute_action(action)
