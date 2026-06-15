from __future__ import annotations

import traceback

from .actions import perform_lesson_action
from .browser import BrowserSession
from .config import load_settings
from .notify import notify_new_lessons, notify_run_report
from .parser import parse_overview_records
from .state import ScheduleRecord, StateChange, diff_records, load_records, save_records


def run(action: str | None = None, lesson_key: str | None = None) -> int:
    print("[start] Loading settings from .env.", flush=True)
    settings = load_settings()
    print("[start] Settings loaded.", flush=True)

    with BrowserSession(settings) as browser:
        try:
            print("[step] Login and open schedule page.", flush=True)
            page = browser.login_and_open_schedule()
            if action is not None and lesson_key is not None:
                print(f"[action] Running requested action: {action}", flush=True)
                return 0 if perform_lesson_action(page, settings, action, lesson_key) else 1

            print("[step] Parse Übersicht schedule records.", flush=True)
            records = parse_overview_records(page, settings.selectors)
            print(f"[step] Parsed {len(records)} schedule record(s).", flush=True)
            print("[step] Save success screenshot.", flush=True)
            screenshot = browser.save_screenshot("arbeitsplan")
            print(f"[step] Load previous records from {settings.state_path}.", flush=True)
            previous_records = load_records(settings.state_path)
            print(f"[step] Loaded {len(previous_records)} previous record(s).", flush=True)
            print("[step] Compare current records with previous state.", flush=True)
            changes = diff_records(previous_records, records)
            _print_result(records, changes, str(screenshot))
            new_lessons = [change.current for change in changes if change.kind == "new"]
            print(f"[step] New lessons to notify: {len(new_lessons)}.", flush=True)
            pending_lessons = [record for record in records if record.confirmation_status == "pending"]
            print(f"[step] Pending lessons needing action: {len(pending_lessons)}.", flush=True)
            _print_action_hints(pending_lessons)
            if _notify_always_send_report():
                print("[notify] NOTIFY_ALWAYS_SEND_REPORT is enabled; sending run report.", flush=True)
                notify_run_report(records, new_lessons)
            else:
                print("[notify] Sending notification if new or pending lessons exist.", flush=True)
                notify_new_lessons(_merge_lessons(new_lessons, pending_lessons))
            print(f"[step] Save current records to {settings.state_path}.", flush=True)
            save_records(settings.state_path, records)
            print("[done] Checker completed successfully.", flush=True)
            return 0
        except Exception as exc:
            print(f"ERROR: {exc}")
            print(traceback.format_exc())
            try:
                error_screenshot = browser.save_screenshot("error")
                print(f"Saved error screenshot: {error_screenshot}")
            except Exception:
                print("Could not save an error screenshot because the browser was not available.")
            return 1


def _print_result(records: list[ScheduleRecord], changes: list[StateChange], screenshot: str) -> None:
    print(f"Parsed {len(records)} schedule record(s).")
    print(f"Saved screenshot: {screenshot}")

    if not changes:
        print("No new courses or status changes detected.")
        return

    print(f"\nDetected {len(changes)} change(s):")
    for change in changes:
        if change.kind == "new":
            print("\nNEW course:")
            _print_record(change.current)
        else:
            print("\nCHANGED course:")
            _print_record(change.current)
            if change.previous is not None:
                print(f"Previous Bestätigung: {change.previous.bestaetigung}")


def _print_record(record: ScheduleRecord) -> None:
    print(f"  lesson_id: {record.lesson_id}")
    print(f"  Tag: {record.tag}")
    print(f"  Von/Bis: {record.von} - {record.bis}")
    print(f"  Raum/Ort: {record.raum_ort}")
    print(f"  Trainingsbezeichnung: {record.trainingsbezeichnung}")
    print(f"  Bestätigung: {record.bestaetigung}")
    print(f"  confirmation_status: {record.confirmation_status}")
    print(f"  available_actions: {_format_actions(record.available_actions)}")


def _format_actions(actions: list[str] | None) -> str:
    if not actions:
        return "-"
    return ", ".join(actions)


def _print_action_hints(pending_lessons: list[ScheduleRecord]) -> None:
    if not pending_lessons:
        return

    print("\nAction needed. You can copy one of these commands:", flush=True)
    for lesson in pending_lessons:
        lesson_id = lesson.lesson_id
        print("", flush=True)
        print(f"Lesson: {lesson.tag} {lesson.von}-{lesson.bis} {lesson.trainingsbezeichnung}", flush=True)
        print(f"Available actions: {_format_actions(lesson.available_actions)}", flush=True)
        print(f'python run_checker.py --accept "{lesson_id}"', flush=True)
        print(f'python run_checker.py --decline "{lesson_id}"', flush=True)


def _merge_lessons(first: list[ScheduleRecord], second: list[ScheduleRecord]) -> list[ScheduleRecord]:
    merged: list[ScheduleRecord] = []
    seen: set[str] = set()
    for lesson in first + second:
        if lesson.key in seen:
            continue
        seen.add(lesson.key)
        merged.append(lesson)
    return merged


def _notify_always_send_report() -> bool:
    import os

    value = os.getenv("NOTIFY_ALWAYS_SEND_REPORT", "")
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}
