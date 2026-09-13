"""The Google OAuth flow, and one access token per project.

Gmail, Drive and Calendar are three APIs behind one OAuth consent, so a project
connects Google once and gets all three. The client id and secret identify *this
application* to Google and stay in backend/.env; the refresh token is one project's
grant to one Google account, and is stored encrypted against that project alone.

The refresh token is requested for these scopes:
    gmail.readonly · gmail.send · drive.readonly · calendar.events
"""

import time

import httpx

from app.config import settings

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
TIMEOUT = 20.0

SCOPES = (
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/userinfo.email",
)

# project_id -> (access token, when it expires). An access token lasts an hour; the
# refresh token it is minted from is read from the database each time it runs out.
_cache: dict[str, tuple[str, float]] = {}


class GoogleError(RuntimeError):
    """Google refused the request. The message is whatever Google itself said."""


def redirect_uri() -> str:
    """Where Google sends the browser back to. Must be registered, character for
    character, as an authorized redirect URI on the OAuth client."""
    return f"{settings.backend_url.rstrip('/')}/integrations/google/callback"


def authorize_url(state: str) -> str:
    """The consent screen to send the user to.

    `access_type=offline` with `prompt=consent` is what makes Google return a refresh
    token — without both, a user who has already consented gets an access token only,
    and the connection silently dies an hour later.
    """
    settings.require("google_client_id", "google_client_secret")
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return str(httpx.URL(AUTH_URL, params=params))


def exchange_code(code: str) -> dict:
    """Trade the one-time code from the callback for a refresh token.

    Returns the refresh token and the Google account it belongs to, so the
    Connections page can show *which* mailbox a project is reading.
    """
    settings.require("google_client_id", "google_client_secret")
    response = httpx.post(
        TOKEN_URL,
        data={
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "code": code,
            "redirect_uri": redirect_uri(),
            "grant_type": "authorization_code",
        },
        timeout=TIMEOUT,
    )
    if response.status_code >= 400:
        raise GoogleError(f"Google rejected the authorization code: {response.text}")

    body = response.json()
    refresh_token = body.get("refresh_token")
    if not refresh_token:
        raise GoogleError(
            "Google returned no refresh token. Revoke this app at "
            "myaccount.google.com/permissions and connect again."
        )

    return {"refresh_token": refresh_token, "email": _email(body["access_token"])}


def is_connected(project_id: str) -> bool:
    """True when this project has granted Google access. Cheap enough to call from
    each of the three integrations at the top of collect_evidence."""
    from app.projects import service

    return service.get_integration_credential(project_id, "google") is not None


def access_token(project_id: str) -> str:
    """A valid access token for this project, refreshed only when the cached one is
    about to expire. Raises GoogleError when the project has not connected Google."""
    cached = _cache.get(project_id)
    if cached and time.time() < cached[1]:
        return cached[0]

    # Imported here: service imports the integrations, so importing it at module level
    # would be a cycle.
    from app.projects import service

    credential = service.get_integration_credential(project_id, "google")
    if credential is None:
        raise GoogleError("This project has not connected Google")

    token, expires_in = _refresh(credential["token"])
    _cache[project_id] = (token, time.time() + expires_in - 60)
    return token


def headers(project_id: str) -> dict[str, str]:
    """Authorization header every Google request in this folder uses."""
    return {"Authorization": f"Bearer {access_token(project_id)}"}


def forget(project_id: str) -> None:
    """Drop the cached access token — called when a project disconnects Google, so a
    reconnect never serves a token minted from the old grant."""
    _cache.pop(project_id, None)


def _refresh(refresh_token: str) -> tuple[str, float]:
    settings.require("google_client_id", "google_client_secret")
    response = httpx.post(
        TOKEN_URL,
        data={
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=TIMEOUT,
    )
    if response.status_code >= 400:
        raise GoogleError(
            f"Google would not refresh this project's token: {response.text}. "
            "The grant may have been revoked — disconnect and connect again."
        )
    body = response.json()
    return body["access_token"], float(body.get("expires_in", 3600))


def _email(token: str) -> str:
    """Which Google account just consented. Best effort — a connection is still valid
    if this fails, so it never raises."""
    try:
        response = httpx.get(
            USERINFO_URL, headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT
        )
        return response.json().get("email", "") if response.status_code < 400 else ""
    except httpx.HTTPError:
        return ""
