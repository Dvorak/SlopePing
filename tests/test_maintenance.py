import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from slopeping.maintenance import prune_directory, rotate_file


def write_file(path: Path, content: str, modified_at: datetime) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    timestamp = modified_at.timestamp()
    os.utime(path, (timestamp, timestamp))


def test_prune_directory_removes_expired_and_excess_files(tmp_path: Path) -> None:
    now = datetime(2026, 7, 30, tzinfo=UTC)
    directory = tmp_path / "screenshots"
    expired = directory / "expired.png"
    old = directory / "old.png"
    recent = directory / "recent.png"
    unrelated = directory / "keep.txt"
    write_file(expired, "x", now - timedelta(days=31))
    write_file(old, "x", now - timedelta(days=2))
    write_file(recent, "x", now - timedelta(days=1))
    write_file(unrelated, "x", now - timedelta(days=90))

    removed = prune_directory(
        directory,
        suffix=".png",
        max_age_days=30,
        max_files=1,
        now=now,
    )

    assert set(removed) == {expired, old}
    assert recent.exists()
    assert unrelated.exists()


def test_rotate_file_keeps_bounded_backups(tmp_path: Path) -> None:
    path = tmp_path / "checker.log"
    path.write_text("current-log", encoding="utf-8")
    path.with_name("checker.log.1").write_text("previous-log", encoding="utf-8")
    path.with_name("checker.log.2").write_text("oldest-log", encoding="utf-8")

    assert rotate_file(path, max_bytes=5, backups=2) is True

    assert not path.exists()
    assert path.with_name("checker.log.1").read_text(encoding="utf-8") == "current-log"
    assert path.with_name("checker.log.2").read_text(encoding="utf-8") == "previous-log"
