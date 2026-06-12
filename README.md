# SlopePing

Language: English | [中文](README.zh-CN.md) | [Deutsch](README.de.md)

SlopePing is a small schedule watcher designed for Neuss Skihalle trainers. It
logs in to the Allrounder coach portal, opens the `Arbeitsplan/Verfügbarkeit`
page, reads the `Übersicht` schedule table, and sends a phone notification
through ntfy when new lessons appear.

The first version is intentionally simple: Python, Playwright, local `.env`
configuration, local `state.json`, and ntfy notifications.

## What It Does

- Opens `https://allrounder-jobs.de/login`
- Logs in with `SKI_USERNAME` and `SKI_PASSWORD`
- Opens `Meine Daten` -> `Arbeitsplan/Verfügbarkeit`
- Switches to the schedule page at `https://anmeldung.allrounder.de/do`
- Parses the schedule table with these fields:
  `Tag`, `Von`, `Bis`, `Raum/Ort`, `Trainingsbezeichnung`, `Bestätigung`
- Saves a screenshot after each successful check
- Compares current lessons with `state.json`
- Sends ntfy notifications for new lessons
- Can send a report on every run while testing

## Requirements

- Python 3.11+
- An Allrounder coach portal account for the Neuss Skihalle trainer system
- The ntfy app on your phone, or another ntfy client

## Setup

```bash
cd SlopePing
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env
```

## Configure `.env`

Edit:

```bash
nano .env
```

Set your login details:

```dotenv
SKI_USERNAME=your_username
SKI_PASSWORD=your_password
```

Set ntfy:

```dotenv
NOTIFY_CHANNEL=ntfy
NTFY_SERVER=https://ntfy.sh
NTFY_TOPIC=your-long-private-topic
```

Use the same `NTFY_SERVER` and `NTFY_TOPIC` in the ntfy iOS/Android app. Keep
the topic private; anyone who knows it can subscribe.

For testing, send a notification on every successful run:

```dotenv
NOTIFY_ALWAYS_SEND_REPORT=true
```

For normal use, notify only when new lessons appear:

```dotenv
NOTIFY_ALWAYS_SEND_REPORT=false
```

## Run

```bash
cd SlopePing
source .venv/bin/activate
python run_checker.py
```

The terminal prints each step, including login, navigation, parsing, screenshot
saving, comparison, and notification status.

## Files Created At Runtime

- `state.json`: last known lesson state
- `screenshots/`: success and error screenshots

Both are ignored by Git.

## Troubleshooting

- If login fails, check `SKI_USERNAME` and `SKI_PASSWORD`.
- If the page opens but no lessons are parsed, check the latest screenshot in
  `screenshots/`.
- If ntfy says sent but your phone is quiet, check the phone notification
  permission, server, and topic spelling.
- If you want to test notifications without waiting for a new lesson, set
  `NOTIFY_ALWAYS_SEND_REPORT=true`.

## More Details

Implementation notes are kept separate:

- [Architecture notes, English](docs/architecture.en.md)
- [架构说明，中文](docs/architecture.zh-CN.md)
- [Architekturhinweise, Deutsch](docs/architecture.de.md)
