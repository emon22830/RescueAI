"""Authentication: who is calling, and the keys that protect what they connected.

Three files, one job each:

- `dependencies.py` — verifies the caller's Supabase session on every request.
- `security.py`     — encrypts the third-party tokens a project connects, and signs
                      the OAuth state that has to survive a round trip through Google.
- `router.py`       — `GET /auth/me`, so the API itself can answer "who am I".

Import from the package, not from the modules inside it:

    from app.auth import CurrentUser, get_current_user

`security` stays a module import (`from app.auth import security`) because its names
— `encrypt`, `decrypt` — only read correctly when they are qualified.

See `app/auth/README.md` for how the whole flow fits together.
"""

from app.auth.dependencies import AuthError, CurrentUser, bearer_scheme, get_current_user
from app.auth.security import CredentialError, StateError

__all__ = [
    "AuthError",
    "CredentialError",
    "CurrentUser",
    "StateError",
    "bearer_scheme",
    "get_current_user",
]
