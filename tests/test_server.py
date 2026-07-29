import pytest

from slopeping.server import load_webhook_server_settings, main

SECRET = "a-secure-test-secret-that-is-long-enough"


def test_server_settings_use_safe_defaults(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ACTION_WEBHOOK_TOKEN", SECRET)
    monkeypatch.delenv("WEBHOOK_HOST", raising=False)
    monkeypatch.delenv("WEBHOOK_PORT", raising=False)
    monkeypatch.delenv("ACTION_WEBHOOK_BASE_URL", raising=False)
    monkeypatch.delenv("NTFY_TOPIC", raising=False)

    settings = load_webhook_server_settings(tmp_path / "missing.env")

    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.token == SECRET


@pytest.mark.parametrize("port", ["zero", "0", "65536"])
def test_server_settings_reject_invalid_ports(monkeypatch, tmp_path, port: str) -> None:
    monkeypatch.setenv("ACTION_WEBHOOK_TOKEN", SECRET)
    monkeypatch.setenv("WEBHOOK_PORT", port)

    with pytest.raises(ValueError, match="WEBHOOK_PORT"):
        load_webhook_server_settings(tmp_path / "missing.env")


def test_server_main_stops_before_uvicorn_without_token(monkeypatch, capsys) -> None:
    monkeypatch.delenv("ACTION_WEBHOOK_TOKEN", raising=False)
    monkeypatch.setattr(
        "slopeping.server.load_webhook_server_settings",
        lambda: (_ for _ in ()).throw(ValueError("Missing token")),
    )
    uvicorn_calls = []
    monkeypatch.setattr(
        "slopeping.server.uvicorn.run",
        lambda *args, **kwargs: uvicorn_calls.append((args, kwargs)),
    )

    assert main() == 1
    assert uvicorn_calls == []
    assert "Missing token" in capsys.readouterr().out


def test_server_rejects_short_webhook_secret(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ACTION_WEBHOOK_TOKEN", "too-short")

    with pytest.raises(ValueError, match="at least 32"):
        load_webhook_server_settings(tmp_path / "missing.env")
