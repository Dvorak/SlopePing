import pytest

from slopeping.state import ScheduleRecord
from slopeping.web_views import render_confirmation_page, render_control_page


def lesson(**overrides: object) -> ScheduleRecord:
    values: dict[str, object] = {
        "tag": "Mi, 29.07.2026",
        "von": "09:00",
        "bis": "11:00",
        "raum_ort": "Skihalle",
        "trainingsbezeichnung": "Privatkurs Ski",
        "bestaetigung": "",
        "confirmation_status": "pending",
        "available_actions": ["Bestätigen", "Absagen"],
    }
    values.update(overrides)
    return ScheduleRecord(**values)  # type: ignore[arg-type]


def test_control_page_escapes_lesson_data_and_encodes_token() -> None:
    rendered = render_control_page(
        [lesson(trainingsbezeichnung="<script>alert(1)</script>")],
        "token with spaces",
        "2026-07-29T20:00:00+00:00",
    )

    assert "<script>" not in rendered
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered
    assert "token=token+with+spaces" in rendered


def test_confirmation_page_rejects_unknown_action() -> None:
    with pytest.raises(ValueError, match="Unknown action"):
        render_confirmation_page(lesson(), "delete", "control-token", "execute-token")
