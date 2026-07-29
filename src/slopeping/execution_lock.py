from __future__ import annotations

import fcntl
import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO


class LockUnavailableError(RuntimeError):
    """Raised when another SlopePing process already owns the execution lock."""


@contextmanager
def execution_lock(path: Path, purpose: str) -> Iterator[None]:
    """Hold a non-blocking process-wide file lock for browser work."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+", encoding="utf-8")
    try:
        _acquire(handle, path)
        _write_owner(handle, purpose)
        yield
    finally:
        _release(handle)


def _acquire(handle: TextIO, path: Path) -> None:
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        owner = _read_owner(handle)
        detail = f" Current owner: {owner}." if owner else ""
        handle.close()
        raise LockUnavailableError(f"SlopePing is already running.{detail} Lock: {path}") from exc


def _write_owner(handle: TextIO, purpose: str) -> None:
    payload = {
        "pid": os.getpid(),
        "purpose": purpose,
        "started_at": datetime.now(UTC).isoformat(),
    }
    handle.seek(0)
    handle.truncate()
    json.dump(payload, handle, ensure_ascii=False)
    handle.write("\n")
    handle.flush()
    os.fsync(handle.fileno())


def _read_owner(handle: TextIO) -> str:
    try:
        handle.seek(0)
        raw = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return ""
    if not isinstance(raw, dict):
        return ""
    return ", ".join(
        f"{key}={raw[key]}" for key in ("pid", "purpose", "started_at") if raw.get(key)
    )


def _release(handle: TextIO) -> None:
    if handle.closed:
        return
    try:
        handle.seek(0)
        handle.truncate()
        handle.flush()
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()
