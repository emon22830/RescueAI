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

# How long we are willing to sit on a single retry. The provider tells us how long it
# wants us to wait, and it is often longer than anyone is prepared to watch a spinner
# for — past this, failing now with the real reason beats hanging and failing anyway.
MAX_RETRY_WAIT_SECONDS = 30

# Gemini spends output tokens thinking before it writes anything, and that thinking is
# most of the wait on a short answer. The analysis is a real reasoning job over every
# piece of evidence and needs the room. Ask is one focused question with the evidence
# already in front of it — the same budget there is mostly spent making someone watch a
# spinner.
DEFAULT_THINKING_BUDGET = 2000
BRIEF_THINKING_BUDGET = 600


class LLMError(RuntimeError):
    """The model returned nothing usable. The run records it and fails honestly."""


# The provider's own failure type, re-exported so the error handlers in main.py can
# name it without importing the LLM SDK — this file is the only place that may.
ProviderError = genai_errors.APIError


@lru_cache
def _client() -> genai.Client:
    settings.require("gemini_api_key")
    return genai.Client(api_key=settings.gemini_api_key)


def _config(
    system: str, max_tokens: int, thinking_budget: int = DEFAULT_THINKING_BUDGET, **extra
) -> types.GenerateContentConfig:
    """Shared generation settings.

    Gemini spends output tokens on thinking before it writes an answer, so a budget
    that looks generous can be consumed entirely by reasoning and return an empty
    response. `thinking_budget` caps that so the answer always has room.
    """
    return types.GenerateContentConfig(
        system_instruction=system,
        max_output_tokens=max_tokens,
        thinking_config=types.ThinkingConfig(thinking_budget=thinking_budget),
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
            # Prefer the provider's own number over ours. When Gemini says "retry in
            # 31s" and we wait 2, every attempt is spent failing on purpose — which is
            # how a fast, clear error turns into a minute and a half of nothing.
            wait = _requested_wait(error)
            if wait is None:
                wait = RETRY_BACKOFF_SECONDS[min(attempt, len(RETRY_BACKOFF_SECONDS) - 1)]
            if wait > MAX_RETRY_WAIT_SECONDS:
                raise
            last = error
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
    """A 5xx or a 429 is the provider having a moment. A 4xx is us.

    With one exception: a 429 that names a *per-day* quota is not a moment. It does not
    come back until the day does, so the three further attempts only spend the caller's
    time before failing with the message they would have had straight away.
    """
    code = getattr(error, "code", None)
    if code == 429:
        return not _daily_quota_exhausted(error)
    return isinstance(code, int) and 500 <= code < 600


# --- reading what the provider said -------------------------------------------
#
# google-genai hands the raw Google API error body back on `error.details`. These read
# the two parts of it worth acting on, and each is written to survive a shape it does
# not recognise — a missing key must never become a second failure on top of the first.


def _error_parts(error: Exception) -> list[dict]:
    details = getattr(error, "details", None)
    body = details.get("error", details) if isinstance(details, dict) else None
    parts = body.get("details") if isinstance(body, dict) else None
    return [part for part in parts if isinstance(part, dict)] if isinstance(parts, list) else []


def _quota_violation(error: Exception) -> dict | None:
    for part in _error_parts(error):
        if str(part.get("@type", "")).endswith("QuotaFailure"):
            violations = part.get("violations")
            if isinstance(violations, list) and violations and isinstance(violations[0], dict):
                return violations[0]
    return None


def _daily_quota_exhausted(error: Exception) -> bool:
    violation = _quota_violation(error)
    return violation is not None and "PerDay" in str(violation.get("quotaId", ""))


def _requested_wait(error: Exception) -> float | None:
    """The `RetryInfo` the provider attached, in seconds, or None if it attached none."""
    for part in _error_parts(error):
        if str(part.get("@type", "")).endswith("RetryInfo"):
            try:
                return float(str(part.get("retryDelay", "")).removesuffix("s"))
            except ValueError:
                return None
    return None


def explain_llm_error(error: Exception) -> str:
    """The provider's failure in words that say what to do about it.

    The raw body is three paragraphs of quota metrics and doc links, and it reached the
    UI verbatim on a failed run. The one case worth naming is the one that actually
    happens: the key is on the free tier and has spent its allowance.
    """
    if getattr(error, "code", None) == 429:
        violation = _quota_violation(error)
        if violation is not None and "FreeTier" in str(violation.get("quotaId", "")):
            limit = violation.get("quotaValue")
            allowance = f" ({limit} requests per day)" if limit else ""
            return (
                f"{settings.llm_model} has used up its free-tier quota{allowance}. "
                "Enable billing on the Gemini API key in backend/.env, or wait for the "
                "quota to reset."
            )
        return f"{settings.llm_model} is rate limited. Try again in a minute."
    if isinstance(getattr(error, "code", None), int) and error.code >= 500:
        return f"{settings.llm_model} is unavailable right now. Try again in a minute."
    return f"{settings.llm_model} refused the request: {error}"


def ask(
    system: str,
    prompt: str,
    max_tokens: int = 8000,
    thinking_budget: int = DEFAULT_THINKING_BUDGET,
) -> str:
    """Plain text answer."""
    response = _generate(prompt, _config(system, max_tokens, thinking_budget))
    return response.text or ""


def ask_for(
    schema: type[T],
    system: str,
    prompt: str,
    max_tokens: int = 8000,
    thinking_budget: int = DEFAULT_THINKING_BUDGET,
) -> T:
    """Answer validated against a Pydantic model, so agents never parse loose JSON."""
    response = _generate(
        prompt,
        _config(
            system,
            max_tokens,
            thinking_budget,
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
