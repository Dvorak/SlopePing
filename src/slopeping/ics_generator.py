from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event

from .state import ScheduleRecord


BERLIN = ZoneInfo("Europe/Berlin")


def build_ics_bytes(lesson: ScheduleRecord, action: str | None = None) -> bytes:
    """Build an iCalendar payload that can be downloaded directly."""
    return _build_calendar(lesson, action=action).to_ical()


def build_ics_filename(lesson: ScheduleRecord, action: str | None = None) -> str:
    """Build a phone-friendly .ics filename."""
    safe_tag = re.sub(r"[^0-9A-Za-z._-]+", "_", lesson.tag).strip("_") or "lesson"
    safe_name = re.sub(r"[^0-9A-Za-z._-]+", "_", lesson.trainingsbezeichnung).strip("_")[:24]
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = action or "export"
    return f"{safe_tag}_{safe_name}_{suffix}_{timestamp}.ics"


def create_ics_event(lesson: ScheduleRecord, action: str) -> Path:
    """
    Create an .ics calendar event file from a lesson.

    Args:
        lesson: The ScheduleRecord containing lesson details
        action: The action performed ('accept' or 'decline')

    Returns:
        Path to the created .ics file
    """
    calendar = _build_calendar(lesson, action=action)

    # Create calendar_events directory if it doesn't exist
    calendar_dir = Path("calendar_events")
    calendar_dir.mkdir(parents=True, exist_ok=True)

    filename = build_ics_filename(lesson, action=action)
    filepath = calendar_dir / filename

    # Write ICS file
    with filepath.open("wb") as f:
        f.write(calendar.to_ical())

    print(f"[ics] Created calendar event: {filepath}", flush=True)
    return filepath


def _build_calendar(lesson: ScheduleRecord, action: str | None = None) -> Calendar:
    calendar = Calendar()
    calendar.add("prodid", "-//SlopePing//EN")
    calendar.add("version", "2.0")

    event = Event()

    event_start = _parse_datetime(lesson.tag, lesson.von)
    event_end = _parse_datetime(lesson.tag, lesson.bis)

    event.add("summary", lesson.trainingsbezeichnung)
    event.add("location", lesson.raum_ort)
    event.add("dtstart", event_start)
    event.add("dtend", event_end)

    description = f"lesson_id: {lesson.lesson_id}"
    if action:
        description = f"{description}\nAction: {action}"
    event.add("description", description)
    event.add("uid", f"{lesson.lesson_id}-{action or 'export'}@slopeping")

    calendar.add_component(event)
    return calendar


def _parse_datetime(tag: str, time_str: str) -> datetime:
    """
    Parse date and time strings from lesson data.

    Args:
        tag: Date string (e.g., "Mo, 10.01.2025")
        time_str: Time string (e.g., "10:00")

    Returns:
        Europe/Berlin datetime object
    """
    date_match = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", tag)
    time_match = re.search(r"(\d{1,2}):(\d{2})", time_str)
    if not date_match or not time_match:
        raise ValueError(f"Could not parse lesson datetime from tag={tag!r}, time={time_str!r}")

    day, month, year = (int(part) for part in date_match.groups())
    hour, minute = (int(part) for part in time_match.groups())
    return datetime(year, month, day, hour, minute, tzinfo=BERLIN)
