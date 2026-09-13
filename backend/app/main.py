"""FastAPI entrypoint: CORS, the three routers, and the error handling they share."""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from postgrest import APIError

from app.api import actions, analysis, projects
from app.config import ConfigurationError, settings
from app.projects.service import ProjectNotFound

logger = logging.getLogger(__name__)

app = FastAPI(title="AI Project Rescue", version="0.1.0")

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


@app.exception_handler(ProjectNotFound)
async def handle_project_not_found(request: Request, error: ProjectNotFound) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(error)})


@app.exception_handler(APIError)
async def handle_database_error(request: Request, error: APIError) -> JSONResponse:
    logger.exception("Supabase request failed")
    return JSONResponse(status_code=502, content={"detail": f"Database error: {error.message}"})


app.include_router(projects.router)
app.include_router(analysis.router)
app.include_router(actions.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
