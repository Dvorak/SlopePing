import json
from dataclasses import replace
from pathlib import Path

import pytest

from slopeping.state import ScheduleRecord, diff_records, load_records, save_records


def lesson(**overrides: object) -> ScheduleRecord:
    values: dict[str, object] = {
        "tag": "Mi, 29.07.2026",
        "von": "09:00",
        "bis": "11:00",
        "raum_ort": "Skihalle",
        "trainingsbezeichnung": "Privatkurs Ski",
        "bestaetigung": "Bestätigt",
        "confirmation_status": "confirmed",
        "available_actions": [],
    }
    values.update(overrides)
    return ScheduleRecord(**values)  # type: ignore[arg-type]


def test_record_identity_ignores_confirmation_but_fingerprint_does_not() -> None:
    original = lesson()
    changed = replace(
        original,
        bestaetigung="",
        confirmation_status="pending",
        available_actions=["Bestätigen", "Absagen"],
    )

    assert original.key == changed.key
    assert original.lesson_id == ("Mi, 29.07.2026|09:00|11:00|Skihalle|Privatkurs Ski")
    assert original.fingerprint != changed.fingerprint


def test_diff_records_reports_new_changed_and_unchanged() -> None:
    unchanged = lesson()
    changed_before = lesson(tag="Do, 30.07.2026")
    changed_after = replace(changed_before, confirmation_status="pending")
    new = lesson(tag="Fr, 31.07.2026")

    changes = diff_records(
        [unchanged, changed_before],
        [unchanged, changed_after, new],
    )

    assert [change.kind for change in changes] == ["changed", "new"]
    assert changes[0].previous == changed_before
    assert changes[0].current == changed_after
    assert changes[1].previous is None


def test_diff_records_collapses_duplicate_current_lessons() -> None:
    duplicate = lesson()

    changes = diff_records([], [duplicate, duplicate])

    assert len(changes) == 1
    assert changes[0].current == duplicate


def test_load_missing_state_returns_empty_list(tmp_path: Path) -> None:
    assert load_records(tmp_path / "missing.json") == []


def test_save_and_load_state_atomically(tmp_path: Path) -> None:
    path = tmp_path / "state" / "state.json"
    expected = [lesson()]

    save_records(path, expected)

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["last_checked_at"].endswith("+00:00")
    assert load_records(path) == expected
    assert not path.with_suffix(".json.tmp").exists()


def test_load_legacy_list_state(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text(
        json.dumps(
            [
                {
                    "tag": "Mi, 29.07.2026",
                    "von": "09:00",
                    "bis": "11:00",
                    "raum_ort": "Skihalle",
                    "trainingsbezeichnung": "Privatkurs Ski",
                    "bestaetigung": "Bestätigt",
                }
            ]
        ),
        encoding="utf-8",
    )

    [record] = load_records(path)

    assert record.tag == "Mi, 29.07.2026"
    assert record.confirmation_status == "unknown"
    assert record.available_actions == []


def test_invalid_json_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        load_records(path)


def test_invalid_records_shape_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text('{"records": "not-a-list"}', encoding="utf-8")

    with pytest.raises(ValueError, match="records must be a list"):
        load_records(path)
