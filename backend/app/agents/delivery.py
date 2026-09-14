"""Investigates what the plan says: the task trackers.

Separate from `engineering` on purpose. What a team committed is a different question
from what it said it would do, and the gap between the two is most of what this product
exists to find — so the two are collected by different agents and logged separately.

A project connects whichever tracker it actually uses; the rest return [].
"""

from app.agents import supervisor
from app.agents.state import AgentState
from app.integrations import asana, jira, linear, trello


def run(state: AgentState) -> dict:
    return supervisor.investigate(
        "delivery",
        state["project_id"],
        state["project_name"],
        {
            "linear": linear.collect_evidence,
            "jira": jira.collect_evidence,
            "asana": asana.collect_evidence,
            "trello": trello.collect_evidence,
        },
    )
