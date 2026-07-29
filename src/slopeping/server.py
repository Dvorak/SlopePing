from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class WebhookServerSettings:
    host: str
    port: int
    token: str
    base_url: str
    ntfy_topic: str


def load_webhook_server_settings(
    env_file: str | Path = PROJECT_ROOT / ".env",
) -> WebhookServerSettings:
    load_dotenv(env_file)

    token = os.getenv("ACTION_WEBHOOK_TOKEN", "").strip()
    if not token:
        raise ValueError("Missing ACTION_WEBHOOK_TOKEN in .env")

    raw_port = os.getenv("WEBHOOK_PORT", "8000").strip() or "8000"
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise ValueError(f"WEBHOOK_PORT must be an integer, got {raw_port!r}") from exc

    if not 1 <= port <= 65535:
        raise ValueError("WEBHOOK_PORT must be between 1 and 65535")

    return WebhookServerSettings(
        host=os.getenv("WEBHOOK_HOST", "127.0.0.1").strip() or "127.0.0.1",
        port=port,
        token=token,
        base_url=os.getenv("ACTION_WEBHOOK_BASE_URL", "").strip(),
        ntfy_topic=os.getenv("NTFY_TOPIC", "").strip(),
    )


def print_startup_summary(settings: WebhookServerSettings) -> None:
    print("\nSlopePing Webhook Server", flush=True)
    print(f"  listen: {settings.host}:{settings.port}", flush=True)
    print(f"  health: http://localhost:{settings.port}/health", flush=True)
    print(f"  token:  {'*' * min(len(settings.token), 12)} (configured)", flush=True)
    if settings.base_url:
        print(f"  public URL: {settings.base_url}", flush=True)
    else:
        print("  warning: ACTION_WEBHOOK_BASE_URL is not configured", flush=True)
    if not settings.ntfy_topic:
        print("  warning: NTFY_TOPIC is not configured", flush=True)
    if settings.host == "0.0.0.0":
        print("  warning: server is exposed on all network interfaces", flush=True)


def main() -> int:
    try:
        settings = load_webhook_server_settings()
    except ValueError as exc:
        print(f"ERROR: {exc}", flush=True)
        return 1

    print_startup_summary(settings)
    uvicorn.run(
        "slopeping.webhook:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
    return 0
