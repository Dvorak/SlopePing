from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Selectors:
    username_label: str = "Benutzername"
    password_label: str = "Passwort"
    login_button_name: str = "Anmelden"
    my_data_text: str = "Meine Daten"
    schedule_text: str = "Arbeitsplan/Verfügbarkeit"
    overview_text: str = "Übersicht"
    overview_table_xpath: str = "xpath=following::table[1]"


@dataclass(frozen=True)
class RuntimePaths:
    runtime_dir: Path
    state_path: Path
    screenshots_dir: Path
    health_path: Path
    lock_path: Path
    actions_log_path: Path
    calendar_dir: Path
    logs_dir: Path
    used_nonces_path: Path


@dataclass(frozen=True)
class Settings:
    login_url: str
    username: str
    password: str
    headless: bool
    slow_mo_ms: int
    navigation_timeout_ms: int
    runtime_dir: Path
    screenshots_dir: Path
    state_path: Path
    health_path: Path
    lock_path: Path
    actions_log_path: Path
    calendar_dir: Path
    logs_dir: Path
    used_nonces_path: Path
    empty_confirmation_runs: int
    check_retry_attempts: int
    check_retry_delay_seconds: float
    failure_alert_threshold: int
    retention_days: int
    screenshots_max_files: int
    calendar_max_files: int
    log_max_bytes: int
    log_backups: int
    selectors: Selectors


def _bool_from_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int_from_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {value!r}") from exc


def _float_from_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {value!r}") from exc


def load_runtime_paths(env_file: str | Path = ".env") -> RuntimePaths:
    load_dotenv(env_file)
    runtime_dir = Path(os.getenv("SLOPEPING_RUNTIME_DIR", "var"))
    return RuntimePaths(
        runtime_dir=runtime_dir,
        state_path=Path(os.getenv("SKI_STATE_PATH", str(runtime_dir / "state.json"))),
        screenshots_dir=Path(os.getenv("SKI_SCREENSHOTS_DIR", str(runtime_dir / "screenshots"))),
        health_path=Path(os.getenv("SKI_HEALTH_PATH", str(runtime_dir / "health.json"))),
        lock_path=Path(os.getenv("SKI_LOCK_PATH", str(runtime_dir / "slopeping.lock"))),
        actions_log_path=Path(os.getenv("SKI_ACTIONS_LOG_PATH", str(runtime_dir / "actions.log"))),
        calendar_dir=Path(os.getenv("SKI_CALENDAR_DIR", str(runtime_dir / "calendar_events"))),
        logs_dir=Path(os.getenv("SKI_LOGS_DIR", str(runtime_dir / "logs"))),
        used_nonces_path=Path(
            os.getenv("SKI_USED_NONCES_PATH", str(runtime_dir / "used-action-nonces.json"))
        ),
    )


def load_settings(env_file: str | Path = ".env") -> Settings:
    load_dotenv(env_file)
    runtime_paths = load_runtime_paths(env_file)

    username = os.getenv("SKI_USERNAME", "").strip()
    password = os.getenv("SKI_PASSWORD", "")

    if not username:
        raise ValueError("Missing SKI_USERNAME. Copy .env.example to .env and fill it in.")
    if not password:
        raise ValueError("Missing SKI_PASSWORD. Copy .env.example to .env and fill it in.")

    selectors = Selectors(
        username_label=os.getenv("SKI_USERNAME_LABEL", "Benutzername"),
        password_label=os.getenv("SKI_PASSWORD_LABEL", "Passwort"),
        login_button_name=os.getenv("SKI_LOGIN_BUTTON_NAME", "Anmelden"),
        my_data_text=os.getenv("SKI_MY_DATA_TEXT", "Meine Daten"),
        schedule_text=os.getenv("SKI_SCHEDULE_TEXT", "Arbeitsplan/Verfügbarkeit"),
        overview_text=os.getenv("SKI_OVERVIEW_TEXT", "Übersicht"),
        overview_table_xpath=os.getenv("SKI_OVERVIEW_TABLE_XPATH", "xpath=following::table[1]"),
    )

    return Settings(
        login_url=os.getenv("SKI_LOGIN_URL", "https://allrounder-jobs.de/login"),
        username=username,
        password=password,
        headless=_bool_from_env("SKI_HEADLESS", False),
        slow_mo_ms=_int_from_env("SKI_SLOW_MO_MS", 250),
        navigation_timeout_ms=_int_from_env("SKI_NAVIGATION_TIMEOUT_MS", 30000),
        runtime_dir=runtime_paths.runtime_dir,
        screenshots_dir=runtime_paths.screenshots_dir,
        state_path=runtime_paths.state_path,
        health_path=runtime_paths.health_path,
        lock_path=runtime_paths.lock_path,
        actions_log_path=runtime_paths.actions_log_path,
        calendar_dir=runtime_paths.calendar_dir,
        logs_dir=runtime_paths.logs_dir,
        used_nonces_path=runtime_paths.used_nonces_path,
        empty_confirmation_runs=max(2, _int_from_env("SKI_EMPTY_CONFIRMATION_RUNS", 2)),
        check_retry_attempts=max(1, _int_from_env("SKI_CHECK_RETRY_ATTEMPTS", 2)),
        check_retry_delay_seconds=max(
            0.0,
            _float_from_env("SKI_CHECK_RETRY_DELAY_SECONDS", 5.0),
        ),
        failure_alert_threshold=max(1, _int_from_env("SKI_FAILURE_ALERT_THRESHOLD", 2)),
        retention_days=max(1, _int_from_env("SKI_RETENTION_DAYS", 30)),
        screenshots_max_files=max(1, _int_from_env("SKI_SCREENSHOTS_MAX_FILES", 200)),
        calendar_max_files=max(1, _int_from_env("SKI_CALENDAR_MAX_FILES", 100)),
        log_max_bytes=max(1, _int_from_env("SKI_LOG_MAX_BYTES", 5_000_000)),
        log_backups=max(0, _int_from_env("SKI_LOG_BACKUPS", 3)),
        selectors=selectors,
    )
