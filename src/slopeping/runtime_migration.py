from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


class MigrationConflictError(RuntimeError):
    """Raised before migration when a source and target both exist."""


@dataclass(frozen=True)
class MigrationMove:
    source: Path
    target: Path


@dataclass(frozen=True)
class MigrationResult:
    moved: tuple[MigrationMove, ...]
    env_backup: Path | None


def planned_moves(project_root: Path, runtime_dir: Path) -> list[MigrationMove]:
    target_root = runtime_dir if runtime_dir.is_absolute() else project_root / runtime_dir
    mappings = (
        ("state.json", "state.json"),
        ("state.json.bak", "state.json.bak"),
        ("actions.log", "actions.log"),
        ("screenshots", "screenshots"),
        ("calendar_events", "calendar_events"),
        ("logs", "logs"),
        (".slopeping-health.json", "health.json"),
        (".slopeping-nonces.json", "used-action-nonces.json"),
    )
    return [
        MigrationMove(project_root / source, target_root / target) for source, target in mappings
    ]


def migrate_runtime_data(
    project_root: Path,
    runtime_dir: Path,
    *,
    update_env: bool = True,
    timestamp: str | None = None,
) -> MigrationResult:
    moves = planned_moves(project_root, runtime_dir)
    conflicts = [move for move in moves if move.source.exists() and move.target.exists()]
    if conflicts:
        details = ", ".join(f"{move.source} -> {move.target}" for move in conflicts)
        raise MigrationConflictError(f"Migration targets already exist: {details}")

    moved = []
    for move in moves:
        if not move.source.exists():
            continue
        move.target.parent.mkdir(parents=True, exist_ok=True)
        move.source.replace(move.target)
        moved.append(move)

    env_backup = None
    env_path = project_root / ".env"
    if update_env and env_path.exists():
        current_timestamp = timestamp or datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        backup_dir = project_root / ".local" / "runtime-migration" / current_timestamp
        backup_dir.mkdir(parents=True, exist_ok=True)
        env_backup = backup_dir / ".env.backup"
        shutil.copy2(env_path, env_backup)
        update_env_paths(env_path, runtime_dir)

    return MigrationResult(tuple(moved), env_backup)


def update_env_paths(env_path: Path, runtime_dir: Path) -> None:
    runtime = str(runtime_dir)
    values = {
        "SLOPEPING_RUNTIME_DIR": runtime,
        "SKI_STATE_PATH": str(runtime_dir / "state.json"),
        "SKI_SCREENSHOTS_DIR": str(runtime_dir / "screenshots"),
        "SKI_HEALTH_PATH": str(runtime_dir / "health.json"),
        "SKI_LOCK_PATH": str(runtime_dir / "slopeping.lock"),
        "SKI_ACTIONS_LOG_PATH": str(runtime_dir / "actions.log"),
        "SKI_CALENDAR_DIR": str(runtime_dir / "calendar_events"),
        "SKI_LOGS_DIR": str(runtime_dir / "logs"),
        "SKI_USED_NONCES_PATH": str(runtime_dir / "used-action-nonces.json"),
    }
    original = env_path.read_text(encoding="utf-8").splitlines()
    found = set()
    updated = []
    pattern = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=")

    for line in original:
        match = pattern.match(line)
        key = match.group(1) if match else None
        if key in values:
            updated.append(f"{key}={values[key]}")
            found.add(key)
        else:
            updated.append(line)

    missing = [key for key in values if key not in found]
    if missing:
        if updated and updated[-1]:
            updated.append("")
        updated.append("# SlopePing runtime paths")
        updated.extend(f"{key}={values[key]}" for key in missing)

    temp_path = env_path.with_suffix(".env.tmp")
    temp_path.write_text("\n".join(updated) + "\n", encoding="utf-8")
    temp_path.replace(env_path)
