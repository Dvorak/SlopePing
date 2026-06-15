from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from slopeping.checker import run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SlopePing schedule checker")
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument("--accept", metavar="LESSON_KEY", help="select Bestätigen for a pending lesson")
    action_group.add_argument("--decline", metavar="LESSON_KEY", help="select Absagen for a pending lesson")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.accept:
        raise SystemExit(run(action="accept", lesson_key=args.accept))
    if args.decline:
        raise SystemExit(run(action="decline", lesson_key=args.decline))
    raise SystemExit(run())
