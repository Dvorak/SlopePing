from __future__ import annotations

import argparse
from collections.abc import Sequence

from .checker import run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SlopePing schedule checker")
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument(
        "--accept",
        metavar="LESSON_KEY",
        help="select Bestätigen for a pending lesson",
    )
    action_group.add_argument(
        "--decline",
        metavar="LESSON_KEY",
        help="select Absagen for a pending lesson",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.accept:
        return run(action="accept", lesson_key=args.accept)
    if args.decline:
        return run(action="decline", lesson_key=args.decline)
    return run()
