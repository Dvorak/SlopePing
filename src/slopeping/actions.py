from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import Locator, Page, TimeoutError as PlaywrightTimeoutError

from .config import Settings
from .parser import ParsedScheduleRow, parse_overview_rows
from .state import ScheduleRecord


ACTION_LABELS = {
    "accept": "Bestätigen",
    "decline": "Absagen",
}


def perform_lesson_action(
    page: Page,
    settings: Settings,
    action: str,
    lesson_key: str,
) -> bool:
    label = ACTION_LABELS[action]
    print(f"[action] Looking for lesson: {lesson_key}", flush=True)
    parsed_rows = parse_overview_rows(page, settings.selectors)
    match = _find_matching_row(parsed_rows, lesson_key)
    if match is None:
        message = f"Could not find lesson matching {lesson_key!r}."
        print(f"[action] {message}", flush=True)
        _write_action_log(action, lesson_key, None, "not_found", message)
        return False

    record = match.record
    print(f"[action] Matched lesson_id: {record.lesson_id}", flush=True)
    print(f"[action] confirmation_status: {record.confirmation_status}", flush=True)
    if record.confirmation_status != "pending":
        message = "Refusing to act because the lesson is not pending."
        print(f"[action] {message}", flush=True)
        _write_action_log(action, lesson_key, record, "not_pending", message)
        return False

    select = match.row.locator("select").first
    if select.count() == 0:
        message = "Could not find a confirmation select in the matched row."
        print(f"[action] {message}", flush=True)
        _write_action_log(action, lesson_key, record, "missing_select", message)
        return False

    if label not in (record.available_actions or []):
        message = f"Action {label!r} is not available for the matched lesson."
        print(f"[action] {message}", flush=True)
        _write_action_log(action, lesson_key, record, "action_unavailable", message)
        return False

    before = _save_action_screenshot(page, settings, action, "before")
    print(f"[action] Selecting {label!r}.", flush=True)
    try:
        select.select_option(label=label)
    except Exception as exc:
        message = f"Could not select {label!r}: {exc}"
        print(f"[action] {message}", flush=True)
        _write_action_log(action, lesson_key, record, "select_failed", message, before_screenshot=before)
        return False

    save_button = _find_save_button(page)
    if save_button is None:
        message = "Could not find Speichern button."
        print(f"[action] {message}", flush=True)
        _write_action_log(action, lesson_key, record, "missing_save", message, before_screenshot=before)
        return False

    print("[action] Clicking Speichern.", flush=True)
    try:
        save_button.click()
        _wait_after_save(page)
    except Exception as exc:
        after = _save_action_screenshot(page, settings, action, "after-error")
        message = f"Could not save action: {exc}"
        print(f"[action] {message}", flush=True)
        _write_action_log(
            action,
            lesson_key,
            record,
            "save_failed",
            message,
            before_screenshot=before,
            after_screenshot=after,
        )
        return False

    after = _save_action_screenshot(page, settings, action, "after")
    message = f"Selected {label!r} and clicked Speichern."
    print(f"[action] {message}", flush=True)
    _write_action_log(
        action,
        lesson_key,
        record,
        "success",
        message,
        before_screenshot=before,
        after_screenshot=after,
    )
    return True


def _find_matching_row(parsed_rows: list[ParsedScheduleRow], lesson_key: str) -> ParsedScheduleRow | None:
    needle = lesson_key.strip()
    for parsed in parsed_rows:
        record = parsed.record
        if needle in {record.key, record.lesson_id}:
            return parsed
        if record.key.startswith(needle) and len(needle) >= 8:
            return parsed
    return None


def _find_save_button(page: Page) -> Locator | None:
    candidates = [
        page.get_by_text("Speichern", exact=False).first,
        page.locator("input[type='submit']").first,
        page.locator("button").filter(has_text="Speichern").first,
    ]
    for candidate in candidates:
        try:
            if candidate.count() > 0 and candidate.is_visible():
                return candidate
        except Exception:
            continue
    return None


def _wait_after_save(page: Page) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except PlaywrightTimeoutError:
        try:
            page.wait_for_load_state("domcontentloaded", timeout=5000)
        except PlaywrightTimeoutError:
            pass


def _save_action_screenshot(page: Page, settings: Settings, action: str, phase: str) -> str:
    settings.screenshots_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = settings.screenshots_dir / f"action-{action}-{phase}-{timestamp}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"[action] Saved {phase} screenshot: {path}", flush=True)
    return str(path)


def _write_action_log(
    action: str,
    lesson_key: str,
    record: ScheduleRecord | None,
    result: str,
    message: str,
    before_screenshot: str | None = None,
    after_screenshot: str | None = None,
) -> None:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "lesson_key": lesson_key,
        "result": result,
        "message": message,
        "lesson": asdict(record) if record is not None else None,
        "lesson_id": record.lesson_id if record is not None else None,
        "before_screenshot": before_screenshot,
        "after_screenshot": after_screenshot,
    }
    path = Path("actions.log")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False))
        handle.write("\n")
    print(f"[action] Wrote action log: {path}", flush=True)
