"""Asking a question about a project.

This is not a chatbot bolted on the side. It is one more view onto the state the
workflow already built: the answer may only use evidence collected by the latest
completed run, and it cites that evidence the same way a finding does. A question the
evidence cannot answer comes back as `answered: false` rather than a guess.

It still talks like a person. A greeting or a question about the agent itself gets a
real reply — `kind: "chat"` — because refusing to say hello is not grounding, it is
just rude.
"""

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.agents.state import Evidence
from app.auth import CurrentUser, get_current_user
from app.projects import service

router = APIRouter(prefix="/projects/{project_id}", tags=["ask"])


class AskRequest(BaseModel):
    # Long enough to paste a paragraph of context into the question, short enough that
    # one message can never crowd the evidence out of the prompt.
    question: str = Field(min_length=1, max_length=2000)


class AskResponse(BaseModel):
    """One answer, and the evidence it was drawn from."""

    question: str
    # Markdown: bold, bullets and headings, the way the analyst would write it out.
    answer: str
    # False when the collected evidence does not answer the question, or when there is
    # no completed run to answer from. The UI says so instead of implying certainty.
    answered: bool
    # "answer" drawn from evidence, "gap" the evidence cannot fill, or "chat" — a hello
    # or a question about the agent itself, which is not a hole in the evidence and must
    # not be flagged as one.
    kind: Literal["answer", "gap", "chat"] = "answer"
    # Questions this same evidence could answer next.
    follow_ups: list[str] = []
    evidence: list[Evidence] = []


@router.post("/ask", response_model=AskResponse)
def ask_project(
    project_id: str, body: AskRequest, user: CurrentUser = Depends(get_current_user)
) -> dict:
    return service.answer_question(project_id, user.id, body.question)
