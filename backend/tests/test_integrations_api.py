"""Connecting an app to a project, as the Connections page does it.

Slack, Linear and GitHub are "token" apps — a user pastes a credential here, it is
verified for real before anything is saved, and it belongs to one project only.
Gmail, Drive and Calendar are "oauth": the user grants consent instead of pasting, and
one grant covers all three. Either way the credential belongs to one project.
"""

import pytest
from fastapi.testclient import TestClient

from app.auth import security
from app.config import settings
from app.integrations import github, google_auth, linear, slack
from app.projects import service
from tests.conftest import OWNER_ID


@pytest.fixture
def project_id(client: TestClient) -> str:
    response = client.post("/projects", json={"name": "SaaS Product Launch", "goal": "Launch by Oct 1"})
    return response.json()["id"]


def statuses(client: TestClient, project_id: str) -> dict[str, dict]:
    response = client.get(f"/projects/{project_id}/integrations")
    assert response.status_code == 200, response.text
    return {app["id"]: app for app in response.json()}


def test_lists_every_app_the_agent_investigates(client, project_id):
    """The Connections page must offer every app the workflow can actually collect
    from — an app the graph reads but the page never lists is unconnectable."""
    from app.agents import executor

    assert set(statuses(client, project_id)) == set(executor.INTEGRATIONS)


def test_a_token_app_starts_disconnected(client, project_id):
    assert statuses(client, project_id)["slack"]["connected"] is False


def test_connecting_verifies_the_token_before_storing_it(client, project_id, monkeypatch):
    monkeypatch.setattr(slack, "verify_token", lambda token, **_: {"team": "Acme"})

    response = client.post(
        f"/projects/{project_id}/integrations/slack/connect", json={"token": "xoxb-real"}
    )

    assert response.status_code == 200, response.text
    status = response.json()
    assert status["connected"] is True
    assert status["metadata"]["team"] == "Acme"
    assert statuses(client, project_id)["slack"]["connected"] is True


def test_a_token_that_fails_verification_is_never_stored(client, project_id, monkeypatch):
    def reject(token, **_):
        raise slack.SlackError("Slack auth.test failed: invalid_auth")

    monkeypatch.setattr(slack, "verify_token", reject)

    response = client.post(
        f"/projects/{project_id}/integrations/slack/connect", json={"token": "xoxb-bad"}
    )

    assert response.status_code == 400
    assert "invalid_auth" in response.json()["detail"]
    assert statuses(client, project_id)["slack"]["connected"] is False


def test_a_pasted_token_value_never_comes_back_in_the_response(client, project_id, monkeypatch):
    monkeypatch.setattr(linear, "verify_token", lambda token: {"user": "Dana"})

    response = client.post(
        f"/projects/{project_id}/integrations/linear/connect",
        json={"token": "lin_api_super_secret"},
    )

    assert "lin_api_super_secret" not in response.text
    assert "lin_api_super_secret" not in client.get(f"/projects/{project_id}/integrations").text


def test_disconnecting_removes_it(client, project_id, monkeypatch):
    monkeypatch.setattr(github, "verify_token", lambda token, repo: {"repo": repo})
    client.post(
        f"/projects/{project_id}/integrations/github/connect",
        json={"token": "ghp_test", "repo": "acme/payments-api"},
    )
    assert statuses(client, project_id)["github"]["connected"] is True

    response = client.delete(f"/projects/{project_id}/integrations/github")

    assert response.status_code == 204
    assert statuses(client, project_id)["github"]["connected"] is False


def test_a_connected_app_is_scoped_to_the_project_that_connected_it(client, monkeypatch):
    monkeypatch.setattr(slack, "verify_token", lambda token, **_: {"team": "Acme"})
    first = client.post("/projects", json={"name": "First", "goal": "Ship it"}).json()["id"]
    second = client.post("/projects", json={"name": "Second", "goal": "Ship it too"}).json()["id"]

    client.post(f"/projects/{first}/integrations/slack/connect", json={"token": "xoxb-real"})

    assert statuses(client, first)["slack"]["connected"] is True
    assert statuses(client, second)["slack"]["connected"] is False


def test_connecting_an_oauth_app_by_pasting_a_token_is_rejected(client, project_id):
    """Google is connected by consent, not by pasting a credential."""
    response = client.post(f"/projects/{project_id}/integrations/gmail/connect", json={"token": "x"})
    assert response.status_code == 400


def test_an_oauth_app_is_disconnected_until_the_project_grants_access(client, project_id):
    gmail = statuses(client, project_id)["gmail"]

    assert gmail["connected"] is False


def test_an_oauth_app_names_the_app_registration_when_it_is_missing(monkeypatch, client, project_id):
    """The client id identifies this deployment to Google. Without it nobody can connect,
    so the page has to say so rather than offer a button that cannot work."""
    monkeypatch.setattr(settings, "google_client_id", "")

    assert statuses(client, project_id)["gmail"]["variables"] == [
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
    ]


def test_granting_google_connects_all_three_apps(client, project_id, monkeypatch):
    """One consent covers Gmail, Drive and Calendar — they are one grant, one row."""
    monkeypatch.setattr(
        google_auth, "exchange_code", lambda code: {"refresh_token": "1//rt", "email": "a@b.com"}
    )
    service.connect_google(project_id, OWNER_ID, "auth-code")

    apps = statuses(client, project_id)
    assert [apps[name]["connected"] for name in ("gmail", "drive", "calendar")] == [True, True, True]
    assert apps["gmail"]["metadata"]["email"] == "a@b.com"


def test_the_write_targets_are_marked_as_such(client, project_id):
    """`writes_back` is what the UI calls read-only, so it has to agree with the one
    list that decides what can actually be executed."""
    from app.agents import executor

    writes_back = {app_id for app_id, app in statuses(client, project_id).items() if app["writes_back"]}

    assert writes_back == executor.WRITE_TARGETS
    assert "drive" not in writes_back  # the one app that only ever collects


def test_integrations_are_404_for_someone_elses_project(client, project_id):
    assert client.get("/projects/does-not-exist/integrations").status_code == 404


# --- what the project list reports --------------------------------------------
# The dashboard shows each project's connectors without a request per project, so the
# project payload carries them. These guard that it tells the truth.


def connected_on_list(client: TestClient) -> list[str]:
    return client.get("/projects").json()[0]["connected"]


def test_a_new_project_reports_no_connected_apps(client, project_id):
    assert connected_on_list(client) == []


def test_connecting_an_app_shows_up_on_the_project(client, project_id, monkeypatch):
    monkeypatch.setattr(linear, "verify_token", lambda token, **_: {"user": "Priya"})

    client.post(f"/projects/{project_id}/integrations/linear/connect", json={"token": "lin_real"})

    assert connected_on_list(client) == ["linear"]


def test_google_counts_as_connected_only_for_the_project_that_granted_it(
    client, project_id, monkeypatch
):
    """The old shared-.env model made one Google account everyone's. It is per project now."""
    monkeypatch.setattr(
        google_auth, "exchange_code", lambda code: {"refresh_token": "1//rt", "email": "a@b.com"}
    )
    other = client.post("/projects", json={"name": "Other", "goal": "g"}).json()["id"]
    service.connect_google(project_id, OWNER_ID, "auth-code")

    granted = client.get(f"/projects/{project_id}/integrations").json()
    assert sorted(app["id"] for app in granted if app["connected"]) == ["calendar", "drive", "gmail"]

    ungranted = client.get(f"/projects/{other}/integrations").json()
    assert [app["id"] for app in ungranted if app["connected"]] == []


def test_disconnecting_removes_it_from_the_project(client, project_id, monkeypatch):
    monkeypatch.setattr(slack, "verify_token", lambda token, **_: {"team": "Acme"})
    client.post(f"/projects/{project_id}/integrations/slack/connect", json={"token": "xoxb"})
    assert connected_on_list(client) == ["slack"]

    client.delete(f"/projects/{project_id}/integrations/slack")

    assert connected_on_list(client) == []


# --- the Google OAuth round trip ----------------------------------------------
# Consent happens on Google's site, so the browser leaves us and comes back. These
# guard the two ends of that trip: what we send a user to, and what we accept back.


def test_authorize_sends_the_user_to_google_with_offline_consent(client, project_id, monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "client-id")
    monkeypatch.setattr(settings, "google_client_secret", "client-secret")

    url = client.get(f"/projects/{project_id}/integrations/google/authorize").json()["url"]

    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth")
    # Without both of these Google returns no refresh token and the connection dies
    # silently an hour later.
    assert "access_type=offline" in url
    assert "prompt=consent" in url
    assert "gmail.readonly" in url


def test_authorize_is_404_for_a_project_you_do_not_own(client):
    assert client.get("/projects/not-mine/integrations/google/authorize").status_code == 404


def test_the_callback_stores_the_grant_and_returns_to_the_project(client, project_id, monkeypatch):
    monkeypatch.setattr(
        google_auth, "exchange_code", lambda code: {"refresh_token": "1//rt", "email": "a@b.com"}
    )
    state = security.sign_state(project_id=project_id, owner_id=OWNER_ID)

    response = client.get(
        "/integrations/google/callback", params={"code": "abc", "state": state}, follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"].endswith(f"/app/projects/{project_id}/connections?google=connected")
    assert statuses(client, project_id)["drive"]["connected"] is True


def test_a_forged_callback_state_is_refused(client):
    """The state is the only thing proving this redirect is the one we sent."""
    response = client.get(
        "/integrations/google/callback",
        params={"code": "abc", "state": "forged"},
        follow_redirects=False,
    )

    assert response.status_code == 401
    assert statuses  # the credential was never stored, so nothing to assert beyond refusal


def test_a_user_who_declines_consent_is_returned_without_a_connection(client, project_id):
    state = security.sign_state(project_id=project_id, owner_id=OWNER_ID)

    response = client.get(
        "/integrations/google/callback",
        params={"error": "access_denied", "state": state},
        follow_redirects=False,
    )

    assert response.headers["location"].endswith("?google=access_denied")
    assert statuses(client, project_id)["gmail"]["connected"] is False


def test_a_google_grant_is_reported_as_its_three_apps_not_as_google(client, project_id, monkeypatch):
    """'google' is the storage row, not an app. Leaking it into the project payload
    fails ProjectResponse validation, which reaches the browser as a dead backend."""
    monkeypatch.setattr(
        google_auth, "exchange_code", lambda code: {"refresh_token": "1//rt", "email": "a@b.com"}
    )
    service.connect_google(project_id, OWNER_ID, "auth-code")

    connected = connected_on_list(client)

    assert sorted(connected) == ["calendar", "drive", "gmail"]
    assert "google" not in connected
