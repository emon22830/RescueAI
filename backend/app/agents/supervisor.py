"""Opens the investigation, and holds the one piece of work the three
investigation agents share: running an integration and recording what it gave back."""

from collections.abc import Callable

from app.agents.state import AgentState, Evidence, activity

Collector = Callable[[str, str], list[Evidence]]

AGENTS = ("communication", "engineering", "requirements")


def run(state: AgentState) -> dict:
    """Nothing is known yet — the project starts on_track and the investigators go out."""
    return {
        "findings": [],
        "plan": [],
        "health": "on_track",
        "agent_activity": [
            activity(
                "supervisor",
                "ok",
                f"Investigating '{state['project_name']}' with {len(AGENTS)} agents: "
                + ", ".join(AGENTS),
            )
        ],
    }


def investigate(
    agent: str, project_id: str, project_name: str, sources: dict[str, Collector]
) -> dict:
    """Collect from each of one agent's apps, logging what each one returned.

    One unreachable app must not throw away the evidence the others already found,
    so a failure becomes a line of activity and the investigation carries on.
    A missing credential is not caught here: it is a ConfigurationError and the
    user deserves the 503 naming the variable.
    """
    evidence: list[Evidence] = []
    log = []

    for name, collect in sources.items():
        try:
            found = collect(project_id, project_name)
        except Exception as error:
            log.append(activity(agent, "failed", f"{name}: {type(error).__name__}: {error}"))
            continue
        evidence += found
        log.append(activity(agent, "ok", f"{name}: {len(found)} items", len(found)))

    return {"evidence": evidence, "agent_activity": log}
