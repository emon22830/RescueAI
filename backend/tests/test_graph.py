"""The graph must carry evidence from the investigators all the way to the plan."""

from datetime import UTC, datetime

import pytest

from app.agents import executor, risk, supervisor
from app.agents.graph import analyze
from app.agents.state import Evidence
from app.integrations import slack

# Every app the workflow can investigate, from the one place that lists them. Deriving
# it means adding a connector does not mean editing the assertions in this file.
ALL_APPS = sorted(executor.INTEGRATIONS)


def evidence(source: str, title: str) -> Evidence:
    return Evidence(
        source=source,
        type="message",
        title=title,
        content=f"content of {title}",
        url=f"https://example.test/{title}",
        timestamp=datetime(2026, 9, 1, tzinfo=UTC),
    )


@pytest.fixture
def apps(monkeypatch):
    """Every integration returns one identifiable piece of evidence."""
    for source, module in executor.INTEGRATIONS.items():
        monkeypatch.setattr(
            module,
            "collect_evidence",
            lambda _project_id, _name, source=source: [evidence(source, source)],
        )


def test_analysis_runs_with_no_evidence():
    """No credentials means no evidence, which must mean no invented findings."""
    result = analyze("test-id", "SaaS Product Launch", "Launch by Oct 1")

    assert result["evidence"] == []
    assert result["findings"] == []
    assert result["plan"] == []
    assert result["health"] == "on_track"


def test_every_agent_reports_activity():
    result = analyze("test-id", "SaaS Product Launch", "Launch by Oct 1")

    agents = {entry.agent for entry in result["agent_activity"]}
    assert agents == {"supervisor", *supervisor.AGENTS, "risk", "recovery"}


def test_evidence_from_every_app_reaches_the_risk_agent(apps, monkeypatch):
    """The parallel investigators must append, not overwrite each other."""
    seen: list[Evidence] = []

    def fake_ask_for(schema, system, prompt):
        seen.extend(prompt.splitlines())
        return schema(findings=[])

    monkeypatch.setattr(risk.llm, "ask_for", fake_ask_for)
    result = analyze("test-id", "SaaS Product Launch", "Launch by Oct 1")

    sources = {item.source for item in result["evidence"]}
    assert sources == set(ALL_APPS)
    assert len(result["evidence"]) == len(ALL_APPS)
    assert any(line.startswith("[0] ") for line in seen), "risk never saw numbered evidence"
    assert sum(1 for line in seen if line.startswith("[")) == len(ALL_APPS)


def test_findings_cite_real_evidence_and_set_health(apps, monkeypatch):
    """The findings and the plan come back from one call, in one answer."""

    def fake_ask_for(schema, system, prompt):
        return schema(
            findings=[
                {
                    "title": "Payment API blocked",
                    "severity": "critical",
                    "confidence": 0.9,
                    "description": "Slack and Linear disagree about PAY-124.",
                    "evidence_indexes": [0, 2, 99],  # 99 must be ignored
                }
            ],
            steps=[
                {
                    "integration": "linear",
                    "type": "update_issue",
                    "description": "Reassign PAY-124",
                    "target": "PAY-124",
                    "value": "assign to Dana",
                    "finding_index": 0,
                }
            ],
        )

    monkeypatch.setattr(risk.llm, "ask_for", fake_ask_for)

    result = analyze("test-id", "SaaS Product Launch", "Launch by Oct 1")

    finding = result["findings"][0]
    assert len(finding.evidence) == 2  # the out-of-range index was dropped
    assert all(item in result["evidence"] for item in finding.evidence)
    assert result["health"] == "at_risk"

    action = result["plan"][0]
    assert action.reason == "Payment API blocked"
    assert action.target == "PAY-124"


def test_one_broken_app_does_not_lose_the_others(apps, monkeypatch):
    def boom(_project_id, _name):
        raise RuntimeError("Slack is down")

    monkeypatch.setattr(slack, "collect_evidence", boom)
    monkeypatch.setattr(risk.llm, "ask_for", lambda schema, system, prompt: schema(findings=[]))

    result = analyze("test-id", "SaaS Product Launch", "Launch by Oct 1")

    assert len(result["evidence"]) == len(ALL_APPS) - 1
    failures = [entry for entry in result["agent_activity"] if entry.status == "failed"]
    assert len(failures) == 1
    assert "Slack is down" in failures[0].detail


def test_one_analysis_costs_one_model_call(apps, monkeypatch):
    """The reason the findings and the plan share a request.

    A metered key counts calls, not tokens — the Gemini free tier allows 20 a day — so
    a second call to plan around findings the model had just written was half of every
    analysis. If this ever goes back to two, an afternoon of debugging costs twice the
    quota it needs to.
    """
    calls: list[str] = []

    def fake_ask_for(schema, system, prompt):
        calls.append(schema.__name__)
        return schema(
            findings=[
                {
                    "title": "Payment API blocked",
                    "severity": "critical",
                    "confidence": 0.9,
                    "description": "PAY-124 has not moved.",
                    "evidence_indexes": [0],
                }
            ],
            steps=[
                {
                    "integration": "linear",
                    "type": "update_issue",
                    "description": "Reassign PAY-124",
                    "target": "PAY-124",
                    "value": "assign to Dana",
                    "finding_index": 0,
                }
            ],
        )

    monkeypatch.setattr(risk.llm, "ask_for", fake_ask_for)
    result = analyze("test-id", "SaaS Product Launch", "Launch by Oct 1")

    assert len(calls) == 1, f"one analysis should be one call, was {calls}"
    assert result["findings"] and result["plan"], "and it still produces both halves"


def test_no_evidence_spends_nothing(monkeypatch):
    """The cheapest call is the one nobody makes."""
    calls: list[str] = []
    monkeypatch.setattr(risk.llm, "ask_for", lambda *a, **k: calls.append("x"))

    result = analyze("test-id", "SaaS Product Launch", "Launch by Oct 1")

    assert calls == []
    assert result["findings"] == [] and result["plan"] == []


def test_a_plan_for_a_problem_nobody_found_is_dropped(apps, monkeypatch):
    """The last guard before the UI offers a user something to approve. One request for
    both halves means a model that finds nothing can still volunteer steps."""

    def fake_ask_for(schema, system, prompt):
        return schema(
            findings=[],
            steps=[
                {
                    "integration": "linear",
                    "type": "update_issue",
                    "description": "Tidy the backlog",
                    "target": "PAY-1",
                    "value": "close it",
                    "finding_index": 0,
                }
            ],
        )

    monkeypatch.setattr(risk.llm, "ask_for", fake_ask_for)
    result = analyze("test-id", "SaaS Product Launch", "Launch by Oct 1")

    assert result["plan"] == []


def test_a_long_evidence_body_is_capped_in_the_prompt():
    """A GitHub commit arrives with its whole message body, and a few of those dominated
    the prompt while saying nothing the first lines did not. The stored evidence keeps
    the full text — this only caps what a model is charged to read."""
    from app.agents.state import MAX_CONTENT_IN_PROMPT, Evidence

    item = Evidence(source="github", type="commit", title="feat: everything", content="x" * 5000)

    line = item.for_prompt(3)

    assert line.startswith("[3] github · commit · ")
    assert "feat: everything" in line
    assert line.endswith("[…]")
    assert len(line) < MAX_CONTENT_IN_PROMPT + 200
    assert len(item.content) == 5000, "the evidence itself must not be truncated"


def test_a_short_evidence_body_is_left_alone():
    from app.agents.state import Evidence

    item = Evidence(source="slack", type="message", title="Blocked", content="PAY-124 is stuck")

    assert item.for_prompt(0).endswith("PAY-124 is stuck")
