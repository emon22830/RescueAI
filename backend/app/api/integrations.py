"""Which external apps a project has connected, and how to connect the rest.

Slack, Linear and GitHub are "token" apps: a user pastes a credential here, it is
verified against the real API, then stored encrypted for this project alone — see
projects/service.py connect_integration. Gmail, Drive and Calendar are still one
shared Google OAuth app configured in backend/.env for the whole deployment (Phase 2
moves them to the same per-project model), so their status still comes from settings
and they have no connect/disconnect endpoint yet.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.auth import security
from app.agents.state import Source
from app.auth import CurrentUser, get_current_user
from app.config import settings
from app.integrations import google_auth
from app.integrations.asana import AsanaError
from app.integrations.github import GitHubError
from app.integrations.jira import JiraError
from app.integrations.linear import LinearError
from app.integrations.notion import NotionError
from app.integrations.slack import SlackError
from app.integrations.trello import TrelloError
from app.projects import service

router = APIRouter(prefix="/projects/{project_id}/integrations", tags=["integrations"])

# Google's redirect comes back from Google, not from our frontend, so it cannot carry a
# bearer token. It lives outside the project-scoped router and proves who it is with the
# signed `state` instead.
oauth_router = APIRouter(prefix="/integrations/google", tags=["integrations"])

logger = logging.getLogger(__name__)

GOOGLE_SETUP_URL = "https://console.cloud.google.com/apis/credentials"

# Every app the agent can investigate, in the order the page lists them. `writes_back`
# is true only where execute_action() actually does something; the rest are read-only.
CATALOG: list[dict] = [
    # Listed in the order the workflow reads them — what people said, what was built,
    # what the plan says, what was agreed — which is the same order SOURCE_ORDER uses
    # on the frontend, so the Connections page and every app strip agree.
    {"id": "slack", "mode": "token", "writes_back": True, "setup_url": "https://api.slack.com/apps"},
    # Gmail, Drive and Calendar are three APIs behind one Google consent: connecting any
    # of them connects all three, and they share the project's single 'google' row.
    {"id": "gmail", "mode": "oauth", "writes_back": True, "setup_url": GOOGLE_SETUP_URL},
    {
        "id": "github",
        "mode": "token",
        "writes_back": True,
        "setup_url": "https://github.com/settings/personal-access-tokens",
    },
    {"id": "linear", "mode": "token", "writes_back": True, "setup_url": "https://linear.app/settings/api"},
    {
        "id": "jira",
        "mode": "token",
        "writes_back": True,
        "setup_url": "https://id.atlassian.com/manage-profile/security/api-tokens",
    },
    {
        "id": "asana",
        "mode": "token",
        "writes_back": True,
        "setup_url": "https://app.asana.com/0/my-apps",
    },
    {"id": "trello", "mode": "token", "writes_back": True, "setup_url": "https://trello.com/power-ups/admin"},
    {"id": "drive", "mode": "oauth", "writes_back": False, "setup_url": GOOGLE_SETUP_URL},
    {
        "id": "notion",
        "mode": "token",
        "writes_back": True,
        "setup_url": "https://www.notion.so/my-integrations",
    },
    {"id": "calendar", "mode": "oauth", "writes_back": True, "setup_url": GOOGLE_SETUP_URL},
]

VERIFY_ERRORS = (
    SlackError, LinearError, GitHubError, JiraError, AsanaError, TrelloError, NotionError,
)


class IntegrationStatus(BaseModel):
    """One app and whether this project can reach it."""

    id: Source
    mode: str  # "token" — connected per project from this page — or "oauth" — set in .env
    connected: bool
    metadata: dict = {}  # team/repo/user info recorded when a token app was connected
    writes_back: bool  # whether an approved action can be executed here
    setup_url: str  # where the user goes to issue the credential
    variables: list[str] = []  # oauth apps only: the env vars still needed


class ConnectIntegrationRequest(BaseModel):
    """The credential, plus whatever else that one app needs to be reachable.

    Everything but `token` is stored as metadata and read back by the owner, so nothing
    secret belongs here. Trello's `key` is the exception that proves it: it identifies
    the application, not the user, and Trello's own docs ship it in client-side code —
    the token beside it is the secret half, and that is what gets encrypted.
    """

    token: str
    repo: str = ""  # github only
    channel_ids: str = ""  # slack only, optional
    site: str = ""  # jira only — acme.atlassian.net
    email: str = ""  # jira only — the account the API token was issued for
    project_key: str = ""  # jira only, optional — narrows collection to one project
    key: str = ""  # trello only — the API key that pairs with the token
    workspace: str = ""  # asana only, optional — defaults to the token's first workspace


@router.get("", response_model=list[IntegrationStatus])
def list_integrations(project_id: str, user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    connected = service.list_integration_status(project_id, user.id)
    return [_status(app, connected) for app in CATALOG]


@router.post("/{provider}/connect", response_model=IntegrationStatus)
def connect_integration(
    project_id: str,
    provider: Source,
    body: ConnectIntegrationRequest,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    if provider not in service.TOKEN_INTEGRATIONS:
        raise HTTPException(status_code=400, detail=f"{provider} is not connected per project yet")

    extra = {
        name: value
        for name, value in {
            "repo": body.repo,
            "channel_ids": body.channel_ids,
            "site": body.site,
            "email": body.email,
            "project_key": body.project_key,
            "key": body.key,
            "workspace": body.workspace,
        }.items()
        if value
    }
    try:
        service.connect_integration(project_id, user.id, provider, body.token, extra)
    except VERIFY_ERRORS as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    connected = service.list_integration_status(project_id, user.id)
    app = next(app for app in CATALOG if app["id"] == provider)
    return _status(app, connected)


@router.delete("/{provider}", status_code=204)
def disconnect_integration(
    project_id: str, provider: Source, user: CurrentUser = Depends(get_current_user)
) -> None:
    # Disconnecting any one Google app revokes all three — they are one grant.
    stored = "google" if provider in service.GOOGLE_INTEGRATIONS else provider
    if stored != "google" and provider not in service.TOKEN_INTEGRATIONS:
        raise HTTPException(status_code=400, detail=f"{provider} is not connected per project")
    service.disconnect_integration(project_id, user.id, stored)


class AuthorizeResponse(BaseModel):
    """Where to send the browser to ask the user for Google's consent."""

    url: str


@router.get("/google/authorize", response_model=AuthorizeResponse)
def authorize_google(project_id: str, user: CurrentUser = Depends(get_current_user)) -> dict:
    """Start the Google connection for this project.

    Ownership is checked here, while we still have a bearer token, and then carried
    across the redirect in a signed state — the callback cannot re-check it any other way.
    """
    service.get_project(project_id, user.id)
    state = security.sign_state(project_id=project_id, owner_id=user.id)
    return {"url": google_auth.authorize_url(state)}


@oauth_router.get("/callback")
def google_callback(
    state: str, code: str = "", error: str = ""
) -> RedirectResponse:
    """Where Google sends the browser back. Trades the code for a refresh token and
    stores it against the project named in the signed state.

    This always redirects back into the app rather than returning JSON — a person is
    looking at this URL, not a script.
    """
    claims = security.verify_state(state)
    project_id, owner_id = claims["project_id"], claims["owner_id"]
    back = f"{settings.app_url}/app/projects/{project_id}/connections"

    if error or not code:
        return RedirectResponse(f"{back}?google={error or 'cancelled'}", status_code=303)

    try:
        service.connect_google(project_id, owner_id, code)
    except (google_auth.GoogleError, ValueError) as failure:
        logger.warning("Google connect failed for project %s: %s", project_id, failure)
        return RedirectResponse(f"{back}?google=failed", status_code=303)

    return RedirectResponse(f"{back}?google=connected", status_code=303)


def _status(app: dict, connected: dict[str, dict]) -> dict:
    if app["mode"] == "oauth":
        # All three read the project's single Google grant, so they report as one.
        row = connected.get("google")
        return {
            "id": app["id"],
            "mode": "oauth",
            "connected": row is not None,
            "metadata": row["metadata"] if row else {},
            "writes_back": app["writes_back"],
            "setup_url": app["setup_url"],
            "variables": [] if settings.google_client_id else ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
        }

    row = connected.get(app["id"])
    return {
        "id": app["id"],
        "mode": "token",
        "connected": row is not None,
        "metadata": row["metadata"] if row else {},
        "writes_back": app["writes_back"],
        "setup_url": app["setup_url"],
        "variables": [],
    }
