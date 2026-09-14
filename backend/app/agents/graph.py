"""The single LangGraph workflow.

    supervisor
        ├── communication  (Slack, Gmail)
        ├── engineering    (GitHub)
        ├── delivery       (Linear, Jira, Asana, Trello)
        └── requirements   (Drive, Notion, Calendar)
                ↓
              risk

The four investigation agents run in parallel and each append to state["evidence"]
and state["agent_activity"]. Risk waits for all of them before it runs, and produces
the findings, the project state and the recovery plan in a single model call — see
`risk.py` for why that is one call and not two.

`engineering` and `delivery` are deliberately separate: what a team built and what its
plan says are different questions, and the gap between them is most of what this
product exists to find.
"""

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agents import (
    communication,
    delivery,
    engineering,
    requirements,
    risk,
    supervisor,
)
from app.agents.state import AgentState

INVESTIGATORS = {
    "communication": communication.run,
    "engineering": engineering.run,
    "delivery": delivery.run,
    "requirements": requirements.run,
}


@lru_cache
def get_analysis_graph():
    graph = StateGraph(AgentState)

    graph.add_node("supervisor", supervisor.run)
    graph.add_node("risk", risk.run)
    for name, node in INVESTIGATORS.items():
        graph.add_node(name, node)

    graph.add_edge(START, "supervisor")
    for name in INVESTIGATORS:
        graph.add_edge("supervisor", name)
        graph.add_edge(name, "risk")
    graph.add_edge("risk", END)

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
            "health": "on_track",
            "summary": "",
            "progress": None,
            "plan": [],
            "agent_activity": [],
        }
    )
