import asyncio
import html
import re

from fastapi import Request
from fastapi.responses import Response

from slopeping.security import issue_token, verify_token
from slopeping.state import ScheduleRecord
from slopeping.webhook import add_security_headers, confirm_action

SECRET = "a-secure-test-secret-that-is-long-enough"


def test_webhook_responses_include_security_headers() -> None:
    request = Request({"type": "http", "headers": []})

    async def call_next(request: Request) -> Response:
        return Response("ok")

    response = asyncio.run(add_security_headers(request, call_next))

    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_confirmation_page_issues_a_bound_short_lived_action_token(monkeypatch) -> None:
    lesson = ScheduleRecord(
        tag="Do, 30.07.2026",
        von="09:00",
        bis="11:00",
        raum_ort="Skihalle",
        trainingsbezeichnung="Gruppenkurs",
        bestaetigung="Bitte auswählen",
        confirmation_status="pending",
        available_actions=["Bestätigen", "Absagen"],
    )
    monkeypatch.setenv("ACTION_WEBHOOK_TOKEN", SECRET)
    monkeypatch.setenv("WEBHOOK_ACTION_TTL_SECONDS", "600")
    monkeypatch.setattr(
        "slopeping.webhook._load_cached_records",
        lambda: ([lesson], "2026-07-30T08:00:00+00:00"),
    )
    control_token = issue_token(SECRET, "control", 3600)

    response = confirm_action(lesson.lesson_id, "accept", control_token)
    body = html.unescape(response.body.decode("utf-8"))
    match = re.search(r"token=([^&\"]+)", body)

    assert match is not None
    claims = verify_token(SECRET, match.group(1), {"execute"})
    assert claims.values["action"] == "accept"
    assert claims.values["lesson_id"] == lesson.lesson_id
