import pytest

from slopeping.cli import main


@pytest.mark.parametrize(
    ("arguments", "expected_call"),
    [
        ([], (None, None)),
        (["--accept", "lesson-1"], ("accept", "lesson-1")),
        (["--decline", "lesson-2"], ("decline", "lesson-2")),
    ],
)
def test_cli_routes_to_checker(monkeypatch, arguments, expected_call) -> None:
    calls = []

    def fake_run(action=None, lesson_key=None) -> int:
        calls.append((action, lesson_key))
        return 7

    monkeypatch.setattr("slopeping.cli.run", fake_run)

    assert main(arguments) == 7
    assert calls == [expected_call]


def test_cli_rejects_conflicting_actions() -> None:
    with pytest.raises(SystemExit):
        main(["--accept", "one", "--decline", "two"])
