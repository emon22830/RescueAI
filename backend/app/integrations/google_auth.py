"""One Google access token, minted from the refresh token in backend/.env.

Gmail, Drive and Calendar are three APIs behind one OAuth client, so the token
exchange lives here instead of three times over. Nothing else is shared — each
integration builds its own requests.

The refresh token must have been issued for these scopes:
    gmail.readonly · gmail.send · drive.readonly · calendar.events
"""

import time

import httpx

from app.config import settings

TOKEN_URL = "https://oauth2.googleapis.com/token"
TIMEOUT = 20.0

_token = ""
_expires_at = 0.0


def is_connected() -> bool:
    """True when backend/.env has the three Google variables filled in."""
    return bool(
        settings.google_client_id and settings.google_client_secret and settings.google_refresh_token
    )


def access_token() -> str:
    """A valid access token, refreshed only when the cached one is about to expire."""
    global _token, _expires_at

    if _token and time.time() < _expires_at:
        return _token

    settings.require("google_client_id", "google_client_secret", "google_refresh_token")
    response = httpx.post(
        TOKEN_URL,
        data={
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "refresh_token": settings.google_refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    body = response.json()

    _token = body["access_token"]
    _expires_at = time.time() + body.get("expires_in", 3600) - 60
    return _token


def headers() -> dict[str, str]:
    """Authorization header every Google request in this folder uses."""
    return {"Authorization": f"Bearer {access_token()}"}
