"""Who is allowed to call the API, and who owns what once they are in.

Every other test file signs in as one fixed user via the `client` fixture's dependency
override, so the real Supabase verification path and cross-user isolation are only
exercised here.
"""

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

import app.auth.dependencies as auth_module
from app.auth import CurrentUser, get_current_user
from app.main import app
from tests.conftest import OWNER_ID
from tests.fake_db import FakeDatabase, FakeUser


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    """What FastAPI hands the dependency once it has parsed the Authorization header."""
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_no_bearer_token_is_401(db):
    """A raw client, with no dependency override and no header, hits the real check."""
    response = TestClient(app).get("/projects")

    assert response.status_code == 401
    assert "bearer token" in response.json()["detail"].lower()


def test_a_valid_token_resolves_to_the_supabase_user(monkeypatch):
    fake = FakeDatabase()
    fake.auth.users["good-token"] = FakeUser("u-1", "person@example.test")
    monkeypatch.setattr(auth_module, "get_db", lambda: fake)

    user = get_current_user(_bearer("good-token"))

    assert user == CurrentUser("u-1", "person@example.test")


def test_an_unrecognized_token_is_401(monkeypatch):
    monkeypatch.setattr(auth_module, "get_db", lambda: FakeDatabase())

    with pytest.raises(auth_module.AuthError):
        get_current_user(_bearer("nonsense"))


def test_a_project_belonging_to_someone_else_is_404_not_403(client: TestClient):
    """An id that exists but isn't yours must read exactly like an id that doesn't."""
    project_id = client.post(
        "/projects", json={"name": "SaaS Product Launch", "goal": "Launch by Oct 1"}
    ).json()["id"]

    app.dependency_overrides[get_current_user] = lambda: CurrentUser("someone-else", None)
    try:
        response = TestClient(app).get(f"/projects/{project_id}")
    finally:
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(OWNER_ID, "owner@example.com")

    assert response.status_code == 404


def test_projects_are_listed_only_for_their_owner(client: TestClient):
    client.post("/projects", json={"name": "Mine", "goal": "Ship it"})

    app.dependency_overrides[get_current_user] = lambda: CurrentUser("someone-else", None)
    try:
        others_view = TestClient(app).get("/projects").json()
    finally:
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(OWNER_ID, "owner@example.com")

    assert others_view == []


def test_me_returns_the_signed_in_user(client: TestClient):
    response = client.get("/auth/me")

    assert response.status_code == 200
    assert response.json() == {"id": OWNER_ID, "email": "owner@example.com"}


def test_me_without_a_token_is_401(db):
    assert TestClient(app).get("/auth/me").status_code == 401


def test_protected_routes_declare_the_bearer_scheme(db):
    """The padlock in /docs is what tells a reader the API is not open. If the scheme
    stops being declared, auth still works but the documentation quietly lies."""
    schema = TestClient(app).get("/openapi.json").json()

    assert "Supabase session" in schema["components"]["securitySchemes"]
    assert schema["paths"]["/projects"]["get"]["security"] == [{"Supabase session": []}]
    assert "security" not in schema["paths"]["/health"]["get"]


# --- how often we ask Supabase who this is ------------------------------------
#
# Verifying a token is a network round trip, and the project page opens seven requests
# at once — so an unremembered answer put seven hops in front of every page load before
# a single one had looked at a project.


def test_the_same_token_is_only_verified_once(monkeypatch):
    fake = FakeDatabase()
    fake.auth.users["good-token"] = FakeUser("u-1", "person@example.test")
    calls = {"n": 0}
    original = fake.auth.get_user

    def counted(token):
        calls["n"] += 1
        return original(token)

    fake.auth.get_user = counted
    monkeypatch.setattr(auth_module, "get_db", lambda: fake)

    for _ in range(7):
        assert get_current_user(_bearer("good-token")) == CurrentUser("u-1", "person@example.test")

    assert calls["n"] == 1, "a page load should cost one verification, not seven"


def test_a_rejected_token_is_asked_about_every_time(monkeypatch):
    """Only successes are remembered. Remembering a rejection would keep telling a
    session that has just been renewed that it is still invalid."""
    fake = FakeDatabase()
    calls = {"n": 0}

    def counted(_token):
        calls["n"] += 1
        raise RuntimeError("no such user")

    fake.auth.get_user = counted
    monkeypatch.setattr(auth_module, "get_db", lambda: fake)

    for _ in range(3):
        with pytest.raises(auth_module.AuthError):
            get_current_user(_bearer("nonsense"))

    assert calls["n"] == 3


def test_a_remembered_token_is_forgotten_once_it_expires(monkeypatch):
    fake = FakeDatabase()
    fake.auth.users["good-token"] = FakeUser("u-1", "person@example.test")
    calls = {"n": 0}
    original = fake.auth.get_user

    def counted(token):
        calls["n"] += 1
        return original(token)

    fake.auth.get_user = counted
    monkeypatch.setattr(auth_module, "get_db", lambda: fake)

    get_current_user(_bearer("good-token"))
    now = [auth_module.time.monotonic()]
    monkeypatch.setattr(auth_module.time, "monotonic", lambda: now[0])
    now[0] += auth_module._VERIFIED_FOR_SECONDS + 1

    get_current_user(_bearer("good-token"))

    assert calls["n"] == 2, "the answer must not outlive its window"


def test_two_users_are_never_confused_for_each_other(monkeypatch):
    """The memory is keyed on the token, and getting that wrong would hand one person
    another person's projects — the one bug in here that matters."""
    fake = FakeDatabase()
    fake.auth.users["token-a"] = FakeUser("u-a", "a@example.test")
    fake.auth.users["token-b"] = FakeUser("u-b", "b@example.test")
    monkeypatch.setattr(auth_module, "get_db", lambda: fake)

    assert get_current_user(_bearer("token-a")).id == "u-a"
    assert get_current_user(_bearer("token-b")).id == "u-b"
    assert get_current_user(_bearer("token-a")).id == "u-a"
