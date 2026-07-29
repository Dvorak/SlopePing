#!/usr/bin/env python
"""Generate safe, offline HTML previews of the SlopePing mobile UI."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from slopeping.ui_preview import main as preview_main

    return preview_main()


if __name__ == "__main__":
    raise SystemExit(main())
