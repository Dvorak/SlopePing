#!/usr/bin/env python
"""Apply SlopePing runtime retention before launchd opens service logs."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from slopeping.config import load_settings
    from slopeping.maintenance import maintain_runtime_files

    maintain_runtime_files(load_settings(), include_service_logs=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
