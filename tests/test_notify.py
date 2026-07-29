from slopeping.notify import (
    _build_calendar_action,
    _build_control_action,
    _format_lessons,
    _notification_subject,
)
from slopeping.state import ScheduleRecord


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
    monkeypatch.setenv("ACTION_WEBHOOK_TOKEN", "token with spaces")

    assert _build_control_action() == [
        "view, Open SlopePing, https://example.test/base/control?token=token+with+spaces"
    ]
    assert _build_calendar_action() == [
        "view, Open calendar page, https://example.test/base/calendar?token=token+with+spaces"
    ]


def test_control_links_require_both_url_and_token(monkeypatch) -> None:
    monkeypatch.delenv("ACTION_WEBHOOK_BASE_URL", raising=False)
    monkeypatch.setenv("ACTION_WEBHOOK_TOKEN", "secret")

    assert _build_control_action() == []
    assert _build_calendar_action() == []
