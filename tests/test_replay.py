from pathlib import Path

import pytest

from slopeping.replay import ReplayDetectedError, consume_nonce


def test_consumed_nonce_cannot_be_replayed(tmp_path: Path) -> None:
    path = tmp_path / "nonces.json"

    consume_nonce(path, "nonce-1", expires_at=2000, now=1000)

    with pytest.raises(ReplayDetectedError, match="already been submitted"):
        consume_nonce(path, "nonce-1", expires_at=2000, now=1001)


def test_expired_nonces_are_pruned_and_can_be_reused(tmp_path: Path) -> None:
    path = tmp_path / "nonces.json"

    consume_nonce(path, "nonce-1", expires_at=1000, now=900)
    consume_nonce(path, "nonce-1", expires_at=2000, now=1001)

    assert "nonce-1" in path.read_text(encoding="utf-8")
