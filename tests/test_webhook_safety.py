from slopeping.security import issue_token
from slopeping.state import ScheduleRecord
from slopeping.web_views import render_confirmation_page
from slopeping.webhook import accept_lesson, decline_lesson

SECRET = "a-secure-test-secret-that-is-long-enough"


def test_direct_remote_actions_remain_blocked(monkeypatch) -> None:
    monkeypatch.setenv("ACTION_WEBHOOK_TOKEN", SECRET)
    token = issue_token(SECRET, "control", 60)

    assert accept_lesson("lesson-id", token)["status"] == "blocked"
    assert decline_lesson("lesson-id", token)["status"] == "blocked"


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

    rendered = render_confirmation_page(
        current,
        "accept",
        "control-token",
        "execute-token",
    )

    assert "Action unavailable" in rendered
    assert "/actions/execute" not in rendered
