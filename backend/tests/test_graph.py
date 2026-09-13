"""The graph must be wired correctly even before the integrations return data."""

from app.agents.graph import analyze


def test_analysis_runs_with_no_evidence():
    result = analyze("test-id", "SaaS Product Launch", "Launch by Oct 1")

    assert result["evidence"] == []
    assert result["findings"] == []
    assert result["plan"] == []
