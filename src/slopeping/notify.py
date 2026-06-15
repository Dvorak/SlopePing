from __future__ import annotations

import os
import urllib.error
import urllib.request
from typing import TypeAlias

from .state import ScheduleRecord


Lesson: TypeAlias = ScheduleRecord


def notify_new_lessons(new_lessons: list[Lesson]) -> None:
    if not new_lessons:
        return

    _send_notification(
        subject=_notification_subject(new_lessons),
        body=_format_lessons(new_lessons),
        lessons_for_console=new_lessons,
    )


def notify_run_report(current_lessons: list[Lesson], new_lessons: list[Lesson]) -> None:
    if _pending_lessons(current_lessons):
        subject = "SlopePing: action needed"
    else:
        subject = (
            f"SlopePing test: {len(current_lessons)} current lesson(s), "
            f"{len(new_lessons)} new lesson(s)"
        )
    _send_notification(
        subject=subject,
        body=_format_run_report(current_lessons, new_lessons),
        lessons_for_console=current_lessons,
    )


def _send_notification(subject: str, body: str, lessons_for_console: list[Lesson]) -> None:
    channel = os.getenv("NOTIFY_CHANNEL", "console").strip().casefold() or "console"

    if channel == "ntfy":
        if _send_ntfy(subject, body):
            print("[notify] ntfy notification sent.", flush=True)
            return
        _notify_console(subject, body)
        return

    if channel != "console":
        print(f"WARNING: Unknown NOTIFY_CHANNEL={channel!r}; falling back to console.")

    if lessons_for_console:
        _notify_console(subject, body)


def _notify_console(subject: str, body: str) -> None:
    print(f"\nNotification: {subject}")
    print(body)


def _send_ntfy(subject: str, body: str) -> bool:
    server = os.getenv("NTFY_SERVER", "").strip().rstrip("/")
    topic = os.getenv("NTFY_TOPIC", "").strip()

    missing = []
    if not server:
        missing.append("NTFY_SERVER")
    if not topic:
        missing.append("NTFY_TOPIC")
    if missing:
        print(f"WARNING: Missing ntfy notification config: {', '.join(missing)}. Falling back to console.")
        return False

    request = urllib.request.Request(
        f"{server}/{topic}",
        data=body.encode("utf-8"),
        method="POST",
        headers={
            "Title": subject,
            "Content-Type": "text/plain; charset=utf-8",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=20):
            pass
    except (urllib.error.URLError, OSError) as exc:
        print(f"ERROR: ntfy notification failed: {exc}")
        return False

    return True


def _notification_subject(lessons: list[Lesson]) -> str:
    if _pending_lessons(lessons):
        return "SlopePing: action needed"
    return f"SlopePing: {len(lessons)} new lesson(s)"


def _pending_lessons(lessons: list[Lesson]) -> list[Lesson]:
    return [lesson for lesson in lessons if lesson.confirmation_status == "pending"]


def _format_run_report(current_lessons: list[Lesson], new_lessons: list[Lesson]) -> str:
    current_text = _format_lessons(current_lessons) if current_lessons else "No current lessons found."
    new_text = _format_lessons(new_lessons) if new_lessons else "No new lessons detected."
    return "\n\n".join(
        [
            "Current lessons:",
            current_text,
            "New lessons pending confirmation:",
            new_text,
        ]
    )


def _format_lessons(new_lessons: list[Lesson]) -> str:
    blocks = []
    for lesson in new_lessons:
        blocks.append(
            "\n".join(
                [
                    f"lesson_id: {lesson.lesson_id}",
                    f"Tag: {lesson.tag}",
                    f"Von: {lesson.von}",
                    f"Bis: {lesson.bis}",
                    f"Raum/Ort: {lesson.raum_ort}",
                    f"Trainingsbezeichnung: {lesson.trainingsbezeichnung}",
                    f"Bestätigung: {lesson.bestaetigung}",
                    f"confirmation_status: {lesson.confirmation_status}",
                    f"available_actions: {_format_actions(lesson.available_actions)}",
                ]
            )
        )
    return "\n\n".join(blocks)


def _format_actions(actions: list[str] | None) -> str:
    if not actions:
        return "-"
    return ", ".join(actions)
