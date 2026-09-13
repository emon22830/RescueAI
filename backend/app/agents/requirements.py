"""Investigates what was agreed: Google Drive documents and Calendar deadlines."""

from app.agents import supervisor
from app.agents.state import AgentState
from app.integrations import calendar, drive


def run(state: AgentState) -> dict:
    return supervisor.investigate(
        "requirements",
        state["project_id"],
        state["project_name"],
        {"drive": drive.collect_evidence, "calendar": calendar.collect_evidence},
    )
