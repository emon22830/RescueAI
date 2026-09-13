"""The only place the app talks to an LLM. Swap providers here and nowhere else."""

from functools import lru_cache
from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.config import settings

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    """The model returned nothing usable. The run records it and fails honestly."""


@lru_cache
def _client() -> genai.Client:
    settings.require("gemini_api_key")
    return genai.Client(api_key=settings.gemini_api_key)


def _config(system: str, max_tokens: int, **extra) -> types.GenerateContentConfig:
    """Shared generation settings.

    Gemini spends output tokens on thinking before it writes an answer, so a budget
    that looks generous can be consumed entirely by reasoning and return an empty
    response. `thinking_budget` caps that so the answer always has room.
    """
    return types.GenerateContentConfig(
        system_instruction=system,
        max_output_tokens=max_tokens,
        thinking_config=types.ThinkingConfig(thinking_budget=2000),
        **extra,
    )


def ask(system: str, prompt: str, max_tokens: int = 8000) -> str:
    """Plain text answer."""
    response = _client().models.generate_content(
        model=settings.llm_model,
        contents=prompt,
        config=_config(system, max_tokens),
    )
    return response.text or ""


def ask_for(schema: type[T], system: str, prompt: str, max_tokens: int = 8000) -> T:
    """Answer validated against a Pydantic model, so agents never parse loose JSON."""
    response = _client().models.generate_content(
        model=settings.llm_model,
        contents=prompt,
        config=_config(
            system,
            max_tokens,
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    parsed = response.parsed
    if not isinstance(parsed, schema):
        raise LLMError(
            f"{settings.llm_model} did not return a valid {schema.__name__}. "
            f"Finish reason: {response.candidates[0].finish_reason if response.candidates else 'none'}"
        )
    return parsed
