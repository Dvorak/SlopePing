# Architecture Notes

Language: English | [中文](architecture.zh-CN.md) | [Deutsch](architecture.de.md)

This document describes the implementation. For day-to-day usage, see
[README.md](../README.md).

SlopePing is scoped to the Neuss Skihalle trainer scheduling workflow in the
Allrounder coach portal.

## Module Overview

- `run_checker.py`
  Entry point. Adds `src/` to `sys.path` and calls `ski_checker.checker.run()`.
- `src/ski_checker/config.py`
  Loads `.env` and builds typed settings.
- `src/ski_checker/browser.py`
  Owns Playwright startup, login, navigation, page switching, and screenshots.
- `src/ski_checker/parser.py`
  Finds the schedule table and converts table rows into lesson records.
- `src/ski_checker/state.py`
  Defines lesson records, stores `state.json`, and compares current lessons with
  the previous run.
- `src/ski_checker/notify.py`
  Sends ntfy notifications, with console fallback.

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

The normal notification path only sends new lessons. During testing,
`NOTIFY_ALWAYS_SEND_REPORT=true` sends a report on every successful run.

## ntfy Notification

The project posts plain text to:

```text
{NTFY_SERVER}/{NTFY_TOPIC}
```

The notification body includes:

- Current lessons, in test report mode
- New lessons pending confirmation
- `Tag`, `Von`, `Bis`, `Raum/Ort`, `Trainingsbezeichnung`, `Bestätigung`

If ntfy is missing configuration or sending fails, the program prints the same
message to the console and keeps running.

## Runtime Files

- `.env`
  Local secrets and user configuration. Ignored by Git.
- `state.json`
  Last successful parsed state. Ignored by Git.
- `screenshots/`
  Success and error screenshots. Ignored by Git.

## Safety Notes

- Do not commit `.env`.
- Keep `NTFY_TOPIC` long and private.
- The public `ntfy.sh` service does not protect a topic with a password by
  default.
- The script prints progress messages, but it does not print the password.
