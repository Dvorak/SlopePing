from __future__ import annotations

import traceback
from dataclasses import asdict

from .browser import BrowserSession
from .config import load_settings
from .notify import notify_new_lessons, notify_run_report
from .parser import parse_overview_records
from .state import ScheduleRecord, StateChange, diff_records, load_records, save_records


def run() -> int:
    print("[start] Loading settings from .env.", flush=True)
    settings = load_settings()
    print("[start] Settings loaded.", flush=True)

    with BrowserSession(settings) as browser:
        try:
            print("[step] Login and open schedule page.", flush=True)
            page = browser.login_and_open_schedule()
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
            if _notify_always_send_report():
                print("[notify] NOTIFY_ALWAYS_SEND_REPORT is enabled; sending run report.", flush=True)
                notify_run_report(records, new_lessons)
            else:
                print("[notify] Sending notification only if new lessons exist.", flush=True)
                notify_new_lessons(new_lessons)
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
        current = asdict(change.current)
        if change.kind == "new":
            print("\nNEW course:")
            _print_record(current)
        else:
            print("\nCHANGED course:")
            _print_record(current)
            if change.previous is not None:
                print(f"Previous Bestätigung: {change.previous.bestaetigung}")


def _print_record(record: dict[str, str]) -> None:
    print(f"  Tag: {record['tag']}")
    print(f"  Von/Bis: {record['von']} - {record['bis']}")
    print(f"  Raum/Ort: {record['raum_ort']}")
    print(f"  Trainingsbezeichnung: {record['trainingsbezeichnung']}")
    print(f"  Bestätigung: {record['bestaetigung']}")


def _notify_always_send_report() -> bool:
    import os

    value = os.getenv("NOTIFY_ALWAYS_SEND_REPORT", "")
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}
