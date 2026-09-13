"""Investigates what the team built: GitHub and Linear."""

from app.agents import supervisor
from app.agents.state import AgentState
from app.integrations import github, linear


def run(state: AgentState) -> dict:
    return supervisor.investigate(
        "engineering",
        state["project_id"],
        state["project_name"],
        {"github": github.collect_evidence, "linear": linear.collect_evidence},
    )
