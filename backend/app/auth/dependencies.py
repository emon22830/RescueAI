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


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> CurrentUser:
    """Verify the bearer token against Supabase Auth and return who it belongs to."""
    token = credentials.credentials.strip() if credentials else ""
    if not token:
        raise AuthError("Missing bearer token")

    try:
        response = get_db().auth.get_user(token)
    except Exception as error:
        raise AuthError("Invalid or expired session") from error

    if response is None or response.user is None:
        raise AuthError("Invalid or expired session")

    return CurrentUser(id=response.user.id, email=response.user.email)
