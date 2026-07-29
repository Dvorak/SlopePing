#!/usr/bin/env python
"""Compatibility entry point for the SlopePing webhook server."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
os.chdir(ROOT)

from slopeping.server import main

if __name__ == "__main__":
    raise SystemExit(main())
