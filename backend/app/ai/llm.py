"""The only place the app talks to an LLM. Swap providers here and nowhere else."""

from functools import lru_cache
from typing import TypeVar

import anthropic
from pydantic import BaseModel

from app.config import settings

T = TypeVar("T", bound=BaseModel)


@lru_cache
def _client() -> anthropic.Anthropic:
    settings.require("anthropic_api_key")
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def ask(system: str, prompt: str, max_tokens: int = 8000) -> str:
    """Plain text answer."""
    response = _client().messages.create(
        model=settings.llm_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def ask_for(schema: type[T], system: str, prompt: str, max_tokens: int = 8000) -> T:
    """Answer validated against a Pydantic model, so agents never parse loose JSON."""
    response = _client().messages.parse(
        model=settings.llm_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
        output_format=schema,
    )
    return response.parsed_output
