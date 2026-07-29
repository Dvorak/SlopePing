from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

from .state import ScheduleRecord
from .web_views import (
    render_calendar_page,
    render_confirmation_page,
    render_control_page,
    render_result_page,
)

PREVIEW_TOKEN = "preview-only"
PREVIEW_CHECKED_AT = "2026-07-29T20:00:00+02:00"


def build_preview_records() -> list[ScheduleRecord]:
    """Return anonymous sample lessons for local UI previews."""
    return [
        ScheduleRecord(
            tag="Sa, 01.08.2026",
            von="09:00",
            bis="11:00",
            raum_ort="Skihalle",
            trainingsbezeichnung="Snowboard Gruppenkurs",
            bestaetigung="Bitte auswählen",
            confirmation_status="pending",
            available_actions=["Bestätigen", "Absagen"],
        ),
        ScheduleRecord(
            tag="So, 02.08.2026",
            von="14:00",
            bis="16:00",
            raum_ort="Piste 2",
            trainingsbezeichnung="Privatkurs Ski",
            bestaetigung="Bestätigt",
            confirmation_status="confirmed",
            available_actions=[],
        ),
    ]


def write_ui_previews(output_dir: Path) -> list[Path]:
    """Render production UI functions with anonymous data and write static HTML."""
    records = build_preview_records()
    pending = records[0]
    pages = {
        "control.html": render_control_page(records, PREVIEW_TOKEN, PREVIEW_CHECKED_AT),
        "confirmation.html": render_confirmation_page(pending, "accept", PREVIEW_TOKEN),
        "result.html": render_result_page(
            {
                "status": "success",
                "message": "Preview only: no remote action was performed.",
                "lesson_id": pending.lesson_id,
            }
        ),
        "calendar.html": render_calendar_page(records, PREVIEW_TOKEN, PREVIEW_CHECKED_AT),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for filename, content in pages.items():
        path = output_dir / filename
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def capture_ui_previews(html_dir: Path, screenshot_dir: Path) -> list[Path]:
    """Capture mobile screenshots of previously generated static previews."""
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    targets = {
        "control.html": "control-page-preview.png",
        "confirmation.html": "confirmation-page-preview.png",
    }
    written = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 430, "height": 932},
            device_scale_factor=1,
        )
        for html_name, screenshot_name in targets.items():
            page.goto((html_dir / html_name).resolve().as_uri())
            screenshot_path = screenshot_dir / screenshot_name
            page.screenshot(path=str(screenshot_path), full_page=True)
            written.append(screenshot_path)
        browser.close()

    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate offline SlopePing UI previews with anonymous lessons."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/ui-preview"),
        help="Output directory for static HTML previews.",
    )
    parser.add_argument(
        "--screenshots",
        type=Path,
        help="Optional directory for mobile PNG screenshots.",
    )
    args = parser.parse_args(argv)

    for path in write_ui_previews(args.output):
        print(path)
    if args.screenshots:
        for path in capture_ui_previews(args.output, args.screenshots):
            print(path)
    return 0
