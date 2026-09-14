"""Supabase client. One instance per thread, created on first use.

Not one shared instance. FastAPI runs every `def` endpoint in a worker thread, so the
project page's seven parallel requests reach this module from seven threads at once.
A single client means a single `httpx` client, and Supabase speaks HTTP/2 — so those
requests were being multiplexed over one TCP connection whose read loop is not safe to
drive from several threads. The collision surfaced as `httpx.ReadError` on whichever
request lost, which reached the browser as a 500 and blanked a page whose data was
perfectly fine.

One client per thread costs a handful of connections and removes the sharing entirely.
"""

import threading

from supabase import Client, create_client

from app.config import settings

_local = threading.local()


def get_db() -> Client:
    client: Client | None = getattr(_local, "client", None)
    if client is None:
        settings.require("supabase_url", "supabase_service_key")
        client = create_client(settings.supabase_url, settings.supabase_service_key)
        _local.client = client
    return client
