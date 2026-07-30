#!/usr/bin/env python
"""Print one configured SlopePing runtime path for shell wrappers."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from slopeping.config import load_runtime_paths

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "name",
        choices=(
            "actions_log_path",
            "calendar_dir",
            "health_path",
            "lock_path",
            "logs_dir",
            "runtime_dir",
            "screenshots_dir",
            "state_path",
            "used_nonces_path",
        ),
    )
    args = parser.parse_args()
    paths = load_runtime_paths(root / ".env")
    configured = getattr(paths, args.name)
    path = configured if configured.is_absolute() else root / configured
    print(path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
