from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class ReplayDetectedError(RuntimeError):
    """Raised when an action token nonce has already been consumed."""


def consume_nonce(
    path: Path,
    nonce: str,
    expires_at: int,
    *,
    now: int | None = None,
) -> None:
    current_time = int(time.time()) if now is None else now
    nonces = _load_nonces(path)
    active = {
        key: expiry
        for key, expiry in nonces.items()
        if isinstance(expiry, int) and expiry >= current_time
    }
    if nonce in active:
        raise ReplayDetectedError("This action confirmation has already been submitted")

    active[nonce] = expires_at
    _save_nonces(path, active)


def _load_nonces(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    values: Any = raw.get("nonces", {})
    if not isinstance(values, dict):
        return {}
    return {
        str(key): value
        for key, value in values.items()
        if isinstance(value, int) and not isinstance(value, bool)
    }


def _save_nonces(path: Path, nonces: dict[str, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(
        json.dumps({"version": 1, "nonces": nonces}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(path)
