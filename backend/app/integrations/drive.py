"""Google Drive. Reads project evidence; write actions live in execute_action()."""

from app.agents.state import Evidence, PlannedAction


def collect_evidence(project_name: str) -> list[Evidence]:
    """Search Google Drive for anything about this project and normalize it to Evidence.

    Not implemented yet — see README "What to implement next".
    """
    return []


def execute_action(action: PlannedAction) -> str:
    """Perform one approved action and return a short human-readable result."""
    raise NotImplementedError(f"Google Drive action not implemented: {action.action}")
