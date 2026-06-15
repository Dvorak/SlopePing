from __future__ import annotations

import html
import json
import os
import threading
from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response

from .actions import perform_lesson_action
from .browser import BrowserSession
from .config import load_settings
from .ics_generator import build_ics_bytes, build_ics_filename, create_ics_event
from .parser import parse_overview_records
from .state import ScheduleRecord, load_records, save_records


app = FastAPI(
    title="SlopePing Webhook",
    description="Mobile control page for SlopePing lesson actions",
    version="1.0.0",
)

_ACTION_LOCK = threading.Lock()


def _validate_token(token: str, action: str) -> None:
    expected_token = os.getenv("ACTION_WEBHOOK_TOKEN", "").strip()
    if not expected_token:
        print("[webhook] ERROR: ACTION_WEBHOOK_TOKEN is not configured.", flush=True)
        raise HTTPException(status_code=500, detail="Webhook token is not configured")

    if token != expected_token:
        print(f"[webhook] Security: invalid token attempt for action={action}.", flush=True)
        raise HTTPException(status_code=403, detail="Invalid token")


def _load_cached_records() -> tuple[list[ScheduleRecord], str | None]:
    settings = load_settings()
    records = load_records(settings.state_path)
    return records, _last_checked_at(settings.state_path)


def _last_checked_at(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(raw, dict):
        value = raw.get("last_checked_at")
        return str(value) if value else None
    return None


def _find_record(records: list[ScheduleRecord], lesson_id: str) -> ScheduleRecord | None:
    for record in records:
        if record.lesson_id == lesson_id:
            return record
    return None


def _lesson_query(lesson: ScheduleRecord, token: str, action: str | None = None) -> str:
    values = {"lesson_id": lesson.lesson_id, "token": token}
    if action:
        values["action"] = action
    return urlencode(values)


def _html_page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{html.escape(title)}</title>
    <style>
        :root {{
            color-scheme: light;
            --bg: #f7f4ee;
            --card: #ffffff;
            --ink: #17212b;
            --muted: #5f6b76;
            --accent: #0f766e;
            --danger: #b42318;
            --border: #d7dee7;
        }}
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: var(--bg); color: var(--ink); padding: 18px 14px 36px; }}
        main {{ max-width: 760px; margin: 0 auto; }}
        h1 {{ margin: 0 0 8px; font-size: 1.55rem; }}
        h2 {{ margin: 8px 0 8px; font-size: 1.08rem; }}
        p {{ line-height: 1.5; }}
        .muted, .meta, .empty {{ color: var(--muted); }}
        .lesson {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 15px; margin: 12px 0; box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04); }}
        .meta {{ font-size: 0.93rem; }}
        .status {{ display: inline-block; margin-top: 8px; padding: 4px 8px; border-radius: 6px; background: #eef6f5; color: #075e58; font-weight: 700; font-size: 0.9rem; }}
        .status.pending {{ background: #fff4d6; color: #7a4b00; }}
        .status.unknown {{ background: #eef1f4; color: #384252; }}
        .actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 13px; }}
        a.button, button {{ display: inline-flex; align-items: center; justify-content: center; min-height: 42px; padding: 10px 14px; border-radius: 7px; border: 0; text-decoration: none; font-weight: 700; font-size: 0.96rem; cursor: pointer; }}
        a.primary, button.primary {{ background: var(--accent); color: white; }}
        a.secondary {{ background: #e8edf2; color: var(--ink); }}
        a.danger, button.danger {{ background: var(--danger); color: white; }}
        .warning {{ border-left: 4px solid #d97706; padding: 10px 12px; background: #fff8e8; border-radius: 6px; }}
        .success {{ border-left: 4px solid var(--accent); padding: 10px 12px; background: #edf8f6; border-radius: 6px; }}
        dl {{ display: grid; grid-template-columns: max-content 1fr; gap: 8px 12px; }}
        dt {{ color: var(--muted); }}
        dd {{ margin: 0; }}
    </style>
</head>
<body>
    <main>{body}</main>
</body>
</html>"""


def _render_lesson_details(lesson: ScheduleRecord) -> str:
    actions = ", ".join(lesson.available_actions or []) or "-"
    fields = [
        ("Tag", lesson.tag),
        ("Von", lesson.von),
        ("Bis", lesson.bis),
        ("Raum/Ort", lesson.raum_ort),
        ("Training", lesson.trainingsbezeichnung),
        ("Bestätigung", lesson.bestaetigung or "-"),
        ("Status", lesson.confirmation_status),
        ("Actions", actions),
    ]
    return "<dl>" + "".join(
        f"<dt>{html.escape(label)}</dt><dd>{html.escape(value)}</dd>" for label, value in fields
    ) + "</dl>"


def _render_control_page(records: list[ScheduleRecord], token: str, last_checked_at: str | None) -> str:
    lesson_cards = []
    for record in records:
        status_class = record.confirmation_status if record.confirmation_status in {"pending", "unknown"} else ""
        details = _render_lesson_details(record)
        calendar_url = f"/calendar/ics?{_lesson_query(record, token)}"
        action_html = [
            f'<a class="button secondary" href="{html.escape(calendar_url)}">Add to calendar</a>'
        ]

        if record.confirmation_status == "pending":
            accept_url = f"/actions/confirm?{_lesson_query(record, token, 'accept')}"
            decline_url = f"/actions/confirm?{_lesson_query(record, token, 'decline')}"
            action_html.insert(0, f'<a class="button primary" href="{html.escape(accept_url)}">Review accept</a>')
            action_html.insert(1, f'<a class="button danger" href="{html.escape(decline_url)}">Review decline</a>')

        lesson_cards.append(
            f"""
            <article class="lesson">
                <div class="meta">{html.escape(record.tag)} · {html.escape(record.von)} - {html.escape(record.bis)}</div>
                <h2>{html.escape(record.trainingsbezeichnung)}</h2>
                <span class="status {html.escape(status_class)}">{html.escape(record.confirmation_status)}</span>
                {details}
                <div class="actions">{''.join(action_html)}</div>
            </article>
            """.strip()
        )

    lessons_html = "\n".join(lesson_cards) if lesson_cards else "<p class='empty'>No cached lessons found. Run python run_checker.py first.</p>"
    checked_text = html.escape(last_checked_at or "unknown")
    body = f"""
        <h1>SlopePing Control</h1>
        <p class="muted">This page uses the last saved schedule from state.json. Last checked: {checked_text}.</p>
        <p class="muted">Accept or decline actions require a second confirmation and then re-check the live Allrounder page before saving.</p>
        {lessons_html}
    """
    return _html_page("SlopePing Control", body)


def _render_calendar_page(records: list[ScheduleRecord], token: str, last_checked_at: str | None) -> str:
    lesson_cards = []
    for record in records:
        calendar_url = f"/calendar/ics?{_lesson_query(record, token)}"
        lesson_cards.append(
            f"""
            <article class="lesson">
                <div class="meta">{html.escape(record.tag)} · {html.escape(record.von)} - {html.escape(record.bis)}</div>
                <h2>{html.escape(record.trainingsbezeichnung)}</h2>
                <div class="meta">{html.escape(record.raum_ort)}</div>
                <div class="actions">
                    <a class="button primary" href="{html.escape(calendar_url)}">Add to calendar</a>
                </div>
            </article>
            """.strip()
        )

    lessons_html = "\n".join(lesson_cards) if lesson_cards else "<p class='empty'>No cached lessons found. Run python run_checker.py first.</p>"
    checked_text = html.escape(last_checked_at or "unknown")
    body = f"""
        <h1>SlopePing Calendar Export</h1>
        <p class="muted">These calendar files are generated from the last saved schedule in state.json. Last checked: {checked_text}.</p>
        {lessons_html}
    """
    return _html_page("SlopePing Calendar Export", body)


def _render_confirmation_page(lesson: ScheduleRecord, action: str, token: str) -> str:
    if action not in {"accept", "decline"}:
        raise HTTPException(status_code=400, detail="Unknown action")

    if lesson.confirmation_status != "pending":
        body = f"""
            <h1>Action unavailable</h1>
            <p class="warning">This lesson is currently <strong>{html.escape(lesson.confirmation_status)}</strong>, so SlopePing will not change it.</p>
            <article class="lesson">{_render_lesson_details(lesson)}</article>
        """
        return _html_page("Action unavailable", body)

    label = "Bestätigen" if action == "accept" else "Absagen"
    button_class = "primary" if action == "accept" else "danger"
    execute_url = f"/actions/execute?{_lesson_query(lesson, token, action)}"
    body = f"""
        <h1>Confirm {html.escape(action)}</h1>
        <p class="warning">This will log in to Allrounder, choose <strong>{html.escape(label)}</strong>, and click <strong>Speichern</strong>.</p>
        <article class="lesson">{_render_lesson_details(lesson)}</article>
        <form method="post" action="{html.escape(execute_url)}">
            <button class="{button_class}" type="submit">Yes, {html.escape(label)}</button>
        </form>
        <p><a class="button secondary" href="/control?{html.escape(urlencode({'token': token}))}">Back</a></p>
    """
    return _html_page(f"Confirm {action}", body)


def _render_result_page(result: dict) -> str:
    message = str(result.get("message", "Action finished."))
    status = str(result.get("status", "unknown"))
    lesson_id = str(result.get("lesson_id", ""))
    body = f"""
        <h1>Action result</h1>
        <p class="success"><strong>{html.escape(status)}</strong>: {html.escape(message)}</p>
        <p class="muted">lesson_id: {html.escape(lesson_id)}</p>
    """
    return _html_page("Action result", body)


@app.get("/control", response_class=HTMLResponse)
def control_page(token: str) -> HTMLResponse:
    _validate_token(token, "control")
    print("[webhook] Control page requested; using cached state.", flush=True)
    records, last_checked_at = _load_cached_records()
    return HTMLResponse(content=_render_control_page(records, token, last_checked_at))


@app.get("/actions/confirm", response_class=HTMLResponse)
def confirm_action(lesson_id: str, action: str, token: str) -> HTMLResponse:
    _validate_token(token, "confirm")
    print(f"[webhook] Confirmation page requested for action={action}; using cached state.", flush=True)
    records, _ = _load_cached_records()
    lesson = _find_record(records, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return HTMLResponse(content=_render_confirmation_page(lesson, action, token))


@app.post("/actions/execute", response_class=HTMLResponse)
def execute_action(lesson_id: str, action: str, token: str) -> HTMLResponse:
    result = _handle_action(action, lesson_id, token)
    return HTMLResponse(content=_render_result_page(result))


@app.post("/actions/accept")
def accept_lesson(lesson_id: str, token: str) -> dict:
    _validate_token(token, "accept")
    return {
        "status": "blocked",
        "message": "Direct remote actions are disabled. Open /control and confirm the action there.",
        "lesson_id": lesson_id,
    }


@app.post("/actions/decline")
def decline_lesson(lesson_id: str, token: str) -> dict:
    _validate_token(token, "decline")
    return {
        "status": "blocked",
        "message": "Direct remote actions are disabled. Open /control and confirm the action there.",
        "lesson_id": lesson_id,
    }


def _handle_action(action: str, lesson_id: str, token: str) -> dict:
    _validate_token(token, action)
    if action not in {"accept", "decline"}:
        raise HTTPException(status_code=400, detail="Unknown action")

    if not _ACTION_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="SlopePing is already processing an action")

    print(f"[webhook] Processing {action.upper()} action for lesson_id={lesson_id}.", flush=True)
    try:
        settings = load_settings()
        with BrowserSession(settings) as browser:
            page = browser.login_and_open_schedule()
            success = perform_lesson_action(page, settings, action, lesson_id)
            if not success:
                raise HTTPException(
                    status_code=400,
                    detail=f"Action {action} failed. Check actions.log for details.",
                )

            records = parse_overview_records(page, settings.selectors)
            matching_lesson = _find_record(records, lesson_id)
            result = {
                "status": "success",
                "action": action,
                "lesson_id": lesson_id,
                "message": f"Successfully {action}ed lesson",
            }
            if matching_lesson:
                ics_path = create_ics_event(matching_lesson, action)
                result["ics_file"] = str(ics_path)
            save_records(settings.state_path, records)
            return result
    except HTTPException:
        raise
    except Exception as exc:
        print(f"[webhook] ERROR: {exc}", flush=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {exc}")
    finally:
        _ACTION_LOCK.release()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "SlopePing Webhook"}


@app.get("/calendar", response_class=HTMLResponse)
def calendar_page(token: str) -> HTMLResponse:
    _validate_token(token, "calendar")
    print("[webhook] Calendar page requested; using cached state.", flush=True)
    records, last_checked_at = _load_cached_records()
    return HTMLResponse(content=_render_calendar_page(records, token, last_checked_at))


@app.get("/calendar/ics")
def calendar_export(lesson_id: str, token: str) -> Response:
    _validate_token(token, "calendar_export")
    print(f"[webhook] ICS export requested for lesson_id={lesson_id}; using cached state.", flush=True)
    records, _ = _load_cached_records()
    matching_lesson = _find_record(records, lesson_id)
    if matching_lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")

    ics_bytes = build_ics_bytes(matching_lesson)
    filename = build_ics_filename(matching_lesson)
    return Response(
        content=ics_bytes,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
