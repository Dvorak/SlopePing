import pytest

from slopeping.retry import retry_call


def test_retry_returns_after_a_transient_failure() -> None:
    calls = []
    delays = []

    def operation() -> str:
        calls.append("call")
        if len(calls) == 1:
            raise OSError("temporary")
        return "ok"

    result = retry_call(
        operation,
        attempts=3,
        delay_seconds=2,
        retry_on=(OSError,),
        label="test",
        sleep=delays.append,
    )

    assert result == "ok"
    assert len(calls) == 2
    assert delays == [2]


def test_retry_stops_after_the_configured_attempts() -> None:
    calls = []

    def operation() -> None:
        calls.append("call")
        raise OSError("still failing")

    with pytest.raises(OSError, match="still failing"):
        retry_call(
            operation,
            attempts=2,
            delay_seconds=0,
            retry_on=(OSError,),
            label="test",
            sleep=lambda delay: None,
        )

    assert len(calls) == 2


def test_retry_does_not_repeat_non_transient_errors() -> None:
    calls = []

    def operation() -> None:
        calls.append("call")
        raise ValueError("business rule")

    with pytest.raises(ValueError, match="business rule"):
        retry_call(
            operation,
            attempts=3,
            delay_seconds=0,
            retry_on=(OSError,),
            label="test",
        )

    assert len(calls) == 1
