"""Investigates what people said: Slack and Gmail."""

from app.agents import supervisor
from app.agents.state import AgentState
from app.integrations import gmail, slack


def run(state: AgentState) -> dict:
    return supervisor.investigate(
        "communication",
        state["project_name"],
        {"slack": slack.collect_evidence, "gmail": gmail.collect_evidence},
    )
