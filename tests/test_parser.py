import pytest
from playwright.sync_api import Page

from slopeping.config import Selectors
from slopeping.parser import ParseError, _confirmation_details, parse_overview_records

from .conftest import load_html_fixture


def test_parse_normal_overview(page: Page) -> None:
    load_html_fixture(page, "overview-normal.html")

    records = parse_overview_records(page, Selectors())

    assert len(records) == 3
    assert records[0].confirmation_status == "confirmed"
    assert records[0].available_actions == []
    assert records[1].confirmation_status == "pending"
    assert records[1].available_actions == ["Bitte wählen", "Bestätigen", "Absagen"]
    assert records[2].confirmation_status == "unknown"


def test_parse_reordered_columns_and_normalize_whitespace(page: Page) -> None:
    load_html_fixture(page, "overview-reordered.html")

    [record] = parse_overview_records(page, Selectors())

    assert record.tag == "Sa, 01.08.2026"
    assert record.von == "10:45"
    assert record.bis == "12:15"
    assert record.raum_ort == "Anfängerhügel"
    assert record.trainingsbezeichnung == "Fördertraining Anfänger"
    assert record.confirmation_status == "confirmed"


def test_parse_empty_overview(page: Page) -> None:
    load_html_fixture(page, "overview-empty.html")

    assert parse_overview_records(page, Selectors()) == []


def test_missing_required_headers_fail_closed(page: Page) -> None:
    load_html_fixture(page, "overview-missing-header.html")

    with pytest.raises(ParseError, match="Could not find"):
        parse_overview_records(page, Selectors())


def test_incomplete_data_row_fails_closed(page: Page) -> None:
    page.set_content(
        """
        <table id="TAB">
          <thead><tr>
            <th>Tag</th><th>Von</th><th>Bis</th><th>Raum/Ort</th>
            <th>Trainingsbezeichnung</th><th>Bestätigung</th>
          </tr></thead>
          <tbody><tr>
            <td>30.07.2026</td><td>09:00</td><td></td><td>Skihalle</td>
            <td>Gruppenkurs</td><td>Bestätigt</td>
          </tr></tbody>
        </table>
        """
    )

    with pytest.raises(ParseError, match="missing required values: bis"):
        parse_overview_records(page, Selectors())


@pytest.mark.parametrize("text", ["Bestätigt", "Bestaetigt", "  BESTÄTIGT  "])
def test_confirmation_text_is_recognized_without_select(text: str) -> None:
    assert _confirmation_details(text, None) == ("confirmed", [])


def test_unknown_confirmation_text_stays_unknown() -> None:
    assert _confirmation_details("In Bearbeitung", None) == ("unknown", [])
