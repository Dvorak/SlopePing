import pytest

from slopeping.security import InvalidTokenError, build_access_url, issue_token, verify_token

SECRET = "a-secure-test-secret-that-is-long-enough"


def test_signed_token_round_trip_with_bound_values() -> None:
    token = issue_token(
        SECRET,
        "execute",
        600,
        values={"action": "accept", "lesson_id": "lesson-1"},
        now=1000,
        nonce="nonce-1",
    )

    claims = verify_token(SECRET, token, {"execute"}, now=1200)

    assert claims.scope == "execute"
    assert claims.expires_at == 1600
    assert claims.nonce == "nonce-1"
    assert claims.values["action"] == "accept"
    assert claims.values["lesson_id"] == "lesson-1"


def test_signed_token_rejects_tampering_expiry_and_wrong_scope() -> None:
    token = issue_token(SECRET, "control", 10, now=1000, nonce="nonce-1")
    payload, signature = token.split(".")

    with pytest.raises(InvalidTokenError, match="signature"):
        verify_token(SECRET, f"{payload}x.{signature}", {"control"}, now=1001)
    with pytest.raises(InvalidTokenError, match="expired"):
        verify_token(SECRET, token, {"control"}, now=1011)
    with pytest.raises(InvalidTokenError, match="scope"):
        verify_token(SECRET, token, {"calendar"}, now=1001)


def test_access_url_contains_a_verifiable_short_lived_token() -> None:
    url = build_access_url(
        "https://example.test/base/",
        "/control",
        SECRET,
        "control",
        60,
    )

    assert url.startswith("https://example.test/base/control?token=")
