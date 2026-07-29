#!/usr/bin/env python
"""Create short-lived SlopePing control and calendar links from local config."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from slopeping.security import build_access_url

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ttl",
        type=int,
        default=None,
        help="Link lifetime in seconds; defaults to WEBHOOK_LINK_TTL_SECONDS.",
    )
    args = parser.parse_args()

    load_dotenv(root / ".env")
    base_url = os.getenv("ACTION_WEBHOOK_BASE_URL", "").strip()
    secret = os.getenv("ACTION_WEBHOOK_TOKEN", "").strip()
    if not base_url or not secret:
        print("ERROR: ACTION_WEBHOOK_BASE_URL and ACTION_WEBHOOK_TOKEN are required.")
        return 1

    ttl = args.ttl or _int_env("WEBHOOK_LINK_TTL_SECONDS", 86400)
    print(build_access_url(base_url, "/control", secret, "control", ttl))
    print(build_access_url(base_url, "/calendar", secret, "calendar", ttl))
    return 0


def _int_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


if __name__ == "__main__":
    raise SystemExit(main())
