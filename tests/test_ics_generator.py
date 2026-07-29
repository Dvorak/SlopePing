import re
from datetime import datetime

import pytest
from icalendar import Calendar

from slopeping.ics_generator import build_ics_bytes, build_ics_filename
from slopeping.state import ScheduleRecord


def lesson(*, von: str = "22:00", bis: str = "23:30") -> ScheduleRecord:
    return ScheduleRecord(
        tag="Mi, 29.07.2026",
        von=von,
        bis=bis,
        raum_ort="Skihalle",
        trainingsbezeichnung="Privatkurs Ski & Snowboard",
        bestaetigung="Bestätigt",
        confirmation_status="confirmed",
        available_actions=[],
    )


def event_from(payload: bytes):
    calendar = Calendar.from_ical(payload)
    return next(component for component in calendar.walk() if component.name == "VEVENT")


def test_ics_contains_lesson_fields_and_berlin_timezone() -> None:
    current = lesson()

    event = event_from(build_ics_bytes(current, action="accept"))

    assert str(event["summary"]) == current.trainingsbezeichnung
    assert str(event["location"]) == current.raum_ort
    assert event.decoded("dtstart") == datetime.fromisoformat("2026-07-29T22:00:00+02:00")
    assert event.decoded("dtend") == datetime.fromisoformat("2026-07-29T23:30:00+02:00")
    assert "Action: accept" in str(event["description"])
    assert str(event["uid"]) == f"{current.lesson_id}-accept@slopeping"


def test_ics_treats_earlier_end_time_as_next_day() -> None:
    event = event_from(build_ics_bytes(lesson(von="23:30", bis="01:15")))

    assert event.decoded("dtstart") == datetime.fromisoformat("2026-07-29T23:30:00+02:00")
    assert event.decoded("dtend") == datetime.fromisoformat("2026-07-30T01:15:00+02:00")


def test_ics_uid_is_stable_for_same_lesson_and_action() -> None:
    current = lesson()

    first = str(event_from(build_ics_bytes(current, action="decline"))["uid"])
    second = str(event_from(build_ics_bytes(current, action="decline"))["uid"])

    assert first == second


def test_ics_filename_is_phone_safe() -> None:
    filename = build_ics_filename(lesson(), action="accept")

    assert re.fullmatch(
        r"Mi_29.07.2026_Privatkurs_Ski_Snowboard_accept_\d{8}-\d{6}\.ics",
        filename,
    )


def test_ics_rejects_invalid_date() -> None:
    invalid = lesson()
    invalid = ScheduleRecord(
        **{**invalid.__dict__, "tag": "kein Datum"},
    )

    with pytest.raises(ValueError, match="Could not parse lesson datetime"):
        build_ics_bytes(invalid)
