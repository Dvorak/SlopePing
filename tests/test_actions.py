from dataclasses import replace
from pathlib import Path

from slopeping.actions import _find_matching_row, perform_lesson_action
from slopeping.config import Selectors, Settings
from slopeping.parser import ParsedScheduleRow
from slopeping.state import ScheduleRecord


class LocatorMustNotBeUsed:
    def locator(self, selector: str):
        raise AssertionError(f"locator must not be used for a protected action: {selector}")


class FakeSelect:
    @property
    def first(self):
        return self

    def count(self) -> int:
        return 1

    def select_option(self, **kwargs) -> None:
        raise AssertionError(f"select_option must not be called: {kwargs}")


class RowWithSelect:
    def __init__(self) -> None:
        self.select = FakeSelect()

    def locator(self, selector: str) -> FakeSelect:
        assert selector == "select"
        return self.select


def lesson() -> ScheduleRecord:
    return ScheduleRecord(
        tag="Mi, 29.07.2026",
        von="09:00",
        bis="11:00",
        raum_ort="Skihalle",
        trainingsbezeichnung="Privatkurs Ski",
        bestaetigung="Bestätigt",
        confirmation_status="confirmed",
        available_actions=[],
    )


def settings(tmp_path: Path) -> Settings:
    return Settings(
        login_url="https://example.test/login",
        username="test-user",
        password="test-password",
        headless=True,
        slow_mo_ms=0,
        navigation_timeout_ms=100,
        screenshots_dir=tmp_path / "screenshots",
        state_path=tmp_path / "state.json",
        selectors=Selectors(),
    )


def parsed(record: ScheduleRecord, row) -> ParsedScheduleRow:
    return ParsedScheduleRow(record=record, row=row, headers={})  # type: ignore[arg-type]


def test_matching_row_accepts_full_id_hash_and_long_hash_prefix() -> None:
    current = lesson()
    rows = [parsed(current, LocatorMustNotBeUsed())]

    assert _find_matching_row(rows, current.lesson_id) == rows[0]
    assert _find_matching_row(rows, current.key) == rows[0]
    assert _find_matching_row(rows, current.key[:8]) == rows[0]
    assert _find_matching_row(rows, current.key[:7]) is None


def test_confirmed_lesson_is_never_modified(monkeypatch, tmp_path: Path) -> None:
    current = lesson()
    log_calls = []
    monkeypatch.setattr(
        "slopeping.actions.parse_overview_rows",
        lambda page, selectors: [parsed(current, LocatorMustNotBeUsed())],
    )
    monkeypatch.setattr(
        "slopeping.actions._write_action_log",
        lambda *args, **kwargs: log_calls.append((args, kwargs)),
    )

    result = perform_lesson_action(
        object(),  # type: ignore[arg-type]
        settings(tmp_path),
        "accept",
        current.lesson_id,
    )

    assert result is False
    assert log_calls[0][0][3] == "not_pending"


def test_unavailable_action_is_never_selected(monkeypatch, tmp_path: Path) -> None:
    current = replace(
        lesson(),
        bestaetigung="",
        confirmation_status="pending",
        available_actions=["Absagen"],
    )
    row = RowWithSelect()
    log_calls = []
    monkeypatch.setattr(
        "slopeping.actions.parse_overview_rows",
        lambda page, selectors: [parsed(current, row)],
    )
    monkeypatch.setattr(
        "slopeping.actions._write_action_log",
        lambda *args, **kwargs: log_calls.append((args, kwargs)),
    )

    result = perform_lesson_action(
        object(),  # type: ignore[arg-type]
        settings(tmp_path),
        "accept",
        current.lesson_id,
    )

    assert result is False
    assert log_calls[0][0][3] == "action_unavailable"
