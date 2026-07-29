from pathlib import Path

from slopeping.ui_preview import build_preview_records, write_ui_previews


def test_preview_records_are_anonymous_and_cover_pending_and_confirmed() -> None:
    records = build_preview_records()

    assert {record.confirmation_status for record in records} == {"pending", "confirmed"}
    assert all("@" not in record.lesson_id for record in records)


def test_ui_previews_are_offline_and_cover_the_user_flow(tmp_path: Path) -> None:
    written = write_ui_previews(tmp_path)

    assert {path.name for path in written} == {
        "calendar.html",
        "confirmation.html",
        "control.html",
        "result.html",
    }

    control = (tmp_path / "control.html").read_text(encoding="utf-8")
    confirmation = (tmp_path / "confirmation.html").read_text(encoding="utf-8")
    result = (tmp_path / "result.html").read_text(encoding="utf-8")

    assert "Snowboard Gruppenkurs" in control
    assert "Review accept" in control
    assert "Confirm accept" in confirmation
    assert "Preview only: no remote action was performed." in result
