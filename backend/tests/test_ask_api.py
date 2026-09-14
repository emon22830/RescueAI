"""Asking a question about a project.

The answer may only come from evidence the workflow already collected, so these tests
care about two things: that a question with no evidence behind it is refused rather
than guessed at, and that an answer carries the real evidence it cited. Saying hello is
the exception — that is a message, not a claim about the project, and it gets a reply.
"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.agents import risk
from app.agents.state import Evidence
from app.ai.llm import LLMError
from app.integrations import calendar, drive, github, gmail, linear, slack
from app.projects import service


@pytest.fixture
def apps(monkeypatch):
    """Two apps contribute one dated item each."""
    for module in (slack, linear):
        source = module.__name__.rsplit(".", 1)[-1]
        monkeypatch.setattr(
            module,
            "collect_evidence",
            lambda _project_id, _name, source=source: [
                Evidence(
                    source=source,
                    type="message",
                    title=f"{source} item",
                    content=f"what {source} said",
                    url=f"https://example.test/{source}",
                    timestamp=datetime(2026, 9, 2, tzinfo=UTC),
                )
            ],
        )
    for module in (gmail, github, drive, calendar):
        monkeypatch.setattr(module, "collect_evidence", lambda _project_id, _name: [])


@pytest.fixture
def no_apps(monkeypatch):
    """A run that reaches every app and collects nothing from any of them."""
    for module in (slack, linear, gmail, github, drive, calendar):
        monkeypatch.setattr(module, "collect_evidence", lambda _project_id, _name: [])


@pytest.fixture
def agent(monkeypatch):
    """A run that produces state but no findings — evidence is what `ask` needs."""

    def fake_ask_for(schema, system, prompt):
        if "findings" in schema.model_fields:
            return schema(findings=[], summary="Two apps reported in.", progress=20)
        return schema(steps=[])

    monkeypatch.setattr(risk.llm, "ask_for", fake_ask_for)


def analyzed_project(client: TestClient) -> str:
    project_id = client.post(
        "/projects", json={"name": "SaaS Product Launch", "goal": "Launch by Oct 1"}
    ).json()["id"]
    assert client.post(f"/projects/{project_id}/analyze").status_code == 202
    return project_id


def answer(monkeypatch, **fields):
    """Make the ask call return one fixed answer."""
    def fake_ask_for(schema, system, prompt):
        fake_ask_for.prompt = prompt
        return schema(**fields)

    monkeypatch.setattr(service.llm, "ask_for", fake_ask_for)
    return fake_ask_for


def test_a_project_with_no_run_is_refused_without_calling_the_model(
    client: TestClient, monkeypatch
):
    project_id = client.post("/projects", json={"name": "Fresh", "goal": "Ship it"}).json()["id"]

    def explode(*_args, **_kwargs):
        raise AssertionError("the model must not be called when there is no evidence")

    monkeypatch.setattr(service.llm, "ask_for", explode)

    body = client.post(f"/projects/{project_id}/ask", json={"question": "Where are we?"}).json()

    assert body["answered"] is False
    assert body["evidence"] == []
    assert "has not been analyzed yet" in body["answer"]


def test_an_answer_carries_the_evidence_it_cited(client: TestClient, apps, agent, monkeypatch):
    project_id = analyzed_project(client)
    answer(monkeypatch, answer="PAY-124 has not moved.", evidence_indexes=[0], answered=True)

    body = client.post(
        f"/projects/{project_id}/ask", json={"question": "What is blocking us?"}
    ).json()

    assert body["answered"] is True
    assert body["answer"] == "PAY-124 has not moved."
    assert len(body["evidence"]) == 1
    assert body["evidence"][0]["source"] in {"slack", "linear"}
    assert body["evidence"][0]["url"].startswith("https://example.test/")


def test_the_question_and_the_evidence_both_reach_the_prompt(
    client: TestClient, apps, agent, monkeypatch
):
    project_id = analyzed_project(client)
    spy = answer(monkeypatch, answer="…", evidence_indexes=[], answered=False)

    client.post(f"/projects/{project_id}/ask", json={"question": "Who owns PAY-124?"})

    assert "QUESTION: Who owns PAY-124?" in spy.prompt
    assert "SaaS Product Launch" in spy.prompt
    assert "what slack said" in spy.prompt


def test_a_question_the_evidence_cannot_answer_comes_back_unanswered(
    client: TestClient, apps, agent, monkeypatch
):
    project_id = analyzed_project(client)
    answer(
        monkeypatch,
        answer="Nothing collected mentions the budget. Finance would hold that.",
        evidence_indexes=[],
        answered=False,
    )

    body = client.post(
        f"/projects/{project_id}/ask", json={"question": "What is the budget?"}
    ).json()

    assert body["answered"] is False
    assert body["evidence"] == []


def test_an_evidence_index_outside_the_list_is_ignored(
    client: TestClient, apps, agent, monkeypatch
):
    project_id = analyzed_project(client)
    answer(monkeypatch, answer="…", evidence_indexes=[0, 99, -3], answered=True)

    body = client.post(f"/projects/{project_id}/ask", json={"question": "Status?"}).json()

    assert len(body["evidence"]) == 1


def test_an_empty_question_is_rejected(client: TestClient):
    project_id = client.post("/projects", json={"name": "Fresh", "goal": "Ship"}).json()["id"]

    assert client.post(f"/projects/{project_id}/ask", json={"question": ""}).status_code == 422


def test_asking_about_an_unknown_project_is_a_404(client: TestClient):
    response = client.post(
        "/projects/00000000-0000-0000-0000-000000000000/ask", json={"question": "Hi"}
    )

    assert response.status_code == 404


def test_a_model_failure_is_reported_instead_of_a_bare_500(
    client: TestClient, apps, agent, monkeypatch
):
    """An unhandled LLMError reaches the Ask panel as a bare 500, which reads to a user
    as the agent not answering at all. It must come back as a message they can act on."""
    project_id = analyzed_project(client)

    def boom(*_args, **_kwargs):
        raise LLMError("the model did not return a valid answer. Finish reason: MAX_TOKENS")

    monkeypatch.setattr(service.llm, "ask_for", boom)

    response = client.post(f"/projects/{project_id}/ask", json={"question": "Status?"})

    assert response.status_code == 502
    assert "MAX_TOKENS" in response.json()["detail"]


def test_a_greeting_gets_a_real_reply_instead_of_an_evidence_warning(
    client: TestClient, apps, agent, monkeypatch
):
    """"Hi" is not a hole in the evidence. Flagging it as one makes the agent look
    broken to the person who just opened the panel."""
    project_id = analyzed_project(client)
    answer(
        monkeypatch,
        answer="Hello. Ask me what is blocking the launch and I will read the evidence.",
        evidence_indexes=[],
        answered=True,
        kind="chat",
    )

    body = client.post(f"/projects/{project_id}/ask", json={"question": "Hi buddy"}).json()

    assert body["kind"] == "chat"
    assert body["answered"] is True
    assert body["evidence"] == []


def test_a_run_that_collected_nothing_still_answers_the_message(
    client: TestClient, no_apps, agent, monkeypatch
):
    """No evidence is a reason to say what is missing, not a reason to stop talking —
    so the model is still asked, with a prompt that forbids any claim about the project."""
    project_id = analyzed_project(client)
    spy = answer(
        monkeypatch,
        answer="The last run found nothing. Connect Slack and Linear, then investigate.",
        evidence_indexes=[],
        answered=False,
        kind="gap",
    )

    body = client.post(f"/projects/{project_id}/ask", json={"question": "Hi buddy"}).json()

    assert "(none — the latest run collected nothing)" in spy.prompt
    assert body["answered"] is False
    assert body["evidence"] == []
    assert "Connect Slack" in body["answer"]


def test_follow_ups_come_back_and_are_capped_at_three(
    client: TestClient, apps, agent, monkeypatch
):
    project_id = analyzed_project(client)
    answer(
        monkeypatch,
        answer="PAY-124 has not moved in nine days.",
        evidence_indexes=[0],
        answered=True,
        follow_ups=["Who owns it?", "What blocks it?", "When was it last touched?", "Extra"],
    )

    body = client.post(f"/projects/{project_id}/ask", json={"question": "Status?"}).json()

    assert body["follow_ups"] == ["Who owns it?", "What blocks it?", "When was it last touched?"]


def test_a_long_pasted_question_is_accepted(client: TestClient, apps, agent, monkeypatch):
    """The composer is a real text area now; a pasted paragraph must not 422."""
    project_id = analyzed_project(client)
    answer(monkeypatch, answer="…", evidence_indexes=[], answered=True)

    response = client.post(
        f"/projects/{project_id}/ask", json={"question": "Why is this late? " * 60}
    )

    assert response.status_code == 200
