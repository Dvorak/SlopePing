from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .config import Settings


@dataclass(frozen=True)
class MaintenanceResult:
    removed: tuple[Path, ...]
    rotated: tuple[Path, ...]


def maintain_runtime_files(
    settings: Settings,
    *,
    include_service_logs: bool = False,
    now: datetime | None = None,
) -> MaintenanceResult:
    """Apply bounded retention only within configured runtime directories."""
    current_time = now or datetime.now(UTC)
    removed = []
    removed.extend(
        prune_directory(
            settings.screenshots_dir,
            suffix=".png",
            max_age_days=settings.retention_days,
            max_files=settings.screenshots_max_files,
            now=current_time,
        )
    )
    removed.extend(
        prune_directory(
            settings.calendar_dir,
            suffix=".ics",
            max_age_days=settings.retention_days,
            max_files=settings.calendar_max_files,
            now=current_time,
        )
    )

    rotated = []
    if rotate_file(
        settings.actions_log_path,
        max_bytes=settings.log_max_bytes,
        backups=settings.log_backups,
    ):
        rotated.append(settings.actions_log_path)

    if include_service_logs and settings.logs_dir.exists():
        for log_path in sorted(settings.logs_dir.glob("*.log")):
            if rotate_file(
                log_path,
                max_bytes=settings.log_max_bytes,
                backups=settings.log_backups,
            ):
                rotated.append(log_path)

    result = MaintenanceResult(tuple(removed), tuple(rotated))
    if result.removed or result.rotated:
        print(
            f"[maintenance] Removed {len(result.removed)} old file(s); "
            f"rotated {len(result.rotated)} log file(s).",
            flush=True,
        )
    return result


def prune_directory(
    directory: Path,
    *,
    suffix: str,
    max_age_days: int,
    max_files: int,
    now: datetime,
) -> list[Path]:
    if not directory.exists():
        return []

    candidates = [
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.casefold() == suffix.casefold()
    ]
    cutoff = now.timestamp() - timedelta(days=max(1, max_age_days)).total_seconds()
    removed = []

    for path in candidates:
        if path.stat().st_mtime < cutoff:
            path.unlink()
            removed.append(path)

    remaining = [path for path in candidates if path not in removed and path.exists()]
    remaining.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    for path in remaining[max(1, max_files) :]:
        path.unlink()
        removed.append(path)

    return removed


def rotate_file(path: Path, *, max_bytes: int, backups: int) -> bool:
    if not path.exists() or not path.is_file():
        return False
    if path.stat().st_size <= max(1, max_bytes):
        return False

    if backups <= 0:
        path.unlink()
        return True

    oldest = _backup_path(path, backups)
    if oldest.exists():
        oldest.unlink()
    for index in range(backups - 1, 0, -1):
        source = _backup_path(path, index)
        if source.exists():
            source.replace(_backup_path(path, index + 1))
    path.replace(_backup_path(path, 1))
    return True


def _backup_path(path: Path, index: int) -> Path:
    return path.with_name(f"{path.name}.{index}")
