from pathlib import Path

import pytest

from slopeping.runtime_migration import MigrationConflictError, migrate_runtime_data


def test_migration_moves_runtime_data_and_updates_env(tmp_path: Path) -> None:
    (tmp_path / "state.json").write_text('{"records": []}\n', encoding="utf-8")
    (tmp_path / "screenshots").mkdir()
    (tmp_path / "screenshots" / "one.png").write_bytes(b"png")
    env_path = tmp_path / ".env"
    env_path.write_text(
        "SKI_USERNAME=user\n"
        "SKI_PASSWORD=private\n"
        "SKI_STATE_PATH=state.json\n"
        "SKI_SCREENSHOTS_DIR=screenshots\n",
        encoding="utf-8",
    )

    result = migrate_runtime_data(
        tmp_path,
        Path("var"),
        timestamp="20260730-120000",
    )

    assert not (tmp_path / "state.json").exists()
    assert (tmp_path / "var" / "state.json").exists()
    assert (tmp_path / "var" / "screenshots" / "one.png").exists()
    assert "SKI_PASSWORD=private" in env_path.read_text(encoding="utf-8")
    assert "SKI_STATE_PATH=var/state.json" in env_path.read_text(encoding="utf-8")
    assert result.env_backup is not None
    assert result.env_backup.exists()


def test_migration_refuses_to_overwrite_existing_targets(tmp_path: Path) -> None:
    source = tmp_path / "state.json"
    target = tmp_path / "var" / "state.json"
    source.write_text("source", encoding="utf-8")
    target.parent.mkdir()
    target.write_text("target", encoding="utf-8")

    with pytest.raises(MigrationConflictError, match="already exist"):
        migrate_runtime_data(tmp_path, Path("var"), update_env=False)

    assert source.read_text(encoding="utf-8") == "source"
    assert target.read_text(encoding="utf-8") == "target"
