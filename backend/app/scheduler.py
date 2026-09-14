"""The loop that makes the agent run without being asked.

One asyncio task, started with the app and stopped with it. Every tick it asks the
service which projects are due and runs each one to completion, in a worker thread —
the whole analysis path is blocking (httpx, Supabase, the LLM), so running it on the
event loop would freeze every other request while a project is analysed.

Deliberately in-process: one background task, no queue, no worker, no broker. That
holds as long as RescueAI runs as a single instance. Running two would have both of
them pick up the same due project, so the day this deploys to more than one process,
this is the file that has to grow a lock — see `due_projects` in projects/service.py.
"""

import asyncio
import logging

from app.config import settings
from app.projects import service

logger = logging.getLogger(__name__)

_task: asyncio.Task | None = None


async def start() -> None:
    """Begin ticking, unless this deployment has no database or has turned it off."""
    global _task

    if not settings.scheduler_enabled:
        logger.info("Scheduler disabled by SCHEDULER_ENABLED")
        return
    if not (settings.supabase_url and settings.supabase_service_key):
        logger.info("Scheduler idle: Supabase is not configured")
        return

    _task = asyncio.create_task(_loop())
    logger.info("Scheduler started, ticking every %ss", settings.scheduler_tick_seconds)


async def stop() -> None:
    """Stop ticking and wait for the current tick to finish."""
    global _task

    if _task is None:
        return
    _task.cancel()
    try:
        await _task
    except asyncio.CancelledError:
        pass
    _task = None


async def _loop() -> None:
    while True:
        try:
            await tick()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — a bad tick must never end the loop
            logger.exception("Scheduler tick failed")
        await asyncio.sleep(settings.scheduler_tick_seconds)


async def tick() -> int:
    """Run every project whose schedule is due. Returns how many were run.

    Projects are run one after another rather than all at once: a tick that fans out
    across every project at the same minute is how an integration's rate limit gets hit.
    """
    due = await asyncio.to_thread(service.due_projects)
    if not due:
        return 0

    logger.info("Scheduler: %s project(s) due", len(due))
    for project in due:
        await asyncio.to_thread(_analyse, project)
    return len(due)


def _analyse(project: dict) -> None:
    """One scheduled analysis. A failure is already recorded on the run by
    `run_analysis`, so this only has to keep the rest of the tick alive."""
    try:
        run = service.start_analysis(project["id"], project["owner_id"], triggered_by="schedule")
        service.run_analysis(project["id"], run["id"])
    except Exception:  # noqa: BLE001
        logger.exception("Scheduled analysis failed for project %s", project["id"])
