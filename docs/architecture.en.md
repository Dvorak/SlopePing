# Architecture Notes

Language: English | [中文](architecture.zh-CN.md) | [Deutsch](architecture.de.md)

This document describes the implementation. For day-to-day usage, see
[README.md](../README.md).

SlopePing is scoped to the Neuss Skihalle trainer scheduling workflow in the
Allrounder coach portal.

## Module Overview

- `run_checker.py`
  Entry point. Adds `src/` to `sys.path` and calls `slopeping.checker.run()`.
- `scripts/webhook_server.py`
  Starts the FastAPI webhook/control-page server.
- `src/slopeping/config.py`
  Loads `.env` and builds typed settings.
- `src/slopeping/browser.py`
  Owns Playwright startup, login, navigation, page switching, and screenshots.
- `src/slopeping/parser.py`
  Finds the schedule table and converts table rows into lesson records.
- `src/slopeping/state.py`
  Defines lesson records, stores `state.json`, and compares current lessons with
  the previous run.
- `src/slopeping/notify.py`
  Sends ntfy notifications, with console fallback.
- `src/slopeping/webhook.py`
  Provides the mobile control page, calendar export, and reviewed remote
  actions.
- `src/slopeping/ics_generator.py`
  Builds Europe/Berlin `.ics` calendar events for lessons.

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
11. Load previous records from `state.json`.
12. Compare current records with previous records.
13. Notify through ntfy when needed.
14. Save the current records back to `state.json`.

When `--accept` or `--decline` is passed, SlopePing runs an action flow instead
of the normal notify-and-save flow:

1. Login and open the schedule page.
2. Parse the table rows and their matching DOM rows.
3. Match the requested lesson by `lesson_id`, full hash key, or hash prefix.
4. Refuse to act unless the lesson is `pending`.
5. Select `Bestätigen` or `Absagen`.
6. Click `Speichern`.
7. Save before/after screenshots.
8. Append a JSON line to `actions.log`.

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

If a key did not exist in `state.json`, the lesson is treated as new.

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
adds safe links:

- `Open SlopePing`: opens `/control?token=...`
- `Open calendar page`: opens `/calendar?token=...`

The notification does not execute accept or decline actions directly. The
control and calendar pages read the last saved `state.json` snapshot, so opening
them does not start Playwright. `/actions/execute` then logs in, re-checks the
live Allrounder page, and saves only after the second confirmation.

The webhook action path uses a process-local lock, so only one remote action can
run at a time.

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

## Runtime Files

- `.env`
  Local secrets and user configuration. Ignored by Git.
- `state.json`
  Last successful parsed state. Ignored by Git.
- `screenshots/`
  Success and error screenshots. Ignored by Git.
- `actions.log`
  JSON-line history for CLI and webhook actions. Ignored by Git.
- `calendar_events/`
  Generated `.ics` files for accepted or declined webhook actions. Ignored by
  Git.

## Safety Notes

- Do not commit `.env`.
- Keep `NTFY_TOPIC` long and private.
- The public `ntfy.sh` service does not protect a topic with a password by
  default.
- The script prints progress messages, but it does not print the password.
- The webhook server listens on `127.0.0.1` by default. Use `0.0.0.0` only on a
  trusted network or behind a secured tunnel.
- The webhook token is still passed in URLs, so avoid exposing the server on the
  public internet without HTTPS and stronger authentication.
