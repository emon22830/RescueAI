"""Cross-references all collected evidence and writes the project state.

Two things come out of one pass over the evidence, because they are one judgement:
the blockers and risks, and where the project actually stands — health, a short
summary, and progress when the evidence supports a number.

The LLM cites evidence by index so findings always point at real items
instead of a paraphrase the model invented.
"""

from pydantic import BaseModel, Field

from app.agents.state import AgentState, Evidence, Finding, Severity, activity, health_for
from app.ai import llm

SYSTEM = """You are a project analyst. You are given evidence collected from a team's
Slack, Gmail, Google Drive, Linear, GitHub and Calendar.

Find the blockers and risks that put the project goal at risk. A finding is only useful
if it connects evidence from more than one source — anyone can read a single task list.
Look for contradictions between sources: a requirement that changed after the work
started, a task still open that someone reported as done, a deadline nothing is moving
toward, a decision made in chat that never reached the tracker.

Rules:
- Cite the index of every piece of evidence that supports a finding.
- Never invent evidence. If the evidence does not support a conclusion, do not make it.
- The description IS your reasoning. Walk from the cited evidence to the conclusion, in
  the order it happened, so a reader can check every step against the evidence itself.
- Severity reflects impact on the goal: critical and high mean the goal is blocked or
  slipping, medium and low mean it is worth watching.
- Confidence reflects how strongly the evidence backs the finding, not how bad it is:
  above 0.8 only when several sources agree and say it plainly, 0.5 to 0.8 when the
  evidence points that way but something is inferred, below 0.5 when it is a suspicion.
  A single ambiguous message is never high confidence.
- Return an empty list if the evidence shows no real problem.

Then state where the project stands:
- summary: two or three sentences a lead could read before a standup. What is actually
  happening, named concretely — the issue, the person, the date. Not a restatement of
  the findings list, and never encouragement.
- progress: percent of the goal completed, 0 to 100, ONLY when the evidence measures it
  — closed versus open issues, milestones shipped, a checklist someone kept. If you
  would be guessing, return null. A number nobody can check is worse than no number."""


class _DraftFinding(BaseModel):
    title: str
    severity: Severity
    confidence: float = Field(ge=0, le=1)
    description: str
    evidence_indexes: list[int]


class _RiskReport(BaseModel):
    findings: list[_DraftFinding]
    summary: str = ""
    progress: int | None = Field(default=None, ge=0, le=100)


def run(state: AgentState) -> dict:
    evidence = state["evidence"]
    if not evidence:
        return {
            "findings": [],
            "health": "on_track",
            "summary": "No evidence was collected, so there is nothing to report yet. "
            "Connect the apps this project runs on and analyze again.",
            "progress": None,
            "agent_activity": [activity("risk", "ok", "No evidence collected — nothing to analyze")],
        }

    report = llm.ask_for(_RiskReport, SYSTEM, _build_prompt(state, evidence))
    findings = [_to_finding(draft, evidence) for draft in report.findings]
    health = health_for([finding.severity for finding in findings])

    return {
        "findings": findings,
        "health": health,
        "summary": report.summary,
        "progress": report.progress,
        "agent_activity": [
            activity(
                "risk",
                "ok",
                f"{len(findings)} findings from {len(evidence)} pieces of evidence — {health}",
            )
        ],
    }


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
