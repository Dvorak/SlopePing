from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RunHealth:
    version: int = 1
    consecutive_failures: int = 0
    consecutive_empty_results: int = 0
    last_started_at: str | None = None
    last_completed_at: str | None = None
    last_success_at: str | None = None
    last_failure_at: str | None = None
    last_error_type: str | None = None
    last_error_message: str | None = None
    last_record_count: int | None = None
    last_duration_seconds: float | None = None


class SuspiciousEmptyScheduleError(RuntimeError):
    """Raised when an empty schedule has not yet been confirmed."""


def load_health(path: Path) -> RunHealth:
    if not path.exists():
        return RunHealth()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return RunHealth()
    if not isinstance(raw, dict):
        return RunHealth()
    return _health_from_dict(raw)


def save_health(path: Path, health: RunHealth) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(
        json.dumps(asdict(health), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(path)


def guard_empty_schedule(
    path: Path,
    previous_count: int,
    current_count: int,
    required_confirmations: int,
) -> None:
    health = load_health(path)
    if current_count > 0 or previous_count == 0:
        if health.consecutive_empty_results:
            save_health(path, _replace_health(health, consecutive_empty_results=0))
        return

    observed = health.consecutive_empty_results + 1
    save_health(path, _replace_health(health, consecutive_empty_results=observed))
    if observed < required_confirmations:
        raise SuspiciousEmptyScheduleError(
            "Parsed 0 lessons while the previous state contained "
            f"{previous_count}. Preserving the previous state until "
            f"{required_confirmations} consecutive empty results are observed "
            f"(currently {observed})."
        )

    save_health(path, _replace_health(health, consecutive_empty_results=0))


def _health_from_dict(raw: dict[str, Any]) -> RunHealth:
    return RunHealth(
        version=_as_int(raw.get("version"), 1),
        consecutive_failures=_as_int(raw.get("consecutive_failures"), 0),
        consecutive_empty_results=_as_int(raw.get("consecutive_empty_results"), 0),
        last_started_at=_as_optional_str(raw.get("last_started_at")),
        last_completed_at=_as_optional_str(raw.get("last_completed_at")),
        last_success_at=_as_optional_str(raw.get("last_success_at")),
        last_failure_at=_as_optional_str(raw.get("last_failure_at")),
        last_error_type=_as_optional_str(raw.get("last_error_type")),
        last_error_message=_as_optional_str(raw.get("last_error_message")),
        last_record_count=_as_optional_int(raw.get("last_record_count")),
        last_duration_seconds=_as_optional_float(raw.get("last_duration_seconds")),
    )


def _replace_health(health: RunHealth, **changes: Any) -> RunHealth:
    values = asdict(health)
    values.update(changes)
    return RunHealth(**values)


def _as_int(value: Any, default: int) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else default


def _as_optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _as_optional_float(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _as_optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None
