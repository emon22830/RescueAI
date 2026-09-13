"""Google Calendar. Reads project evidence; write actions live in execute_action()."""

import logging
from datetime import UTC, datetime, timedelta

import httpx

from app.agents.state import Evidence, PlannedAction
from app.config import settings
from app.integrations import google_auth

logger = logging.getLogger(__name__)

API = "https://www.googleapis.com/calendar/v3/calendars"
TIMEOUT = 20.0
PAST_DAYS = 7
AHEAD_DAYS = 90
MAX_EVENTS = 25
DEFAULT_MEETING_MINUTES = 30


def collect_evidence(project_name: str) -> list[Evidence]:
    """Meetings and deadlines for this project — everything ahead, plus the week just gone.

    The recent past is included on purpose: a kickoff that happened and a review
    that never got booked are both worth knowing about.
    """
    if not google_auth.is_connected():
        logger.warning("Calendar skipped: GOOGLE_* variables are empty in backend/.env")
        return []

    return [_to_evidence(event) for event in upcoming_events(project_name)]


def upcoming_events(project_name: str) -> list[dict]:
    """Events matching the project name, recurring ones expanded, earliest first."""
    now = datetime.now(UTC)
    body = _get(
        f"/{settings.google_calendar_id}/events",
        {
            "q": project_name,
            "timeMin": (now - timedelta(days=PAST_DAYS)).isoformat(),
            "timeMax": (now + timedelta(days=AHEAD_DAYS)).isoformat(),
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": MAX_EVENTS,
        },
    )
    return body.get("items", [])


def create_event(
    summary: str,
    description: str,
    attendees: list[str],
    start: datetime,
    minutes: int = DEFAULT_MEETING_MINUTES,
) -> dict:
    """Book a meeting on the connected calendar and invite the attendees."""
    response = httpx.post(
        f"{API}/{settings.google_calendar_id}/events",
        params={"sendUpdates": "all"},
        json={
            "summary": summary,
            "description": description,
            "start": {"dateTime": start.isoformat()},
            "end": {"dateTime": (start + timedelta(minutes=minutes)).isoformat()},
            "attendees": [{"email": email} for email in attendees],
        },
        headers=google_auth.headers(),
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def execute_action(action: PlannedAction) -> str:
    """Perform one approved action and return a short human-readable result.

    `target` is the attendee list and `value` is the meeting title and purpose.
    A plan may set params.start (ISO 8601) and params.minutes; without a start
    the meeting is booked for 10:00 UTC tomorrow so a human can move it.
    """
    if action.type != "create_event":
        raise NotImplementedError(f"Google Calendar action not implemented: {action.type}")

    purpose = action.params.get("value")
    if not purpose:
        raise ValueError("Calendar create_event needs params.value (what the meeting is for)")

    attendees = [email.strip() for email in action.target.split(",") if "@" in email]
    start = _start_time(action.params.get("start"))
    minutes = int(action.params.get("minutes", DEFAULT_MEETING_MINUTES))

    event = create_event(
        summary=purpose.splitlines()[0][:120],
        description=f"{action.description}\n\n{purpose}",
        attendees=attendees,
        start=start,
        minutes=minutes,
    )
    invited = ", ".join(attendees) or "no attendees"
    return f"Booked \"{event['summary']}\" for {start:%d %b %H:%M UTC} with {invited} — {event.get('htmlLink')}"


def _start_time(given: str | None) -> datetime:
    if given:
        return datetime.fromisoformat(str(given).replace("Z", "+00:00"))
    tomorrow = datetime.now(UTC) + timedelta(days=1)
    return tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)


# --- normalization -----------------------------------------------------------


def _to_evidence(event: dict) -> Evidence:
    start = _when(event.get("start", {}))
    end = _when(event.get("end", {}))
    attendees = [person.get("email", "") for person in event.get("attendees", [])]
    organizer = (event.get("organizer") or {}).get("email", "unknown")

    content = "\n".join(
        [
            f"Starts: {start}",
            f"Ends: {end}",
            f"Organizer: {organizer}",
            f"Attendees: {', '.join(attendees) or 'none invited'}",
            f"Location: {event.get('location', 'not set')}",
            f"Status: {event.get('status', 'unknown')}",
            "",
            event.get("description") or "",
        ]
    ).strip()

    return Evidence(
        source="calendar",
        type="event",
        title=event.get("summary", "(untitled event)"),
        content=content,
        url=event.get("htmlLink"),
        timestamp=start,
        metadata={
            "event_id": event.get("id"),
            "start": start,
            "end": end,
            "organizer": organizer,
            "attendees": attendees,
            "status": event.get("status"),
            "all_day": "date" in event.get("start", {}),
        },
    )


def _when(marker: dict) -> str | None:
    """A timed event carries dateTime; an all-day event carries date."""
    return marker.get("dateTime") or marker.get("date")


def _get(path: str, params: dict) -> dict:
    response = httpx.get(f"{API}{path}", params=params, headers=google_auth.headers(), timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()
