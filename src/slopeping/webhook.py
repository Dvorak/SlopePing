from __future__ import annotations

import hmac
import json
import os
import threading
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from .actions import perform_lesson_action
from .browser import BrowserSession
from .config import load_settings
from .execution_lock import LockUnavailableError, execution_lock
from .ics_generator import build_ics_bytes, build_ics_filename, create_ics_event
from .parser import parse_overview_records
from .replay import ReplayDetectedError, consume_nonce
from .security import InvalidTokenError, TokenClaims, issue_token, verify_token
from .state import ScheduleRecord, load_records, save_records
from .web_views import (
    render_calendar_page,
    render_confirmation_page,
    render_control_page,
    render_result_page,
)

app = FastAPI(
    title="SlopePing Webhook",
    description="Mobile control page for SlopePing lesson actions",
    version="1.0.0",
)

_ACTION_LOCK = threading.Lock()
_TOKEN_SCOPES = {
    "control": {"control"},
    "confirm": {"control"},
    "accept": {"control"},
    "decline": {"control"},
    "calendar": {"calendar", "control"},
    "calendar_export": {"calendar", "control"},
    "execute": {"execute"},
}


@app.middleware("http")
async def add_security_headers(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; style-src 'unsafe-inline'; "
        "form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
    )
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


def _webhook_secret() -> str:
    secret = os.getenv("ACTION_WEBHOOK_TOKEN", "").strip()
    if not secret:
        print("[webhook] ERROR: ACTION_WEBHOOK_TOKEN is not configured.", flush=True)
        raise HTTPException(status_code=500, detail="Webhook token is not configured")
    return secret


def _validate_token(token: str, action: str) -> TokenClaims:
    secret = _webhook_secret()
    allowed_scopes = _TOKEN_SCOPES.get(action, set())
    try:
        return verify_token(secret, token, allowed_scopes)
    except (InvalidTokenError, ValueError):
        if (
            action != "execute"
            and _bool_env("WEBHOOK_ALLOW_LEGACY_TOKEN", False)
            and hmac.compare_digest(token, secret)
        ):
            return TokenClaims(scope="legacy", expires_at=0, nonce="", values={})
        print(
            f"[webhook] Security: invalid token attempt for action={action}.",
            flush=True,
        )
        raise HTTPException(status_code=403, detail="Invalid or expired access token") from None


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


def _find_record(
    records: list[ScheduleRecord],
    lesson_id: str,
) -> ScheduleRecord | None:
    for record in records:
        if record.lesson_id == lesson_id:
            return record
    return None


@app.get("/control", response_class=HTMLResponse)
def control_page(token: str) -> HTMLResponse:
    _validate_token(token, "control")
    print("[webhook] Control page requested; using cached state.", flush=True)
    records, last_checked_at = _load_cached_records()
    return HTMLResponse(content=render_control_page(records, token, last_checked_at))


@app.get("/actions/confirm", response_class=HTMLResponse)
def confirm_action(lesson_id: str, action: str, token: str) -> HTMLResponse:
    _validate_token(token, "confirm")
    if action not in {"accept", "decline"}:
        raise HTTPException(status_code=400, detail="Unknown action")

    print(
        f"[webhook] Confirmation page requested for action={action}; using cached state.",
        flush=True,
    )
    records, _ = _load_cached_records()
    lesson = _find_record(records, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    execute_token = issue_token(
        _webhook_secret(),
        "execute",
        _int_env("WEBHOOK_ACTION_TTL_SECONDS", 600),
        values={"action": action, "lesson_id": lesson_id},
    )
    return HTMLResponse(
        content=render_confirmation_page(
            lesson,
            action,
            token,
            execute_token,
        )
    )


@app.post("/actions/execute", response_class=HTMLResponse)
def execute_action(lesson_id: str, action: str, token: str) -> HTMLResponse:
    result = _handle_action(action, lesson_id, token)
    return HTMLResponse(content=render_result_page(result))


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
    claims = _validate_token(token, "execute")
    if action not in {"accept", "decline"}:
        raise HTTPException(status_code=400, detail="Unknown action")
    if claims.values.get("action") != action or claims.values.get("lesson_id") != lesson_id:
        raise HTTPException(
            status_code=403,
            detail="Action token does not match this lesson and action",
        )

    if not _ACTION_LOCK.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="SlopePing is already processing an action",
        )

    print(
        f"[webhook] Processing {action.upper()} action for lesson_id={lesson_id}.",
        flush=True,
    )
    try:
        settings = load_settings()
        with execution_lock(settings.lock_path, f"webhook-{action}"):
            consume_nonce(
                settings.used_nonces_path,
                claims.nonce,
                claims.expires_at,
            )
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
                    ics_path = create_ics_event(
                        matching_lesson,
                        action,
                        settings.calendar_dir,
                    )
                    result["ics_file"] = str(ics_path)
                save_records(settings.state_path, records)
                return result
    except (LockUnavailableError, ReplayDetectedError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        print(f"[webhook] ERROR: {exc}", flush=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {exc}",
        ) from exc
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
    return HTMLResponse(content=render_calendar_page(records, token, last_checked_at))


@app.get("/calendar/ics")
def calendar_export(lesson_id: str, token: str) -> Response:
    _validate_token(token, "calendar_export")
    print(
        f"[webhook] ICS export requested for lesson_id={lesson_id}; using cached state.",
        flush=True,
    )
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


def _int_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on"}
