# SlopePing

Language: English | [中文](README.zh-CN.md) | [Deutsch](README.de.md)

SlopePing watches the Neuss Skihalle schedule, sends ntfy alerts when lessons
change, and can open a phone-friendly control page for reviewed accept/decline
actions.

The project stays intentionally small: Python, Playwright, a local `.env`, a
local `state.json`, and ntfy notifications.

## Quick Start

1. Install dependencies.

  ```bash
  cd SlopePing
  python3.11 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  python -m playwright install chromium
  cp .env.example .env
  ```

2. Configure `.env`.

  ```dotenv
  SKI_USERNAME=your_username
  SKI_PASSWORD=your_password
  NOTIFY_CHANNEL=ntfy
  NTFY_SERVER=https://ntfy.sh
  NTFY_TOPIC=your-long-private-topic
  NOTIFY_ALWAYS_SEND_REPORT=true
  ACTION_WEBHOOK_TOKEN=your-generated-secure-token
  ACTION_WEBHOOK_BASE_URL=http://YOUR_LOCAL_IP:8000
  WEBHOOK_HOST=127.0.0.1
  WEBHOOK_PORT=8000
  ```

  Keep the ntfy topic private. For phone use, set `ACTION_WEBHOOK_BASE_URL`
  to your Mac's local IP, not `localhost`, and set `WEBHOOK_HOST=0.0.0.0`
  only on a trusted network.

3. Start the webhook server.

  ```bash
  source .venv/bin/activate
  python scripts/webhook_server.py
  ```

4. Run the checker.

  ```bash
  source .venv/bin/activate
  python run_checker.py
  ```

5. Test on your phone.

  Open the ntfy notification and tap `Open SlopePing`. Pending lessons require
  a second confirmation in the control page before SlopePing changes anything.
  If you need the full walkthrough, see [webhook-startup-guide.md](docs/webhook-startup-guide.md).

## What It Does

- Logs in to the Allrounder portal and opens the schedule table
- Detects confirmed, pending, and unknown lessons
- Saves screenshots and compares against `state.json`
- Sends ntfy notifications for new lessons or pending actions
- Adds an `Open SlopePing` action that opens a mobile control page
- Requires a second confirmation before remote accept/decline actions
- Can export lessons as `.ics` calendar files
- Supports `--accept` and `--decline` for explicit CLI actions

SlopePing only changes a lesson after an explicit CLI command or after you open
the mobile control page and confirm the action there.

## Requirements

- Python 3.11+
- An Allrounder coach portal account for the Neuss Skihalle trainer system
- The ntfy app on your phone, or another ntfy client

## Details

See [webhook-startup-guide.md](docs/webhook-startup-guide.md) for the phone and
webhook walkthrough.

Use the CLI actions like this:

```bash
python run_checker.py --accept "LESSON_KEY_OR_ID"
python run_checker.py --decline "LESSON_KEY_OR_ID"
```

If a lesson needs action, the notification title is `SlopePing: action needed`
and the message shows the available actions. The ntfy action opens the control
page; it does not directly accept or decline the lesson.

For safer phone access, the webhook server listens on `127.0.0.1` by default.
Use `WEBHOOK_HOST=0.0.0.0` only on a trusted local network, Tailscale, or a
secured tunnel.

## Files Created At Runtime

- `state.json`: last known lesson state
- `actions.log`: manual accept/decline action history
- `calendar_events/`: ICS calendar files created by webhook actions
- `screenshots/`: success and error screenshots

All are ignored by Git.

## Troubleshooting

- If login fails, check `SKI_USERNAME` and `SKI_PASSWORD`.
- If the page opens but no lessons are parsed, check the latest screenshot in
  `screenshots/`.
- If ntfy says sent but your phone is quiet, check the phone notification
  permission, server, and topic spelling.
- If you want to test notifications without waiting for a new lesson, set
  `NOTIFY_ALWAYS_SEND_REPORT=true`.
- If a lesson needs action, the notification title is `SlopePing: action needed`
  and the message shows the available actions.

## More Details

Implementation notes are kept separate:

- [Architecture notes, English](docs/architecture.en.md)
- [架构说明，中文](docs/architecture.zh-CN.md)
- [Architekturhinweise, Deutsch](docs/architecture.de.md)
