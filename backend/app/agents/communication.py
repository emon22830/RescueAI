"""Investigates what people said: Slack and Gmail."""

from app.agents.state import AgentState
from app.integrations import gmail, slack


def run(state: AgentState) -> dict:
    project_name = state["project_name"]
    evidence = slack.collect_evidence(project_name) + gmail.collect_evidence(project_name)
    return {"evidence": evidence}
