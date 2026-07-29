import urllib.error
from urllib.parse import parse_qs, urlparse

from slopeping.notify import (
    _build_calendar_action,
    _build_control_action,
    _format_lessons,
    _notification_subject,
    _send_ntfy,
)
from slopeping.security import verify_token
from slopeping.state import ScheduleRecord

SECRET = "a-secure-test-secret-that-is-long-enough"


def lesson(*, status: str = "confirmed") -> ScheduleRecord:
    actions = ["Bestätigen", "Absagen"] if status == "pending" else []
    return ScheduleRecord(
        tag="Mi, 29.07.2026",
        von="09:00",
        bis="11:00",
        raum_ort="Skihalle",
        trainingsbezeichnung="Privatkurs Ski",
        bestaetigung="",
        confirmation_status=status,
        available_actions=actions,
    )


def test_pending_lesson_uses_action_needed_subject() -> None:
    assert _notification_subject([lesson(status="pending")]) == "SlopePing: action needed"


def test_confirmed_lessons_use_new_lesson_subject() -> None:
    assert _notification_subject([lesson(), lesson()]) == "SlopePing: 2 new lesson(s)"


def test_notification_body_contains_action_context() -> None:
    body = _format_lessons([lesson(status="pending")])

    assert "confirmation_status: pending" in body
    assert "available_actions: Bestätigen, Absagen" in body
    assert "lesson_id: Mi, 29.07.2026|09:00|11:00|Skihalle|Privatkurs Ski" in body


def test_control_links_are_url_encoded(monkeypatch) -> None:
    monkeypatch.setenv("ACTION_WEBHOOK_BASE_URL", "https://example.test/base/")
    monkeypatch.setenv("ACTION_WEBHOOK_TOKEN", SECRET)

    control_url = _build_control_action()[0].split(", ", 2)[2]
    calendar_url = _build_calendar_action()[0].split(", ", 2)[2]
    control_token = parse_qs(urlparse(control_url).query)["token"][0]
    calendar_token = parse_qs(urlparse(calendar_url).query)["token"][0]

    assert urlparse(control_url).path == "/base/control"
    assert urlparse(calendar_url).path == "/base/calendar"
    assert verify_token(SECRET, control_token, {"control"}).scope == "control"
    assert verify_token(SECRET, calendar_token, {"calendar"}).scope == "calendar"


def test_control_links_require_both_url_and_token(monkeypatch) -> None:
    monkeypatch.delenv("ACTION_WEBHOOK_BASE_URL", raising=False)
    monkeypatch.setenv("ACTION_WEBHOOK_TOKEN", SECRET)

    assert _build_control_action() == []
    assert _build_calendar_action() == []


def test_ntfy_retries_transient_errors(monkeypatch) -> None:
    calls = []
    delays = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

    def urlopen(request, timeout):
        calls.append((request, timeout))
        if len(calls) == 1:
            raise urllib.error.URLError("temporary")
        return Response()

    monkeypatch.setenv("NTFY_SERVER", "https://example.test")
    monkeypatch.setenv("NTFY_TOPIC", "topic")
    monkeypatch.setenv("NTFY_RETRY_ATTEMPTS", "2")
    monkeypatch.setenv("NTFY_RETRY_DELAY_SECONDS", "0.5")
    monkeypatch.setattr("slopeping.notify.urllib.request.urlopen", urlopen)
    monkeypatch.setattr("slopeping.notify.time.sleep", delays.append)

    assert _send_ntfy("subject", "body", include_actions=False) is True
    assert len(calls) == 2
    assert delays == [0.5]
