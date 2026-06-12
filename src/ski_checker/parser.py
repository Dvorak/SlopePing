from __future__ import annotations

import re

from playwright.sync_api import Locator, Page, TimeoutError as PlaywrightTimeoutError

from .config import Selectors
from .state import ScheduleRecord


EXPECTED_HEADERS = {
    "tag": {"tag"},
    "von": {"von"},
    "bis": {"bis"},
    "raum_ort": {"raum/ort", "raum", "ort"},
    "trainingsbezeichnung": {"trainingsbezeichnung", "training", "kurs", "kursbezeichnung"},
    "bestaetigung": {"bestätigung", "bestaetigung", "bestatigung", "status"},
}


class ParseError(RuntimeError):
    pass


def parse_overview_records(page: Page, selectors: Selectors) -> list[ScheduleRecord]:
    print("[parser] Locating Übersicht schedule table.", flush=True)
    table = _find_overview_table(page, selectors)
    try:
        headers = _extract_headers(table)
    except ParseError:
        print("[parser] First table candidate did not match headers; searching all tables.", flush=True)
        table = _find_table_by_headers(page)
        headers = _extract_headers(table)
    print(f"[parser] Header mapping: {headers}", flush=True)
    rows = table.locator("tbody tr")
    if rows.count() == 0:
        rows = table.locator("tr")
    print(f"[parser] Found {rows.count()} table row(s), including header rows.", flush=True)

    records: list[ScheduleRecord] = []
    for index in range(rows.count()):
        row = rows.nth(index)
        cells = _cell_texts(row)
        if not cells or _looks_like_header(cells):
            continue
        record = _record_from_cells(headers, cells)
        if any(record.__dict__.values()):
            records.append(record)

    print(f"[parser] Parsed {len(records)} lesson record(s).", flush=True)
    return records


def _find_overview_table(page: Page, selectors: Selectors) -> Locator:
    table_by_id = page.locator("table#TAB").first
    try:
        table_by_id.wait_for(state="visible", timeout=5000)
        print("[parser] Using table#TAB.", flush=True)
        return table_by_id
    except PlaywrightTimeoutError:
        print("[parser] table#TAB not visible; trying table near Übersicht text.", flush=True)

    overview = page.get_by_text(selectors.overview_text, exact=False).first
    try:
        overview.wait_for(state="visible", timeout=10000)
        table = overview.locator(selectors.overview_table_xpath).first
        table.wait_for(state="visible", timeout=10000)
        print("[parser] Using table near Übersicht text.", flush=True)
        return table
    except PlaywrightTimeoutError:
        print("[parser] Übersicht text strategy failed; searching by headers.", flush=True)
        return _find_table_by_headers(page)


def _find_table_by_headers(page: Page) -> Locator:
    tables = page.locator("table")
    for index in range(tables.count()):
        table = tables.nth(index)
        try:
            headers = _extract_headers(table)
        except ParseError:
            continue
        if {"tag", "von", "bis", "trainingsbezeichnung"}.issubset(headers.values()):
            return table
    raise ParseError("Could not find the Übersicht schedule table.")


def _extract_headers(table: Locator) -> dict[int, str]:
    header_cells = table.locator("thead tr").first.locator("th,td")
    if header_cells.count() == 0:
        header_cells = table.locator("tr").first.locator("th,td")

    headers: dict[int, str] = {}
    for index, raw_header in enumerate(_texts(header_cells)):
        normalized = _canonical_header(raw_header)
        if normalized:
            headers[index] = normalized

    required = {"tag", "von", "bis", "raum_ort", "trainingsbezeichnung", "bestaetigung"}
    if not required.intersection(headers.values()):
        raise ParseError("The located table does not look like the Übersicht table.")
    return headers


def _record_from_cells(headers: dict[int, str], cells: list[str]) -> ScheduleRecord:
    values = {
        "tag": "",
        "von": "",
        "bis": "",
        "raum_ort": "",
        "trainingsbezeichnung": "",
        "bestaetigung": "",
    }
    for index, cell in enumerate(cells):
        field = headers.get(index)
        if field:
            values[field] = cell
    return ScheduleRecord(**values)


def _cell_texts(row: Locator) -> list[str]:
    cells = row.locator("th,td")
    return _texts(cells)


def _texts(locator: Locator) -> list[str]:
    return [_normalize_text(locator.nth(index).inner_text()) for index in range(locator.count())]


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _canonical_header(value: str) -> str | None:
    normalized = _normalize_text(value).casefold()
    for canonical, aliases in EXPECTED_HEADERS.items():
        if normalized in aliases:
            return canonical
    return None


def _looks_like_header(cells: list[str]) -> bool:
    canonical = {_canonical_header(cell) for cell in cells}
    return "tag" in canonical and ("von" in canonical or "bis" in canonical)
