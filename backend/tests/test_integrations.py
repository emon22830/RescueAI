"""Unconnected apps must contribute nothing.

The one rule this file exists to enforce: an integration without credentials returns
an empty list. It never returns invented evidence, and it never reaches the network to
go looking. A demo is only honest if every item on screen came from a real workspace.
"""

import httpx
import pytest

from app.config import settings
from app.integrations import calendar, drive, github, gmail, linear, slack

INTEGRATIONS = (slack, gmail, drive, linear, github, calendar)

CREDENTIALS = (
    "slack_bot_token",
    "linear_api_key",
    "github_token",
    "github_repo",
    "google_client_id",
    "google_client_secret",
    "google_refresh_token",
)


@pytest.fixture
def unconnected(monkeypatch):
    """No credentials, and a network that fails loudly if anything tries to use it."""
    for name in CREDENTIALS:
        monkeypatch.setattr(settings, name, "")

    def no_network(*_args, **_kwargs):
        raise AssertionError("an unconnected integration must not call out to the network")

    monkeypatch.setattr(httpx, "get", no_network)
    monkeypatch.setattr(httpx, "post", no_network)


@pytest.mark.parametrize("module", INTEGRATIONS, ids=lambda m: m.__name__.rsplit(".", 1)[-1])
def test_an_unconnected_app_returns_no_evidence(module, unconnected):
    assert module.collect_evidence("SaaS Product Launch") == []


@pytest.mark.parametrize("module", INTEGRATIONS, ids=lambda m: m.__name__.rsplit(".", 1)[-1])
def test_every_integration_has_the_same_two_functions(module):
    """One shape for all six, so the executor can map an action to any of them."""
    assert callable(module.collect_evidence)
    assert callable(module.execute_action)
