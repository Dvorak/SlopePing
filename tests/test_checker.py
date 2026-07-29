from pathlib import Path

from playwright.sync_api import Error as PlaywrightError

from slopeping.checker import _run_check
from slopeping.config import Selectors, Settings
from slopeping.health import load_health, record_run_failure


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
        health_path=tmp_path / "health.json",
        lock_path=tmp_path / "slopeping.lock",
        empty_confirmation_runs=2,
        check_retry_attempts=2,
        check_retry_delay_seconds=0,
        failure_alert_threshold=2,
        selectors=Selectors(),
    )


def test_check_retries_transient_collection_errors(monkeypatch, tmp_path: Path) -> None:
    current_settings = settings(tmp_path)
    calls = []

    def collect(settings):
        calls.append(settings)
        if len(calls) == 1:
            raise PlaywrightError("temporary browser error")
        return [], "screenshot.png"

    monkeypatch.setattr("slopeping.checker._collect_schedule", collect)
    monkeypatch.setattr("slopeping.checker._process_records", lambda *args: None)

    assert _run_check(current_settings) == 0
    assert len(calls) == 2
    assert load_health(current_settings.health_path).consecutive_failures == 0


def test_check_records_final_failure_and_sends_alert(monkeypatch, tmp_path: Path) -> None:
    current_settings = settings(tmp_path)
    alerts = []
    monkeypatch.setattr(
        "slopeping.checker._collect_schedule",
        lambda settings: (_ for _ in ()).throw(ValueError("invalid page")),
    )
    monkeypatch.setattr(
        "slopeping.checker.notify_run_failure",
        lambda error, consecutive: alerts.append((error, consecutive)),
    )

    assert _run_check(current_settings) == 1
    assert load_health(current_settings.health_path).consecutive_failures == 1
    assert alerts[0][1] == 1


def test_success_after_failure_sends_recovery(monkeypatch, tmp_path: Path) -> None:
    current_settings = settings(tmp_path)
    recoveries = []
    record_run_failure(current_settings.health_path, RuntimeError("old failure"), 1)
    monkeypatch.setattr(
        "slopeping.checker._collect_schedule",
        lambda settings: ([], "screenshot.png"),
    )
    monkeypatch.setattr("slopeping.checker._process_records", lambda *args: None)
    monkeypatch.setattr(
        "slopeping.checker.notify_run_recovery",
        lambda failures, count: recoveries.append((failures, count)),
    )

    assert _run_check(current_settings) == 0
    assert recoveries == [(1, 0)]
