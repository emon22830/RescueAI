import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

import app.auth.dependencies as auth_dependencies
from app.auth import CurrentUser, get_current_user
from app.config import settings
from app.main import app
from app.projects import service
from tests.fake_db import FakeDatabase

# The user every `client` fixture request is signed in as, unless a test overrides
# get_current_user itself (see test_auth.py for the real verification path).
OWNER_ID = "11111111-1111-1111-1111-111111111111"


@pytest.fixture(autouse=True)
def forget_verified_tokens():
    """A verified token is remembered for a minute so one page load is not seven round
    trips to Supabase Auth. That memory is process-wide, so a test must never inherit
    another test's answer for the same token string."""
    auth_dependencies._verified.clear()
    yield
    auth_dependencies._verified.clear()


@pytest.fixture(autouse=True)
def encryption_key(monkeypatch):
    """Every test gets a real key so connect_integration can encrypt a token, without
    needing CREDENTIAL_ENCRYPTION_KEY set in a real backend/.env."""
    monkeypatch.setattr(settings, "credential_encryption_key", Fernet.generate_key().decode())


@pytest.fixture(autouse=True)
def db(monkeypatch) -> FakeDatabase:
    """Swap the Supabase client for an in-memory one.

    Autouse, so no test can reach the real database by forgetting to ask for it — an
    integration whose `collect_evidence` looks up a stored credential would otherwise
    quietly query the live Supabase project on every run.
    """
    fake = FakeDatabase()
    monkeypatch.setattr(service, "get_db", lambda: fake)
    return fake


@pytest.fixture
def client(db) -> TestClient:
    """A signed-in client. Auth is verified for real in test_auth.py; every other test
    only cares about what happens once a user is known, so the dependency is swapped
    for a fixed one here rather than every test carrying a bearer token."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(OWNER_ID, "owner@example.com")
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()
