"""Encrypting third-party credentials at rest. This is the only place that touches Fernet.

Every project can connect its own Slack/Linear/GitHub token, so the token has to live
in the database rather than backend/.env — and it has to be encrypted there, since the
integrations table is otherwise readable to anyone with database access.

It also signs the `state` that survives Google's OAuth redirect. That round trip leaves
our app entirely, so the state coming back has to prove it is the one we sent: it carries
which project is being connected, and nothing else may forge it.
"""

import json

from cryptography.fernet import Fernet, InvalidToken

from app.auth.dependencies import AuthError
from app.config import settings

# How long a user has to finish the Google consent screen before the state expires.
STATE_TTL_SECONDS = 600


class CredentialError(RuntimeError):
    """A stored credential could not be decrypted — usually a rotated encryption key."""


class StateError(AuthError):
    """An OAuth state was forged, tampered with, or took too long to come back.

    It is an AuthError so the handler in main.py answers 401 — a state that does not
    verify is a caller who cannot prove who they are.
    """


def encrypt(value: str) -> str:
    settings.require("credential_encryption_key")
    return Fernet(settings.credential_encryption_key.encode()).encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    settings.require("credential_encryption_key")
    try:
        return Fernet(settings.credential_encryption_key.encode()).decrypt(value.encode()).decode()
    except InvalidToken as error:
        raise CredentialError("A stored credential could not be decrypted") from error


def sign_state(**claims: str) -> str:
    """Pack the claims into a tamper-proof, expiring string to hand to an OAuth provider."""
    settings.require("credential_encryption_key")
    payload = json.dumps(claims).encode()
    return Fernet(settings.credential_encryption_key.encode()).encrypt(payload).decode()


def verify_state(state: str) -> dict:
    """The claims from `sign_state`, or StateError if it was forged or has expired."""
    settings.require("credential_encryption_key")
    try:
        payload = Fernet(settings.credential_encryption_key.encode()).decrypt(
            state.encode(), ttl=STATE_TTL_SECONDS
        )
    # A tampered state is InvalidToken; a malformed one never reaches Fernet's own
    # check and surfaces as a base64 error instead. Both mean the same thing here.
    except (InvalidToken, ValueError, TypeError) as error:
        raise StateError("This sign-in link is invalid or has expired — try connecting again") from error
    return json.loads(payload)
