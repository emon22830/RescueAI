"""Riding out a brief provider outage.

Found in production: `gemini-3.8-flash` answered 503 "experiencing high demand" for
minutes at a time, and every analysis died at the risk node — after the evidence had
already been collected, and with nobody watching a scheduled run to press the button
again. The retry is deliberately small: ride out a spike, do not queue behind an outage.
"""

import pytest
from google.genai import errors as genai_errors

from app.ai import llm


class FakeResponse:
    text = "ok"
    parsed = None


def fake_error(code: int, status: str = "UNAVAILABLE"):
    """A provider error shaped the way google-genai raises one."""
    cls = genai_errors.ServerError if code >= 500 else genai_errors.ClientError
    error = cls.__new__(cls)
    RuntimeError.__init__(error, f"{code} {status}")
    error.code = code
    error.status = status
    return error


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    """The point is what it retries, not how long a test takes."""
    monkeypatch.setattr(llm.time, "sleep", lambda _seconds: None)


@pytest.fixture
def provider(monkeypatch):
    """Swap the client for one that fails a given number of times, then succeeds."""

    def install(failures: list):
        calls = {"n": 0}

        class Models:
            def generate_content(self, **_kwargs):
                index = calls["n"]
                calls["n"] += 1
                if index < len(failures):
                    raise failures[index]
                return FakeResponse()

        class Client:
            models = Models()

        monkeypatch.setattr(llm, "_client", lambda: Client())
        return calls

    return install


def test_a_transient_503_does_not_lose_the_analysis(provider):
    """The failure that actually happened: one spike, then the model is fine."""
    calls = provider([fake_error(503)])

    assert llm.ask("system", "prompt") == "ok"
    assert calls["n"] == 2, "it should have tried again after the 503"


def test_it_keeps_trying_across_several_spikes(provider):
    calls = provider([fake_error(503), fake_error(500), fake_error(503)])

    assert llm.ask("system", "prompt") == "ok"
    assert calls["n"] == 4


def test_a_rate_limit_is_worth_waiting_out(provider):
    calls = provider([fake_error(429, "RESOURCE_EXHAUSTED")])

    assert llm.ask("system", "prompt") == "ok"
    assert calls["n"] == 2


def test_it_gives_up_rather_than_retrying_forever(provider):
    """A run that fails honestly is better than one that hangs. The real error is
    re-raised so it reaches the run row and the notification."""
    calls = provider([fake_error(503)] * 10)

    with pytest.raises(genai_errors.ServerError):
        llm.ask("system", "prompt")
    assert calls["n"] == llm.RETRY_ATTEMPTS


@pytest.mark.parametrize("code,status", [(400, "INVALID_ARGUMENT"), (403, "PERMISSION_DENIED")])
def test_our_own_mistakes_fail_immediately(provider, code, status):
    """A refused schema or a bad key is not going to get better. Retrying it three more
    times only hides the reason behind a delay — this is how the additionalProperties
    bug would have been made harder to find, not easier."""
    calls = provider([fake_error(code, status)])

    with pytest.raises(genai_errors.ClientError):
        llm.ask("system", "prompt")
    assert calls["n"] == 1, "a 4xx must not be retried"


def test_a_structured_answer_is_retried_the_same_way(provider, monkeypatch):
    """ask_for is the one the agents actually use."""
    from pydantic import BaseModel

    class Shape(BaseModel):
        value: str

    answer = Shape(value="x")

    class Response:
        parsed = answer

    calls = {"n": 0}

    class Models:
        def generate_content(self, **_kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise fake_error(503)
            return Response()

    class Client:
        models = Models()

    monkeypatch.setattr(llm, "_client", lambda: Client())

    assert llm.ask_for(Shape, "system", "prompt") is answer
    assert calls["n"] == 2


# --- what the provider asked for, versus what we guessed -----------------------
#
# Found in production, and only in production: the Gemini key was on the free tier,
# which allows 20 requests a day. Every call answered 429, `_worth_retrying` saw a rate
# limit, and the four attempts spent 98 seconds before failing with the same message
# the first attempt already had. A day-long quota is not a spike to ride out.


def quota_error(quota_id: str, retry_delay: str | None = None, limit: str = "20"):
    """A 429 shaped the way the Gemini API actually returns one."""
    error = fake_error(429, "RESOURCE_EXHAUSTED")
    parts: list[dict] = [
        {
            "@type": "type.googleapis.com/google.rpc.QuotaFailure",
            "violations": [{"quotaId": quota_id, "quotaValue": limit}],
        }
    ]
    if retry_delay:
        parts.append({"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": retry_delay})
    error.details = {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "details": parts}}
    return error


def test_a_daily_quota_is_not_retried(provider):
    """It does not come back until the day does."""
    calls = provider([quota_error("GenerateRequestsPerDayPerProjectPerModel-FreeTier")] * 10)

    with pytest.raises(genai_errors.ClientError):
        llm.ask("system", "prompt")
    assert calls["n"] == 1, "a day-long quota must fail on the first attempt"


def test_a_per_minute_limit_is_still_waited_out(provider):
    """The distinction is the quota's period, not the status code."""
    calls = provider([quota_error("GenerateRequestsPerMinutePerProjectPerModel", "5s")])

    assert llm.ask("system", "prompt") == "ok"
    assert calls["n"] == 2


def test_it_waits_as_long_as_the_provider_asked(provider, monkeypatch):
    """Waiting 2s when the provider said 12s just fails again on purpose."""
    waited: list[float] = []
    monkeypatch.setattr(llm.time, "sleep", waited.append)
    provider([quota_error("GenerateRequestsPerMinutePerProjectPerModel", "12s")])

    assert llm.ask("system", "prompt") == "ok"
    assert waited == [12.0], "our own backoff table should not override RetryInfo"


def test_it_refuses_a_wait_nobody_would_sit_through(provider):
    """Past the cap, failing now with the real reason beats hanging and failing anyway."""
    delay = f"{llm.MAX_RETRY_WAIT_SECONDS + 10}s"
    calls = provider([quota_error("GenerateRequestsPerMinutePerProjectPerModel", delay)] * 10)

    with pytest.raises(genai_errors.ClientError):
        llm.ask("system", "prompt")
    assert calls["n"] == 1


def test_an_exhausted_free_tier_says_so_and_names_the_fix():
    """The raw body is quota metrics and doc links; this text is what a user reads."""
    message = llm.explain_llm_error(
        quota_error("GenerateRequestsPerDayPerProjectPerModel-FreeTier")
    )

    assert "free-tier quota" in message
    assert "20 requests per day" in message
    assert "billing" in message


def test_a_malformed_error_body_does_not_become_a_second_failure(provider):
    """Nothing here may crash on a shape the provider changed."""
    error = fake_error(429, "RESOURCE_EXHAUSTED")
    error.details = {"error": {"details": "not a list"}}

    assert llm._daily_quota_exhausted(error) is False
    assert llm._requested_wait(error) is None
    assert llm.explain_llm_error(error)
