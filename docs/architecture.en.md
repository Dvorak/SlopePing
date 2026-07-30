# Architecture Notes

Language: English | [中文](architecture.zh-CN.md) | [Deutsch](architecture.de.md)

This document describes the implementation. For day-to-day usage, see
[README.md](../README.md).

SlopePing is scoped to the Neuss Skihalle trainer scheduling workflow in the
Allrounder coach portal.

## Module Overview

- `run_checker.py`
  Compatibility entry point. Adds `src/` to `sys.path` and calls
  `slopeping.cli.main()`.
- `scripts/webhook_server.py`
  Compatibility entry point for `slopeping.server.main()`.
- `src/slopeping/cli.py`
  Defines checker CLI arguments and dispatches actions to `slopeping.checker.run()`.
- `src/slopeping/server.py`
  Loads and validates webhook server settings, then starts Uvicorn.
- `src/slopeping/config.py`
  Loads `.env`, typed settings, and centralized `var/` runtime paths.
- `src/slopeping/browser.py`
  Owns Playwright startup, login, navigation, page switching, and screenshots.
- `src/slopeping/parser.py`
  Finds the schedule table and converts table rows into lesson records.
- `src/slopeping/state.py`
  Defines lesson records, stores `var/state.json` with a backup, and compares
  current lessons with the previous run.
- `src/slopeping/notify.py`
  Sends ntfy notifications, with console fallback.
- `src/slopeping/webhook.py`
  Defines FastAPI routes and coordinates cached state, calendar export, and
  reviewed remote actions.
- `src/slopeping/web_views.py`
  Renders the control, confirmation, result, and calendar HTML pages.
- `src/slopeping/execution_lock.py`
  Provides one cross-process browser lock for checker, CLI, and webhook work.
- `src/slopeping/health.py` and `src/slopeping/retry.py`
  Persist run health and retry only recoverable transient errors.
- `src/slopeping/maintenance.py`
  Prunes old screenshots and calendars and rotates oversized logs.
- `src/slopeping/security.py` and `src/slopeping/replay.py`
  Issue short-lived HMAC tokens and prevent final action form replay.
- `src/slopeping/runtime_migration.py`
  Safely migrates legacy root runtime data into `var/`.
- `src/slopeping/ui_preview.py`
  Uses anonymous lessons with the same page templates to generate offline HTML
  and mobile screenshots without accessing the portal.
- `scripts/generate_ui_previews.py`
  Development and documentation entry point for UI previews; it is not a
  production service.
- `src/slopeping/ics_generator.py`
  Builds Europe/Berlin `.ics` calendar events for lessons.

The only canonical runtime entry points are `run_checker.py` and
`scripts/webhook_server.py`. The `scripts/run_checker.sh` and
`scripts/run_webhook_server.sh` files only wrap them for launchd.

## Runtime Flow

1. Load settings from `.env`.
2. Start Playwright Chromium.
3. Open the login page.
4. Fill username and password.
5. Click `Anmelden`.
6. Open `Meine Daten` -> `Arbeitsplan/Verfügbarkeit`.
7. Detect the new schedule page/tab and switch to it.
8. Wait for `table#TAB` or the `Übersicht` text.
9. Parse lessons.
10. Save a screenshot.
11. Load previous records from `var/state.json`.
12. Compare current records with previous records.
13. Notify through ntfy when needed.
14. Save current records to `var/state.json` and retain the previous backup.

When `--accept` or `--decline` is passed, SlopePing runs an action flow instead
of the normal notify-and-save flow:

1. Login and open the schedule page.
2. Parse the table rows and their matching DOM rows.
3. Match the requested lesson by `lesson_id`, full hash key, or hash prefix.
4. Refuse to act unless the lesson is `pending`.
5. Select `Bestätigen` or `Absagen`.
6. Click `Speichern`.
7. Save before/after screenshots.
8. Append a JSON line to `var/actions.log`.

## Schedule Parsing

The preferred selector is:

```text
table#TAB
```

The parser expects these columns:

- `Tag`
- `Von`
- `Bis`
- `Raum/Ort`
- `Trainingsbezeichnung`
- `Bestätigung`

Each parsed lesson also carries:

- `confirmation_status`: `confirmed`, `pending`, or `unknown`
- `available_actions`: actions read from the row dropdown

Status detection rules:

- `confirmed`: the confirmation cell text contains `Bestätigt`
- `pending`: the confirmation cell contains a `select` with `Bestätigen` and
  `Absagen`
- `unknown`: neither rule matches

If `table#TAB` is not visible, the parser tries to find a table near
`Übersicht`, then falls back to scanning tables by header names.

## Change Detection

Each lesson has a stable key built from:

```text
Tag + Von + Bis + Raum/Ort + Trainingsbezeichnung
```

If a key did not exist in `var/state.json`, the lesson is treated as new.

If the key exists but the full record changed, for example `Bestätigung`
changed, it is treated as changed.

The normal notification path sends new lessons and pending lessons that need
action. During testing, `NOTIFY_ALWAYS_SEND_REPORT=true` sends a report on
every successful run.

If any notified lesson is pending, the notification title is:

```text
SlopePing: action needed
```

SlopePing does not automatically choose `Bestätigen` or `Absagen`, and it does
not click `Speichern`.

During a normal run, pending lessons are printed with copy-ready commands:

```bash
python run_checker.py --accept "LESSON_ID"
python run_checker.py --decline "LESSON_ID"
```

## Mobile Control Flow

If `ACTION_WEBHOOK_BASE_URL` and `ACTION_WEBHOOK_TOKEN` are configured, ntfy
adds HMAC-signed links that expire after 24 hours by default:

- `Open SlopePing`: opens `/control?token=...`
- `Open calendar page`: opens `/calendar?token=...`

The notification does not execute accept or decline actions directly. The
control and calendar pages read the last saved `var/state.json` snapshot, so opening
them does not start Playwright. `/actions/execute` then logs in, re-checks the
live Allrounder page, and saves only after the second confirmation.

The confirmation page issues a 10-minute execution token bound to the lesson and
action. Its nonce is persisted before execution, so the same form cannot be
submitted twice. Every browser entry point shares a cross-process lock.

## Reliability Guards

- A first empty result after a non-empty state preserves the old state; a second
  structurally valid empty table confirms it.
- Data rows missing date, time, location, or lesson name fail parsing closed.
- Normal checks retry only transient Playwright/network errors; actions never
  retry automatically.
- `var/health.json` records timing, lesson count, consecutive failures, and errors.
- First failure, configured threshold, and recovery produce status notifications.
- Screenshots and calendars have bounded retention; oversized logs rotate.

## ntfy Notification

The project posts plain text to:

```text
{NTFY_SERVER}/{NTFY_TOPIC}
```

The notification body includes:

- Current lessons, in test report mode
- New lessons pending confirmation
- `Tag`, `Von`, `Bis`, `Raum/Ort`, `Trainingsbezeichnung`, `Bestätigung`
- `confirmation_status`
- `available_actions`

If ntfy is missing configuration or sending fails, the program prints the same
message to the console and keeps running.

## Quality Baseline

- `tests/fixtures/` contains anonymized schedule HTML with no real account data.
- Parser fixture tests run in local headless Chromium without accessing Allrounder.
- Action safety tests cover non-pending, unavailable, and direct remote actions.
- `./scripts/check.sh` runs Ruff formatting, Ruff lint, mypy, and pytest.
- `.github/workflows/ci.yml` runs the same checks on Python 3.11.
- Runtime and development direct dependencies are pinned.

## Runtime Files

- `.env`
  Local secrets and user configuration. Ignored by Git.
- `var/state.json` and `var/state.json.bak`
  Last successful parsed state and its previous backup. Ignored by Git.
- `var/screenshots/`
  Success and error screenshots. Ignored by Git.
- `var/actions.log`
  JSON-line history for CLI and webhook actions. Ignored by Git.
- `var/calendar_events/`
  Generated `.ics` files for accepted or declined webhook actions. Ignored by
  Git.
- `var/health.json`
  Latest run and consecutive anomaly state. Ignored by Git.
- `var/logs/`
  Checker, webhook, and launchd logs. Ignored by Git.

## Safety Notes

- Do not commit `.env`.
- Keep `NTFY_TOPIC` long and private.
- The public `ntfy.sh` service does not protect a topic with a password by
  default.
- The script prints progress messages, but it does not print the password.
- The webhook server listens on `127.0.0.1` by default. Use `0.0.0.0` only on a
  trusted network or behind a secured tunnel.
- URLs contain only short-lived signed tokens; the long-term secret remains in `.env`.
- Short-lived tokens are still credentials. Public access still requires HTTPS
  and an additional authentication layer.
