"""Who is calling. Every request from the frontend carries the signed-in user's Supabase
session token as `Authorization: Bearer <token>`; this is the only place that checks it.

We do not store users, hash passwords or mint tokens — Supabase Auth owns all of that.
The frontend signs in against it directly and we verify the token it was given. What
this file adds is the half Supabase cannot do for us: turning that token into a user id
the rest of the backend can check ownership against.

The backend talks to Supabase with the service key (it bypasses row-level security by
design — see projects/service.py), so ownership is enforced in application code, not in
Postgres. That means every route that touches a project must depend on `get_current_user`
and every service function must be given the resulting user id to check against.
"""

import threading
import time
from dataclasses import dataclass

from fastapi import Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.supabase import get_db

# Declaring the scheme is what puts the padlock on every protected route in /docs and
# gives the "Authorize" box a place to paste a session token. `auto_error=False` so a
# missing header raises our own AuthError — and so answers 401 with our wording —
# instead of FastAPI's bare 403.
bearer_scheme = HTTPBearer(
    scheme_name="Supabase session",
    description="The `access_token` from the frontend's Supabase session.",
    auto_error=False,
)


class AuthError(RuntimeError):
    """No valid session. Surfaced to the client as 401."""


@dataclass
class CurrentUser:
    id: str
    email: str | None


# Verifying a token is a network round trip to Supabase Auth, and one screen opens
# seven requests at once — so an unremembered answer costs seven hops before any of
# them has looked at a project. The same token verifies to the same user for the life
# of that token, so the answer is held briefly.
#
# The window is deliberately short. A Supabase access token is a JWT that stays valid
# for an hour on its own terms, so remembering a good one for a minute does not extend
# anyone's access — it only stops us asking the same question seven times a second.
# Only successes are remembered: a rejection must be re-asked every time, so a session
# that has just been renewed is never told it is still invalid.
_VERIFIED_FOR_SECONDS = 60

_verified: dict[str, tuple[float, CurrentUser]] = {}
_verified_lock = threading.Lock()


def _remembered(token: str) -> CurrentUser | None:
    with _verified_lock:
        entry = _verified.get(token)
        if entry is None:
            return None
        expires_at, user = entry
        if expires_at <= time.monotonic():
            del _verified[token]
            return None
        return user


def _remember(token: str, user: CurrentUser) -> None:
    now = time.monotonic()
    with _verified_lock:
        # Tokens rotate, so without this the map would grow for the life of the process.
        for stale in [key for key, (expires_at, _) in _verified.items() if expires_at <= now]:
            del _verified[stale]
        _verified[token] = (now + _VERIFIED_FOR_SECONDS, user)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> CurrentUser:
    """Verify the bearer token against Supabase Auth and return who it belongs to."""
    token = credentials.credentials.strip() if credentials else ""
    if not token:
        raise AuthError("Missing bearer token")

    remembered = _remembered(token)
    if remembered is not None:
        return remembered

    try:
        response = get_db().auth.get_user(token)
    except Exception as error:
        raise AuthError("Invalid or expired session") from error

    if response is None or response.user is None:
        raise AuthError("Invalid or expired session")

    user = CurrentUser(id=response.user.id, email=response.user.email)
    _remember(token, user)
    return user
