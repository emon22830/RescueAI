"""Unconnected apps must contribute nothing.

The one rule this file exists to enforce: an integration without credentials returns
an empty list. It never returns invented evidence, and it never reaches the network to
go looking. A demo is only honest if every item on screen came from a real workspace.

Every app reads its credential from the database now — a Slack/Linear/GitHub token
the project pasted, or the Google refresh token it granted. So "unconnected" means one
thing for all six: no row in `integrations`, which is what the empty fake database gives.
"""

import httpx
import pytest

from app.integrations import calendar, drive, github, gmail, linear, slack
from app.projects import service
from tests.fake_db import FakeDatabase

TOKEN_INTEGRATIONS = (slack, linear, github)
OAUTH_INTEGRATIONS = (gmail, drive, calendar)
INTEGRATIONS = (*TOKEN_INTEGRATIONS, *OAUTH_INTEGRATIONS)


@pytest.fixture
def unconnected(monkeypatch):
    """No project has connected any app, and a network that fails loudly if anything
    tries to use it anyway."""
    monkeypatch.setattr(service, "get_db", lambda: FakeDatabase())

    def no_network(*_args, **_kwargs):
        raise AssertionError("an unconnected integration must not call out to the network")

    monkeypatch.setattr(httpx, "get", no_network)
    monkeypatch.setattr(httpx, "post", no_network)


@pytest.mark.parametrize("module", INTEGRATIONS, ids=lambda m: m.__name__.rsplit(".", 1)[-1])
def test_an_unconnected_app_returns_no_evidence(module, unconnected):
    assert module.collect_evidence("test-project", "SaaS Product Launch") == []


@pytest.mark.parametrize("module", INTEGRATIONS, ids=lambda m: m.__name__.rsplit(".", 1)[-1])
def test_every_integration_can_collect_and_execute(module):
    """One shape for all six, so the executor can map an action to any of them."""
    assert callable(module.collect_evidence)
    assert callable(module.execute_action)


@pytest.mark.parametrize("module", TOKEN_INTEGRATIONS, ids=lambda m: m.__name__.rsplit(".", 1)[-1])
def test_token_apps_can_verify_a_credential_before_it_is_stored(module):
    """The connect flow needs this to fail fast on a bad paste, before anything is saved."""
    assert callable(module.verify_token)


@pytest.mark.parametrize("module", OAUTH_INTEGRATIONS, ids=lambda m: m.__name__.rsplit(".", 1)[-1])
def test_a_connected_google_app_reaches_the_http_layer(module, monkeypatch):
    """The connected path, which the unconnected tests never touch.

    Every Google helper takes the project_id through to google_auth.headers(), so a
    missed argument anywhere in that chain is a TypeError the moment a real project
    collects — invisible until someone actually connects Google.
    """
    monkeypatch.setattr(module.google_auth, "is_connected", lambda project_id: True)
    monkeypatch.setattr(module.google_auth, "headers", lambda project_id: {"Authorization": "Bearer t"})

    class EmptyResponse:
        status_code = 200
        text = ""

        def json(self):
            return {}

        def raise_for_status(self):
            return None

    monkeypatch.setattr(module.httpx, "get", lambda *a, **k: EmptyResponse())

    assert module.collect_evidence("project-1", "SaaS Product Launch") == []


# --- GitHub: resolving what the user actually pasted ---------------------------


class FakeResponse:
    """Just enough of httpx.Response for verify_token to branch on."""

    def __init__(self, status_code: int, payload=None, text: str = ""):
        self.status_code = status_code
        self.is_success = 200 <= status_code < 300
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


def fake_github(monkeypatch, routes: dict):
    """Serve GitHub from a {path: FakeResponse} map; anything unmapped is a 404."""

    def get(url, **kwargs):
        path = url.removeprefix(github.API)
        return routes.get(path, FakeResponse(404, {"message": "Not Found"}))

    monkeypatch.setattr(github.httpx, "get", get)


@pytest.mark.parametrize(
    "pasted",
    [
        "octocat/hello-world",
        "https://github.com/octocat/hello-world",
        "https://github.com/octocat/hello-world/tree/main",
        "git@github.com:octocat/hello-world.git",
        "  octocat/hello-world  ",
    ],
    ids=["plain", "url", "url-with-branch", "ssh", "padded"],
)
def test_a_repository_is_recognised_however_it_was_pasted(pasted, monkeypatch):
    fake_github(
        monkeypatch,
        {"/repos/octocat/hello-world": FakeResponse(200, {"full_name": "octocat/hello-world"})},
    )
    assert github.verify_token("tok", pasted) == {"repo": "octocat/hello-world"}


def test_a_bare_name_resolves_to_the_token_s_own_account(monkeypatch):
    """What the user typed on the Connections page: the repository name, no owner."""
    fake_github(
        monkeypatch,
        {
            "/user": FakeResponse(200, {"login": "mdemon"}),
            "/repos/mdemon/HeyAI": FakeResponse(200, {"full_name": "mdemon/HeyAI"}),
        },
    )
    assert github.verify_token("tok", "HeyAI") == {"repo": "mdemon/HeyAI"}


def test_a_bare_name_resolves_to_an_organization_repository(monkeypatch):
    """Not under the user's own login, but still granted to the token."""
    fake_github(
        monkeypatch,
        {
            "/user": FakeResponse(200, {"login": "mdemon"}),
            "/user/repos": FakeResponse(200, [{"name": "HeyAI", "full_name": "wesably/HeyAI"}]),
        },
    )
    assert github.verify_token("tok", "HeyAI") == {"repo": "wesably/HeyAI"}


def test_an_unfindable_bare_name_says_what_to_type_instead(monkeypatch):
    fake_github(
        monkeypatch,
        {
            "/user": FakeResponse(200, {"login": "mdemon"}),
            "/user/repos": FakeResponse(200, []),
        },
    )
    with pytest.raises(github.GitHubError) as raised:
        github.verify_token("tok", "HeyAI")
    assert "owner/name" in str(raised.value)
    assert "mdemon/HeyAI" in str(raised.value)


def test_an_expired_token_is_named_as_the_problem(monkeypatch):
    """A 401 is the token, not the repository — saying 'not visible' would send the
    user off checking a spelling that was never wrong."""
    fake_github(monkeypatch, {"/user": FakeResponse(401, {"message": "Bad credentials"})})
    with pytest.raises(github.GitHubError, match="rejected this token"):
        github.verify_token("tok", "HeyAI")


def test_an_empty_repository_is_refused_before_any_request(monkeypatch):
    def no_network(*_args, **_kwargs):
        raise AssertionError("an empty repository must not reach the network")

    monkeypatch.setattr(github.httpx, "get", no_network)
    with pytest.raises(github.GitHubError, match="owner/name"):
        github.verify_token("tok", "   ")
