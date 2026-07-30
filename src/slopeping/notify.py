from __future__ import annotations

import os
import time
import urllib.error
import urllib.request
from datetime import datetime
from typing import TypeAlias

from .security import build_access_url
from .state import ScheduleRecord

Lesson: TypeAlias = ScheduleRecord


def notify_new_lessons(new_lessons: list[Lesson]) -> None:
    if not new_lessons:
        return

    _send_notification(
        subject=_notification_subject(new_lessons),
        body=_format_compact_lessons(new_lessons),
    )


def notify_compact_report(
    current_lessons: list[Lesson],
    new_lessons: list[Lesson],
) -> None:
    pending_lessons = _pending_lessons(current_lessons)
    notable_lessons = _merge_lessons(new_lessons, pending_lessons)

    if pending_lessons:
        subject = f"SlopePing · {len(pending_lessons)} 节课程待确认"
    elif new_lessons:
        subject = f"SlopePing · {len(new_lessons)} 节新课程"
    else:
        subject = f"SlopePing · {datetime.now().astimezone():%H:%M} 检查完成"

    _send_notification(
        subject=subject,
        body=_format_compact_report(current_lessons, new_lessons, notable_lessons),
    )


def notify_run_report(current_lessons: list[Lesson], new_lessons: list[Lesson]) -> None:
    pending_count = len(_pending_lessons(current_lessons))
    if pending_count:
        subject = f"SlopePing · {pending_count} 节课程待确认"
    else:
        subject = (
            f"SlopePing test: {len(current_lessons)} current lesson(s), "
            f"{len(new_lessons)} new lesson(s)"
        )
    _send_notification(
        subject=subject,
        body=_format_run_report(current_lessons, new_lessons),
    )


def notify_run_failure(error: BaseException, consecutive_failures: int) -> None:
    _send_notification(
        subject="SlopePing · 检查失败",
        body="\n".join(
            [
                f"连续失败 {consecutive_failures} 次，已保留上次有效课程。",
                f"{type(error).__name__}: {error}",
            ]
        ),
        include_actions=False,
    )


def notify_run_recovery(previous_failures: int, record_count: int) -> None:
    _send_notification(
        subject="SlopePing · 已恢复",
        body=(f"检查已在连续失败 {previous_failures} 次后恢复，当前读取到 {record_count} 节课程。"),
        include_actions=False,
    )


def _send_notification(subject: str, body: str, include_actions: bool = True) -> None:
    channel = os.getenv("NOTIFY_CHANNEL", "console").strip().casefold() or "console"

    if channel == "ntfy":
        if _send_ntfy(subject, body, include_actions=include_actions):
            print("[notify] ntfy notification sent.", flush=True)
            return
        _notify_console(subject, body)
        return

    if channel != "console":
        print(f"WARNING: Unknown NOTIFY_CHANNEL={channel!r}; falling back to console.")

    _notify_console(subject, body)


def _notify_console(subject: str, body: str) -> None:
    print(f"\nNotification: {subject}")
    print(body)


def _send_ntfy(subject: str, body: str, include_actions: bool = True) -> bool:
    server = os.getenv("NTFY_SERVER", "").strip().rstrip("/")
    topic = os.getenv("NTFY_TOPIC", "").strip()

    missing = []
    if not server:
        missing.append("NTFY_SERVER")
    if not topic:
        missing.append("NTFY_TOPIC")
    if missing:
        print(
            f"WARNING: Missing ntfy notification config: {', '.join(missing)}. Falling back to console."
        )
        return False

    headers = {
        "Title": subject,
        "Content-Type": "text/plain; charset=utf-8",
    }

    actions = []
    if include_actions:
        actions.extend(_build_control_action())
        actions.extend(_build_calendar_action())

    if actions:
        headers["Actions"] = ";".join(actions)

    request = urllib.request.Request(
        f"{server}/{topic}",
        data=body.encode("utf-8"),
        method="POST",
        headers=headers,
    )

    attempts = max(1, _int_env("NTFY_RETRY_ATTEMPTS", 3))
    base_delay = max(0.0, _float_env("NTFY_RETRY_DELAY_SECONDS", 2.0))
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=20):
                pass
            return True
        except (urllib.error.URLError, OSError) as exc:
            if attempt >= attempts:
                print(f"ERROR: ntfy notification failed after {attempts} attempt(s): {exc}")
                return False
            delay = base_delay * (2 ** (attempt - 1))
            print(
                f"[notify] ntfy attempt {attempt}/{attempts} failed: {exc}. "
                f"Retrying in {delay:.1f}s.",
                flush=True,
            )
            time.sleep(delay)

    return False


def _build_control_action() -> list[str]:
    """Build an ntfy view action that opens the safe mobile control page."""
    webhook_url = os.getenv("ACTION_WEBHOOK_BASE_URL", "").strip().rstrip("/")
    webhook_token = os.getenv("ACTION_WEBHOOK_TOKEN", "").strip()

    if not webhook_url or not webhook_token:
        return []

    try:
        url = build_access_url(
            webhook_url,
            "/control",
            webhook_token,
            "control",
            _int_env("WEBHOOK_LINK_TTL_SECONDS", 86400),
        )
    except ValueError as exc:
        print(f"WARNING: Cannot create control link: {exc}", flush=True)
        return []
    return [f"view, 打开 SlopePing, {url}"]


def _build_calendar_action() -> list[str]:
    """Build an ntfy view action that opens the mobile calendar export page."""
    webhook_url = os.getenv("ACTION_WEBHOOK_BASE_URL", "").strip().rstrip("/")
    webhook_token = os.getenv("ACTION_WEBHOOK_TOKEN", "").strip()

    if not webhook_url or not webhook_token:
        return []

    try:
        url = build_access_url(
            webhook_url,
            "/calendar",
            webhook_token,
            "calendar",
            _int_env("WEBHOOK_LINK_TTL_SECONDS", 86400),
        )
    except ValueError as exc:
        print(f"WARNING: Cannot create calendar link: {exc}", flush=True)
        return []
    return [f"view, 打开日历, {url}"]


def _notification_subject(lessons: list[Lesson]) -> str:
    pending_count = len(_pending_lessons(lessons))
    if pending_count:
        return f"SlopePing · {pending_count} 节课程待确认"
    return f"SlopePing · {len(lessons)} 节新课程"


def _pending_lessons(lessons: list[Lesson]) -> list[Lesson]:
    return [lesson for lesson in lessons if lesson.confirmation_status == "pending"]


def _format_compact_report(
    current_lessons: list[Lesson],
    new_lessons: list[Lesson],
    notable_lessons: list[Lesson],
) -> str:
    pending_count = len(_pending_lessons(current_lessons))
    action_summary = f"待确认 {pending_count} 节" if pending_count else "无需处理"
    summary = f"当前 {len(current_lessons)} 节｜新增 {len(new_lessons)} 节｜{action_summary}"
    if not notable_lessons:
        return summary
    return f"{summary}\n\n{_format_compact_lessons(notable_lessons)}"


def _format_compact_lessons(lessons: list[Lesson]) -> str:
    blocks = []
    for lesson in lessons:
        status = {
            "confirmed": "已确认",
            "pending": "待确认",
        }.get(lesson.confirmation_status, "状态未知")
        blocks.append(
            "\n".join(
                [
                    f"{lesson.tag} · {lesson.von}–{lesson.bis}",
                    f"{lesson.trainingsbezeichnung} · {lesson.raum_ort}",
                    f"状态：{status}",
                ]
            )
        )
    return "\n\n".join(blocks)


def _format_run_report(current_lessons: list[Lesson], new_lessons: list[Lesson]) -> str:
    current_text = (
        _format_lessons(current_lessons) if current_lessons else "No current lessons found."
    )
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


def _merge_lessons(first: list[Lesson], second: list[Lesson]) -> list[Lesson]:
    merged: list[Lesson] = []
    seen: set[str] = set()
    for lesson in first + second:
        if lesson.key in seen:
            continue
        seen.add(lesson.key)
        merged.append(lesson)
    return merged


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default
