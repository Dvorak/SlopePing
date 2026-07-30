from pathlib import Path

from slopeping.config import load_runtime_paths

PATH_VARIABLES = (
    "SLOPEPING_RUNTIME_DIR",
    "SKI_ACTIONS_LOG_PATH",
    "SKI_CALENDAR_DIR",
    "SKI_HEALTH_PATH",
    "SKI_LOCK_PATH",
    "SKI_LOGS_DIR",
    "SKI_SCREENSHOTS_DIR",
    "SKI_STATE_PATH",
    "SKI_USED_NONCES_PATH",
)


def test_runtime_paths_default_to_var(monkeypatch, tmp_path: Path) -> None:
    for name in PATH_VARIABLES:
        monkeypatch.delenv(name, raising=False)

    paths = load_runtime_paths(tmp_path / "missing.env")

    assert paths.runtime_dir == Path("var")
    assert paths.state_path == Path("var/state.json")
    assert paths.screenshots_dir == Path("var/screenshots")
    assert paths.logs_dir == Path("var/logs")
    assert paths.used_nonces_path == Path("var/used-action-nonces.json")


def test_individual_runtime_paths_can_be_overridden(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SLOPEPING_RUNTIME_DIR", "runtime")
    monkeypatch.setenv("SKI_STATE_PATH", "custom/state.json")

    paths = load_runtime_paths(tmp_path / "missing.env")

    assert paths.runtime_dir == Path("runtime")
    assert paths.state_path == Path("custom/state.json")
    assert paths.logs_dir == Path("runtime/logs")
