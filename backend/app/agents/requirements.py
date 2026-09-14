"""Investigates what was agreed: specs in Drive and Notion, deadlines in Calendar."""

from app.agents import supervisor
from app.agents.state import AgentState
from app.integrations import calendar, drive, notion


def run(state: AgentState) -> dict:
    return supervisor.investigate(
        "requirements",
        state["project_id"],
        state["project_name"],
        {
            "drive": drive.collect_evidence,
            "notion": notion.collect_evidence,
            "calendar": calendar.collect_evidence,
        },
    )
