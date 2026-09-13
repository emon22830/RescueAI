"""Cross-references all collected evidence and names the blockers and risks.

The LLM cites evidence by index so findings always point at real items
instead of a paraphrase the model invented.
"""

from pydantic import BaseModel, Field

from app.agents.state import AgentState, Evidence, Finding, Severity
from app.ai import llm

SYSTEM = """You are a project analyst. You are given evidence collected from a team's
Slack, Gmail, Google Drive, Linear, GitHub and Calendar.

Find the blockers and risks that put the project goal at risk. A finding is only useful
if it connects evidence from more than one source — anyone can read a single task list.

Rules:
- Cite the index of every piece of evidence that supports a finding.
- Never invent evidence. If the evidence does not support a conclusion, do not make it.
- Severity reflects impact on the goal. Confidence reflects how strongly the evidence backs it.
- Return an empty list if the evidence shows no real problem."""


class _DraftFinding(BaseModel):
    title: str
    severity: Severity
    confidence: float = Field(ge=0, le=1)
    description: str
    evidence_indexes: list[int]


class _RiskReport(BaseModel):
    findings: list[_DraftFinding]


def run(state: AgentState) -> dict:
    evidence = state["evidence"]
    if not evidence:
        return {"findings": []}

    report = llm.ask_for(_RiskReport, SYSTEM, _build_prompt(state, evidence))
    return {"findings": [_to_finding(draft, evidence) for draft in report.findings]}


def _build_prompt(state: AgentState, evidence: list[Evidence]) -> str:
    lines = [
        f"PROJECT: {state['project_name']}",
        f"GOAL: {state['project_goal']}",
        "",
        "EVIDENCE:",
    ]
    for index, item in enumerate(evidence):
        when = item.timestamp.date().isoformat() if item.timestamp else "unknown date"
        lines.append(f"[{index}] {item.source} · {item.type} · {when} · {item.title}")
        lines.append(f"    {item.content}")
    return "\n".join(lines)


def _to_finding(draft: _DraftFinding, evidence: list[Evidence]) -> Finding:
    cited = [evidence[i] for i in draft.evidence_indexes if 0 <= i < len(evidence)]
    return Finding(
        title=draft.title,
        severity=draft.severity,
        confidence=draft.confidence,
        description=draft.description,
        evidence=cited,
    )
