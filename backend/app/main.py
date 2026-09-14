"""FastAPI entrypoint: CORS, the routers, and the error handling they share."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from httpx import HTTPError
from postgrest import APIError

from app.ai.llm import LLMError, ProviderError, explain_llm_error
from app.api import actions, analysis, ask, integrations, notifications, projects
from app.auth import AuthError, CredentialError
from app.auth.router import router as auth_router
from app.config import ConfigurationError, settings
from app.projects import service
from app.projects.service import ProjectNotFound
from app import scheduler

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Own the scheduler's lifetime: it starts with the app and is stopped cleanly on
    shutdown, so a reload does not leave a tick running against a closing database."""
    # The allowed origins decide whether the deployed frontend can talk to this API at
    # all, and a wrong one shows up in the browser as a bare network error with nothing
    # in the server log. Say what they are, once, where a deploy log will show it.
    logger.info("CORS allowed origins: %s", ", ".join(settings.allowed_origins) or "(none)")
    await scheduler.start()
    yield
    await scheduler.stop()


app = FastAPI(title="RescueAI", version="0.6.1", lifespan=lifespan)


@app.middleware("http")
async def answer_unhandled_errors(request: Request, call_next):
    """Turn a crash into a response, inside the CORS layer.

    Starlette answers an unhandled exception from its outermost middleware — outside
    CORS — so the 500 goes back with no `access-control-allow-origin`. The browser then
    refuses to show it and `fetch` rejects, so a backend that crashed on one endpoint
    reads in the UI as a backend that is down. Everything the handlers below name is
    already a response by the time it reaches here; this only catches what nothing
    else did.

    Registered before the CORS middleware on purpose: the last middleware added is the
    outermost, so adding CORS after this one puts it outside, where it can still stamp
    its headers onto what we return.
    """
    try:
        return await call_next(request)
    except Exception:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "The server hit an unexpected error. Check the backend logs."},
        )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ConfigurationError)
async def handle_configuration_error(request: Request, error: ConfigurationError) -> JSONResponse:
    """The server is running but not set up yet — tell the caller exactly what is missing."""
    return JSONResponse(status_code=503, content={"detail": str(error)})


@app.exception_handler(AuthError)
async def handle_auth_error(request: Request, error: AuthError) -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": str(error)})


@app.exception_handler(ProjectNotFound)
async def handle_project_not_found(request: Request, error: ProjectNotFound) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(error)})


@app.exception_handler(LLMError)
async def handle_llm_error(request: Request, error: LLMError) -> JSONResponse:
    """The model answered with nothing usable. Say so in the model's own terms — an
    unhandled LLMError reaches the UI as a bare 500, which reads as the agent simply
    not replying."""
    logger.exception("LLM request failed")
    return JSONResponse(status_code=502, content={"detail": str(error)})


@app.exception_handler(ProviderError)
async def handle_provider_error(request: Request, error: ProviderError) -> JSONResponse:
    """The LLM provider refused or could not serve the request.

    `LLMError` above is the model answering with something unusable; this is the API in
    front of it saying no — out of quota, rate limited, key rejected. It arrived as an
    unhandled exception, so Ask spent a minute and a half on retries and then showed
    "The server hit an unexpected error", which names neither the cause nor the fix."""
    logger.exception("LLM provider refused the request")
    return JSONResponse(status_code=502, content={"detail": explain_llm_error(error)})


@app.exception_handler(CredentialError)
async def handle_credential_error(request: Request, error: CredentialError) -> JSONResponse:
    """A stored token cannot be decrypted, which means CREDENTIAL_ENCRYPTION_KEY is not
    the key that encrypted it — rotated, or different between local and deployed. The
    token is unrecoverable; say so and name what fixes it, rather than 500ing."""
    logger.exception("Credential decryption failed")
    return JSONResponse(
        status_code=503,
        content={
            "detail": "A stored credential could not be decrypted. CREDENTIAL_ENCRYPTION_KEY "
            "has changed since this app was connected — reconnect it from the project's "
            "Connections page.",
        },
    )


@app.exception_handler(ValueError)
async def handle_invalid_request(request: Request, error: ValueError) -> JSONResponse:
    """A value the service refused — a schedule below the floor, an action missing the
    field it needs. The message is written to be read by a user, so it is passed on."""
    return JSONResponse(status_code=400, content={"detail": str(error)})


@app.exception_handler(APIError)
async def handle_database_error(request: Request, error: APIError) -> JSONResponse:
    logger.exception("Supabase request failed")
    return JSONResponse(status_code=502, content={"detail": f"Database error: {error.message}"})


@app.exception_handler(HTTPError)
async def handle_transport_error(request: Request, error: HTTPError) -> JSONResponse:
    """The call to Supabase never completed — a dropped connection, a timeout, a reset.

    `APIError` above is Supabase answering with a problem; this is Supabase not
    answering at all, and it arrives as an httpx exception that nothing else names.
    Left unhandled it became "The server hit an unexpected error", which sends whoever
    reads it looking for a bug in code that was fine. Say the request did not get there
    and that retrying is the right move."""
    logger.exception("Could not reach Supabase on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=502,
        content={
            "detail": f"Could not reach the database ({type(error).__name__}). "
            "The request did not complete — try again."
        },
    )


app.include_router(auth_router)
app.include_router(projects.router)
app.include_router(analysis.router)
app.include_router(actions.router)
app.include_router(integrations.router)
app.include_router(integrations.oauth_router)
app.include_router(ask.router)
app.include_router(notifications.router)


@app.get("/health/ready", tags=["health"])
def ready() -> dict[str, str]:
    """Whether this backend can actually serve a request.

    Separate from `/health` on purpose. `/health` must keep answering `ok` whenever the
    process is alive — a platform health check that goes red during a database blip
    would restart or roll back a service whose code is fine. This one reaches the
    database, so it can say no, and nothing automated is wired to it.
    """
    service.check_database()
    return {"status": "ready"}


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Whether the service is up, and which build is answering.

    The commit is what makes a deploy verifiable from outside. Without it a fix that is
    still rolling out looks exactly like a fix that is live, and the only way to tell
    them apart is to find a behaviour that changed and probe for it — which does not
    exist for a fix to an error path. `RENDER_GIT_COMMIT` is set by Render on every
    service and is empty everywhere else, so locally this reads "local".
    """
    return {
        "status": "ok",
        "version": app.version,
        "commit": settings.render_git_commit[:7] or "local",
    }
