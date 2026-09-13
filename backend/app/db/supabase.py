"""Supabase client. One shared instance, created on first use."""

from functools import lru_cache

from supabase import Client, create_client

from app.config import settings


@lru_cache
def get_db() -> Client:
    settings.require("supabase_url", "supabase_service_key")
    return create_client(settings.supabase_url, settings.supabase_service_key)
