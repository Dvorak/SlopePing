from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

MINIMUM_SECRET_LENGTH = 32


class InvalidTokenError(ValueError):
    """Raised when a signed access token is invalid, expired, or unauthorized."""


@dataclass(frozen=True)
class TokenClaims:
    scope: str
    expires_at: int
    nonce: str
    values: dict[str, Any]


def validate_webhook_secret(secret: str) -> None:
    if len(secret) < MINIMUM_SECRET_LENGTH:
        raise ValueError(
            f"ACTION_WEBHOOK_TOKEN must contain at least {MINIMUM_SECRET_LENGTH} characters"
        )


def issue_token(
    secret: str,
    scope: str,
    ttl_seconds: int,
    *,
    values: dict[str, str] | None = None,
    now: int | None = None,
    nonce: str | None = None,
) -> str:
    validate_webhook_secret(secret)
    issued_at = int(time.time()) if now is None else now
    payload: dict[str, Any] = {
        "scope": scope,
        "iat": issued_at,
        "exp": issued_at + max(1, ttl_seconds),
        "nonce": nonce or secrets.token_urlsafe(18),
    }
    if values:
        overlap = payload.keys() & values.keys()
        if overlap:
            raise ValueError(f"Token values may not replace reserved claims: {sorted(overlap)}")
        payload.update(values)

    encoded_payload = _encode(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode(
            "utf-8"
        )
    )
    signature = _sign(secret, encoded_payload)
    return f"{encoded_payload}.{_encode(signature)}"


def verify_token(
    secret: str,
    token: str,
    allowed_scopes: set[str],
    *,
    now: int | None = None,
) -> TokenClaims:
    validate_webhook_secret(secret)
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        supplied_signature = _decode(encoded_signature)
    except (ValueError, UnicodeError) as exc:
        raise InvalidTokenError("Malformed access token") from exc

    expected_signature = _sign(secret, encoded_payload)
    if not hmac.compare_digest(supplied_signature, expected_signature):
        raise InvalidTokenError("Invalid access token signature")

    try:
        raw = json.loads(_decode(encoded_payload).decode("utf-8"))
    except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise InvalidTokenError("Invalid access token payload") from exc
    if not isinstance(raw, dict):
        raise InvalidTokenError("Invalid access token payload")

    scope = raw.get("scope")
    expires_at = raw.get("exp")
    nonce = raw.get("nonce")
    if not isinstance(scope, str) or scope not in allowed_scopes:
        raise InvalidTokenError("Access token scope is not allowed")
    if not isinstance(expires_at, int) or isinstance(expires_at, bool):
        raise InvalidTokenError("Access token expiry is invalid")
    if not isinstance(nonce, str) or not nonce:
        raise InvalidTokenError("Access token nonce is invalid")

    current_time = int(time.time()) if now is None else now
    if expires_at <= current_time:
        raise InvalidTokenError("Access token has expired")

    return TokenClaims(
        scope=scope,
        expires_at=expires_at,
        nonce=nonce,
        values=raw,
    )


def build_access_url(
    base_url: str,
    path: str,
    secret: str,
    scope: str,
    ttl_seconds: int,
) -> str:
    token = issue_token(secret, scope, ttl_seconds)
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}?{urlencode({'token': token})}"


def _sign(secret: str, encoded_payload: str) -> bytes:
    return hmac.new(
        secret.encode("utf-8"),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).digest()


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
