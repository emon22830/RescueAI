"""FastAPI entrypoint: CORS, the routers, and the error handling they share."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from postgrest import APIError

from app.ai.llm import LLMError
from app.api import actions, analysis, ask, integrations, notifications, projects
from app.auth import AuthError
from app.auth.router import router as auth_router
from app.config import ConfigurationError, settings
from app.projects.service import ProjectNotFound
from app import scheduler

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Own the scheduler's lifetime: it starts with the app and is stopped cleanly on
    shutdown, so a reload does not leave a tick running against a closing database."""
    await scheduler.start()
    yield
    await scheduler.stop()


app = FastAPI(title="RescueAI", version="0.5.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
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


@app.exception_handler(ValueError)
async def handle_invalid_request(request: Request, error: ValueError) -> JSONResponse:
    """A value the service refused — a schedule below the floor, an action missing the
    field it needs. The message is written to be read by a user, so it is passed on."""
    return JSONResponse(status_code=400, content={"detail": str(error)})


@app.exception_handler(APIError)
async def handle_database_error(request: Request, error: APIError) -> JSONResponse:
    logger.exception("Supabase request failed")
    return JSONResponse(status_code=502, content={"detail": f"Database error: {error.message}"})


app.include_router(auth_router)
app.include_router(projects.router)
app.include_router(analysis.router)
app.include_router(actions.router)
app.include_router(integrations.router)
app.include_router(integrations.oauth_router)
app.include_router(ask.router)
app.include_router(notifications.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
