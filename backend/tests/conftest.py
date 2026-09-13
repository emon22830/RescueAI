import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.projects import service
from tests.fake_db import FakeDatabase


@pytest.fixture
def db(monkeypatch) -> FakeDatabase:
    """Swap the Supabase client for an in-memory one."""
    fake = FakeDatabase()
    monkeypatch.setattr(service, "get_db", lambda: fake)
    return fake


@pytest.fixture
def client(db) -> TestClient:
    return TestClient(app)
