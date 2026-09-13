"""Investigates what the team built: GitHub and Linear."""

from app.agents.state import AgentState
from app.integrations import github, linear


def run(state: AgentState) -> dict:
    project_name = state["project_name"]
    evidence = github.collect_evidence(project_name) + linear.collect_evidence(project_name)
    return {"evidence": evidence}
