"""One Supabase client per thread, and what happens when one cannot reach Supabase.

Found in production: opening a project showed "Project unavailable — the server hit an
unexpected error" while the project's data was perfectly fine. The page opens seven
requests at once, FastAPI runs every `def` endpoint in a worker thread, and all seven
shared one Supabase client — so one `httpx` client, and one HTTP/2 connection being
read from seven threads. Whichever request lost the race got `httpx.ReadError`, which
nothing handled, so a healthy page rendered as a server crash.
"""

import threading

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import ConfigurationError
from app.db import supabase
from app.projects import service


@pytest.fixture
def stub_client(monkeypatch):
    """Count the clients created, without creating a real one."""
    made: list[object] = []

    def create_client(_url, _key):
        client = object()
        made.append(client)
        return client

    monkeypatch.setattr(supabase, "create_client", create_client)
    monkeypatch.setattr(supabase.settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(supabase.settings, "supabase_service_key", "service-key")
    monkeypatch.setattr(supabase, "_local", threading.local())
    return made


def test_two_threads_never_share_one_client(stub_client):
    """The fix for the bug above. A shared client means a shared HTTP/2 connection, and
    that connection is not safe to read from two threads at once."""
    seen: dict[int, object] = {}

    def grab(index: int) -> None:
        seen[index] = supabase.get_db()

    threads = [threading.Thread(target=grab, args=(i,)) for i in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(seen) == 4
    assert len({id(client) for client in seen.values()}) == 4, "each thread needs its own"


def test_one_thread_reuses_its_own_client(stub_client):
    """Per-thread, not per-call — a new connection pool on every request would trade
    one problem for a slower one."""
    assert supabase.get_db() is supabase.get_db()
    assert len(stub_client) == 1


def test_a_missing_variable_is_still_named(monkeypatch):
    """The 503 that tells a user which variable to fill in must survive the change."""
    monkeypatch.setattr(supabase, "_local", threading.local())
    monkeypatch.setattr(supabase.settings, "supabase_url", "")
    monkeypatch.setattr(supabase.settings, "supabase_service_key", "")

    with pytest.raises(ConfigurationError, match="SUPABASE_URL"):
        supabase.get_db()


def test_an_unreachable_database_says_so_instead_of_a_bare_500(
    client: TestClient, monkeypatch
):
    """Defence in depth for the same bug: any transport failure reaching Supabase must
    read as "could not reach the database", not as an unexplained server error."""

    def unreachable():
        raise httpx.ReadError("[Errno 35] Resource temporarily unavailable")

    monkeypatch.setattr(service, "get_db", unreachable)

    response = client.get("/projects")

    assert response.status_code == 502
    detail = response.json()["detail"]
    assert "Could not reach the database" in detail
    assert "ReadError" in detail
