"""The one authentication endpoint.

Signing in and signing out happen in the browser against Supabase directly, so there is
no `/auth/login` here and there should not be — a login route on this server would mean
this server handling passwords. What the API does owe a client is an answer to "is this
token still good, and who does it belong to", which is what `/auth/me` is for.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.dependencies import CurrentUser, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class CurrentUserResponse(BaseModel):
    id: str
    email: str | None = None


@router.get("/me", response_model=CurrentUserResponse)
def get_me(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Who the bearer token belongs to. 401 if it is missing, invalid or expired."""
    return user
