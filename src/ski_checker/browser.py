from __future__ import annotations

from datetime import datetime
from pathlib import Path

from playwright.sync_api import Browser, Locator, Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

from .config import Settings


class BrowserSession:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._playwright = None
        self._browser: Browser | None = None
        self.page: Page | None = None

    def __enter__(self) -> "BrowserSession":
        print("[browser] Starting Playwright Chromium...", flush=True)
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self.settings.headless,
            slow_mo=self.settings.slow_mo_ms,
        )
        context = self._browser.new_context(viewport={"width": 1440, "height": 1000})
        context.set_default_timeout(self.settings.navigation_timeout_ms)
        context.set_default_navigation_timeout(self.settings.navigation_timeout_ms)
        self.page = context.new_page()
        print("[browser] Browser page opened.", flush=True)
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        print("[browser] Closing browser session.", flush=True)
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()

    def login_and_open_schedule(self) -> Page:
        page = self._require_page()
        selectors = self.settings.selectors

        print(f"[login] Opening login URL: {self.settings.login_url}", flush=True)
        page.goto(self.settings.login_url, wait_until="domcontentloaded")
        print(f"[login] Login page loaded: {page.url}", flush=True)

        print(f"[login] Filling username field labeled {selectors.username_label!r}.", flush=True)
        page.get_by_label(selectors.username_label).fill(self.settings.username)
        print(f"[login] Filling password field labeled {selectors.password_label!r}.", flush=True)
        page.get_by_label(selectors.password_label).fill(self.settings.password)

        print(f"[login] Clicking login button {selectors.login_button_name!r}.", flush=True)
        self._click_and_wait(page, page.get_by_role("button", name=selectors.login_button_name))
        print(f"[login] Login click completed. Current URL: {page.url}", flush=True)

        self._assert_logged_in(page)
        print("[login] Login form is no longer visible; continuing.", flush=True)
        page = self._open_schedule(page)
        self.page = page
        return page

    def save_screenshot(self, prefix: str) -> Path:
        page = self._require_page()
        self.settings.screenshots_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = self.settings.screenshots_dir / f"{prefix}-{timestamp}.png"
        page.screenshot(path=str(path), full_page=True)
        print(f"[screenshot] Saved {path}", flush=True)
        return path

    def _open_schedule(self, page: Page) -> Page:
        selectors = self.settings.selectors

        print(f"[navigation] Looking for menu group text {selectors.my_data_text!r}.", flush=True)
        my_data = page.get_by_text(selectors.my_data_text, exact=False)
        print(f"[navigation] Found {my_data.count()} {selectors.my_data_text!r} match(es).", flush=True)
        if my_data.count() > 0:
            try:
                print(f"[navigation] Clicking {selectors.my_data_text!r}.", flush=True)
                my_data.first.click(timeout=5000)
            except PlaywrightTimeoutError:
                print(f"[navigation] {selectors.my_data_text!r} was not clickable; continuing.", flush=True)

        schedule = page.get_by_text(selectors.schedule_text, exact=False)
        print(f"[navigation] Found {schedule.count()} {selectors.schedule_text!r} match(es).", flush=True)
        print(f"[navigation] Clicking {selectors.schedule_text!r}.", flush=True)
        page = self._click_schedule_and_get_page(page, schedule.first)
        self.page = page
        print(f"[navigation] Schedule click completed. Active URL: {page.url}", flush=True)

        print("[navigation] Waiting for schedule table #TAB or Übersicht text.", flush=True)
        if self._wait_for_schedule_content(page):
            print("[navigation] Schedule content is visible.", flush=True)
            return page

        print("[navigation] Schedule content was not found before timeout.", flush=True)
        print(f"[navigation] Current URL: {page.url}", flush=True)
        print(f"[navigation] Current title: {page.title()}", flush=True)
        raise PlaywrightTimeoutError("Could not find schedule content: neither table#TAB nor Übersicht became visible.")

    def _assert_logged_in(self, page: Page) -> None:
        selectors = self.settings.selectors
        username = page.get_by_label(selectors.username_label)
        password = page.get_by_label(selectors.password_label)
        login_fields_still_visible = (
            username.count() > 0
            and password.count() > 0
            and username.first.is_visible()
            and password.first.is_visible()
        )
        if login_fields_still_visible:
            raise RuntimeError("Login appears to have failed: login form is still visible.")

    def _click_and_wait(self, page: Page, locator: Locator) -> None:
        locator.click()
        try:
            print("[navigation] Waiting for network idle...", flush=True)
            page.wait_for_load_state("networkidle", timeout=10000)
        except PlaywrightTimeoutError:
            print("[navigation] Network idle timed out; waiting for DOM content loaded.", flush=True)
            page.wait_for_load_state("domcontentloaded", timeout=5000)

    def _click_schedule_and_get_page(self, page: Page, locator: Locator) -> Page:
        try:
            with page.context.expect_page(timeout=5000) as new_page_info:
                locator.click()
            schedule_page = new_page_info.value
            print("[navigation] Schedule opened a new page/tab; switching to it.", flush=True)
            self._wait_for_page_load(schedule_page)
            return schedule_page
        except PlaywrightTimeoutError:
            print("[navigation] No new page detected; using current page.", flush=True)
            self._wait_for_page_load(page)
            if page.is_closed():
                replacement = self._latest_open_page(page)
                if replacement is not None:
                    print(f"[navigation] Original page closed; switched to {replacement.url}.", flush=True)
                    return replacement
            return page

    def _wait_for_page_load(self, page: Page) -> None:
        if page.is_closed():
            return
        try:
            print("[navigation] Waiting for destination DOM content loaded.", flush=True)
            page.wait_for_load_state("domcontentloaded", timeout=self.settings.navigation_timeout_ms)
        except PlaywrightTimeoutError:
            print("[navigation] Destination DOM content wait timed out; continuing.", flush=True)
        try:
            print("[navigation] Waiting briefly for destination network idle.", flush=True)
            page.wait_for_load_state("networkidle", timeout=10000)
        except PlaywrightTimeoutError:
            print("[navigation] Destination network idle timed out; continuing.", flush=True)

    def _latest_open_page(self, page: Page) -> Page | None:
        open_pages = [candidate for candidate in page.context.pages if not candidate.is_closed()]
        if not open_pages:
            return None
        return open_pages[-1]

    def _wait_for_schedule_content(self, page: Page) -> bool:
        timeout_ms = self.settings.navigation_timeout_ms
        table = page.locator("table#TAB").first
        try:
            table.wait_for(state="visible", timeout=5000)
            return True
        except PlaywrightTimeoutError:
            pass

        overview = page.get_by_text(self.settings.selectors.overview_text, exact=False).first
        try:
            overview.wait_for(state="visible", timeout=timeout_ms)
            return True
        except PlaywrightTimeoutError:
            return False

    def _require_page(self) -> Page:
        if self.page is None:
            raise RuntimeError("Browser session is not started.")
        return self.page
