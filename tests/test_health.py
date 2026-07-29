from pathlib import Path

import pytest

from slopeping.health import (
    SuspiciousEmptyScheduleError,
    guard_empty_schedule,
    load_health,
    record_run_failure,
    record_run_started,
    record_run_success,
)


def test_first_empty_result_preserves_nonempty_previous_state(tmp_path: Path) -> None:
    path = tmp_path / "health.json"

    with pytest.raises(SuspiciousEmptyScheduleError, match="Preserving"):
        guard_empty_schedule(path, previous_count=3, current_count=0, required_confirmations=2)

    assert load_health(path).consecutive_empty_results == 1


def test_second_empty_result_is_accepted_and_resets_counter(tmp_path: Path) -> None:
    path = tmp_path / "health.json"

    with pytest.raises(SuspiciousEmptyScheduleError):
        guard_empty_schedule(path, previous_count=3, current_count=0, required_confirmations=2)
    guard_empty_schedule(path, previous_count=3, current_count=0, required_confirmations=2)

    assert load_health(path).consecutive_empty_results == 0


def test_nonempty_result_clears_empty_counter(tmp_path: Path) -> None:
    path = tmp_path / "health.json"

    with pytest.raises(SuspiciousEmptyScheduleError):
        guard_empty_schedule(path, previous_count=3, current_count=0, required_confirmations=2)
    guard_empty_schedule(path, previous_count=3, current_count=2, required_confirmations=2)

    assert load_health(path).consecutive_empty_results == 0


def test_health_tracks_failures_and_recovery(tmp_path: Path) -> None:
    path = tmp_path / "health.json"

    record_run_started(path)
    failed = record_run_failure(path, RuntimeError("portal unavailable"), 1.25)
    previous_failures = record_run_success(path, record_count=4, duration_seconds=0.5)
    recovered = load_health(path)

    assert failed.consecutive_failures == 1
    assert failed.last_error_type == "RuntimeError"
    assert previous_failures == 1
    assert recovered.consecutive_failures == 0
    assert recovered.last_record_count == 4
    assert recovered.last_success_at is not None
