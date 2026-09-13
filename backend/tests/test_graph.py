"""The graph must carry evidence from the investigators all the way to the plan."""

from datetime import UTC, datetime

import pytest

from app.agents import risk
from app.agents.graph import analyze
from app.agents.state import Evidence
from app.integrations import calendar, drive, github, gmail, linear, slack


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
    for module in (slack, gmail, github, linear, drive, calendar):
        source = module.__name__.rsplit(".", 1)[-1]
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
    assert agents == {"supervisor", "communication", "engineering", "requirements", "risk", "recovery"}


def test_evidence_from_all_six_apps_reaches_the_risk_agent(apps, monkeypatch):
    """The three parallel investigators must append, not overwrite each other."""
    seen: list[Evidence] = []

    def fake_ask_for(schema, system, prompt):
        seen.extend(prompt.splitlines())
        return schema(findings=[])

    monkeypatch.setattr(risk.llm, "ask_for", fake_ask_for)
    result = analyze("test-id", "SaaS Product Launch", "Launch by Oct 1")

    sources = {item.source for item in result["evidence"]}
    assert sources == {"slack", "gmail", "github", "linear", "drive", "calendar"}
    assert len(result["evidence"]) == 6
    assert any(line.startswith("[0] ") for line in seen), "risk never saw numbered evidence"
    assert sum(1 for line in seen if line.startswith("[")) == 6


def test_findings_cite_real_evidence_and_set_health(apps, monkeypatch):
    """risk and recovery share one llm module, so the fake answers by schema."""

    def fake_ask_for(schema, system, prompt):
        if "findings" in schema.model_fields:
            return schema(
                findings=[
                    {
                        "title": "Payment API blocked",
                        "severity": "critical",
                        "confidence": 0.9,
                        "description": "Slack and Linear disagree about PAY-124.",
                        "evidence_indexes": [0, 2, 99],  # 99 must be ignored
                    }
                ]
            )
        return schema(
            steps=[
                {
                    "integration": "linear",
                    "type": "update_issue",
                    "description": "Reassign PAY-124",
                    "target": "PAY-124",
                    "value": "assign to Dana",
                    "finding_index": 0,
                }
            ]
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

    assert len(result["evidence"]) == 5
    failures = [entry for entry in result["agent_activity"] if entry.status == "failed"]
    assert len(failures) == 1
    assert "Slack is down" in failures[0].detail
