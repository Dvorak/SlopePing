from slopeping.state import ScheduleRecord
from slopeping.webhook import _render_confirmation_page, accept_lesson, decline_lesson


def test_direct_remote_actions_remain_blocked(monkeypatch) -> None:
    monkeypatch.setenv("ACTION_WEBHOOK_TOKEN", "secret")

    assert accept_lesson("lesson-id", "secret")["status"] == "blocked"
    assert decline_lesson("lesson-id", "secret")["status"] == "blocked"


def test_non_pending_confirmation_page_has_no_execute_form() -> None:
    current = ScheduleRecord(
        tag="Mi, 29.07.2026",
        von="09:00",
        bis="11:00",
        raum_ort="Skihalle",
        trainingsbezeichnung="Privatkurs Ski",
        bestaetigung="Bestätigt",
        confirmation_status="confirmed",
        available_actions=[],
    )

    rendered = _render_confirmation_page(current, "accept", "secret")

    assert "Action unavailable" in rendered
    assert "/actions/execute" not in rendered
