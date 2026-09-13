"""The single LangGraph workflow.

    supervisor
        ├── communication  (Slack, Gmail)
        ├── engineering    (GitHub, Linear)
        └── requirements   (Drive, Calendar)
                ↓
              risk  ──►  recovery

The three investigation agents run in parallel and each append to state["evidence"].
Risk waits for all three before it runs.
"""

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agents import communication, engineering, recovery, requirements, risk, supervisor
from app.agents.state import AgentState

INVESTIGATORS = {
    "communication": communication.run,
    "engineering": engineering.run,
    "requirements": requirements.run,
}


@lru_cache
def get_analysis_graph():
    graph = StateGraph(AgentState)

    graph.add_node("supervisor", supervisor.run)
    graph.add_node("risk", risk.run)
    graph.add_node("recovery", recovery.run)
    for name, node in INVESTIGATORS.items():
        graph.add_node(name, node)

    graph.add_edge(START, "supervisor")
    for name in INVESTIGATORS:
        graph.add_edge("supervisor", name)
        graph.add_edge(name, "risk")
    graph.add_edge("risk", "recovery")
    graph.add_edge("recovery", END)

    return graph.compile()


def analyze(project_id: str, name: str, goal: str) -> AgentState:
    """Run the full investigation for one project."""
    return get_analysis_graph().invoke(
        {
            "project_id": project_id,
            "project_name": name,
            "project_goal": goal,
            "evidence": [],
            "findings": [],
            "plan": [],
        }
    )
