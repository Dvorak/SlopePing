from pathlib import Path

import pytest

from slopeping.execution_lock import LockUnavailableError, execution_lock


def test_lock_blocks_a_second_owner_and_releases_after_exit(tmp_path: Path) -> None:
    path = tmp_path / "slopeping.lock"

    with (
        execution_lock(path, "first"),
        pytest.raises(LockUnavailableError, match="purpose=first"),
        execution_lock(path, "second"),
    ):
        raise AssertionError("second owner must not acquire the lock")

    with execution_lock(path, "after-release"):
        assert path.exists()


def test_lock_releases_after_an_exception(tmp_path: Path) -> None:
    path = tmp_path / "slopeping.lock"

    with pytest.raises(RuntimeError, match="boom"), execution_lock(path, "failing"):
        raise RuntimeError("boom")

    with execution_lock(path, "recovered"):
        assert path.read_text(encoding="utf-8")
