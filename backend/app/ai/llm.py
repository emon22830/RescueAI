"""The only place the app talks to an LLM. Swap providers here and nowhere else."""

import logging
import time
from functools import lru_cache
from typing import TypeVar

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# A popular model answers 503 "experiencing high demand" for a minute at a time. One of
# those must not lose an analysis: the evidence has already been collected by then, and
# a scheduled run has nobody watching to press the button again. Attempts are few and
# the waits short — this is riding out a spike, not queueing behind an outage.
RETRY_ATTEMPTS = 4
RETRY_BACKOFF_SECONDS = (2, 6, 15)


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


def _generate(prompt: str, config: types.GenerateContentConfig):
    """One request, retried while the provider is briefly unavailable.

    Only transient server-side failures are retried — a 5xx, or a rate limit. A refused
    schema or a bad key fails on the first attempt, because trying it again would only
    make the same mistake three more times and hide it behind a delay.
    """
    last: Exception | None = None

    for attempt in range(RETRY_ATTEMPTS):
        try:
            return _client().models.generate_content(
                model=settings.llm_model, contents=prompt, config=config
            )
        except (genai_errors.ServerError, genai_errors.ClientError) as error:
            if not _worth_retrying(error) or attempt == RETRY_ATTEMPTS - 1:
                raise
            last = error
            wait = RETRY_BACKOFF_SECONDS[min(attempt, len(RETRY_BACKOFF_SECONDS) - 1)]
            logger.warning(
                "%s unavailable (%s), retrying in %ss [%s/%s]",
                settings.llm_model,
                type(error).__name__,
                wait,
                attempt + 1,
                RETRY_ATTEMPTS - 1,
            )
            time.sleep(wait)

    raise last  # unreachable: the final attempt re-raises


def _worth_retrying(error: Exception) -> bool:
    """A 5xx or a 429 is the provider having a moment. A 4xx is us."""
    code = getattr(error, "code", None)
    return code == 429 or (isinstance(code, int) and 500 <= code < 600)


def ask(system: str, prompt: str, max_tokens: int = 8000) -> str:
    """Plain text answer."""
    response = _generate(prompt, _config(system, max_tokens))
    return response.text or ""


def ask_for(schema: type[T], system: str, prompt: str, max_tokens: int = 8000) -> T:
    """Answer validated against a Pydantic model, so agents never parse loose JSON."""
    response = _generate(
        prompt,
        _config(
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
