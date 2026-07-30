#!/usr/bin/env python
"""Move legacy root runtime data into the configured SlopePing var directory."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from slopeping.runtime_migration import migrate_runtime_data, planned_moves

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runtime-dir",
        type=Path,
        default=Path("var"),
        help="Runtime directory, relative to the project root by default.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the migration. Without this flag, only print the plan.",
    )
    args = parser.parse_args()

    moves = [move for move in planned_moves(root, args.runtime_dir) if move.source.exists()]
    if not args.apply:
        print("Planned runtime migration:")
        for move in moves:
            print(f"  {move.source} -> {move.target}")
        print("No files changed. Re-run with --apply after stopping SlopePing services.")
        return 0

    result = migrate_runtime_data(root, args.runtime_dir)
    for move in result.moved:
        print(f"Moved {move.source} -> {move.target}")
    if result.env_backup:
        print(f"Backed up .env to {result.env_backup}")
    print(f"Runtime migration complete: {len(result.moved)} item(s) moved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
