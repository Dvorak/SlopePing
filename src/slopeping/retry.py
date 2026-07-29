from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

Result = TypeVar("Result")


def retry_call(
    operation: Callable[[], Result],
    *,
    attempts: int,
    delay_seconds: float,
    retry_on: tuple[type[BaseException], ...],
    label: str,
    sleep: Callable[[float], None] = time.sleep,
) -> Result:
    """Retry a transient operation with bounded exponential backoff."""
    total_attempts = max(1, attempts)
    for attempt in range(1, total_attempts + 1):
        try:
            return operation()
        except retry_on as exc:
            if attempt >= total_attempts:
                raise
            delay = max(0.0, delay_seconds) * (2 ** (attempt - 1))
            print(
                f"[retry] {label} failed on attempt {attempt}/{total_attempts}: {exc}. "
                f"Retrying in {delay:.1f}s.",
                flush=True,
            )
            sleep(delay)

    raise AssertionError("retry loop ended without returning or raising")
