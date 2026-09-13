"""Investigates what was agreed: Google Drive documents and Calendar deadlines."""

from app.agents.state import AgentState
from app.integrations import calendar, drive


def run(state: AgentState) -> dict:
    project_name = state["project_name"]
    evidence = drive.collect_evidence(project_name) + calendar.collect_evidence(project_name)
    return {"evidence": evidence}
