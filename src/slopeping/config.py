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
class Settings:
    login_url: str
    username: str
    password: str
    headless: bool
    slow_mo_ms: int
    navigation_timeout_ms: int
    screenshots_dir: Path
    state_path: Path
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


def load_settings(env_file: str | Path = ".env") -> Settings:
    load_dotenv(env_file)

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
        screenshots_dir=Path(os.getenv("SKI_SCREENSHOTS_DIR", "screenshots")),
        state_path=Path(os.getenv("SKI_STATE_PATH", "state.json")),
        selectors=selectors,
    )

