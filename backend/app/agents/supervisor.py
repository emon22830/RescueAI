"""Starts the investigation. The three investigation agents run after this node."""

from app.agents.state import AgentState


def run(state: AgentState) -> dict:
    return {"findings": [], "plan": []}
