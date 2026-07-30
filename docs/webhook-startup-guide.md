# SlopePing Webhook Startup Guide

The Webhook service provides a phone-friendly view of the last saved schedule.
Opening a page never changes a lesson. Accept or decline requires a second,
short-lived confirmation and a fresh live check of Allrounder.

## 1. Configure

`.env` needs:

```dotenv
ACTION_WEBHOOK_TOKEN=generate-at-least-32-random-characters
ACTION_WEBHOOK_BASE_URL=http://YOUR_LOCAL_IP:8000
WEBHOOK_HOST=127.0.0.1
WEBHOOK_PORT=8000
```

Use `WEBHOOK_HOST=0.0.0.0` only when a phone must connect over a trusted local
network or secure tunnel. Public access requires HTTPS and an additional
authentication layer.

## 2. Start and verify

```bash
python scripts/webhook_server.py
curl http://127.0.0.1:8000/health
```

Expected health response:

```json
{"status":"ok","service":"SlopePing Webhook"}
```

For persistent macOS operation:

```bash
./scripts/install_launchd.sh
```

## 3. Open without waiting for a notification

Generate fresh signed control and calendar links:

```bash
python scripts/create_webhook_links.py
```

The command reads the long-term secret from `.env` but prints only short-lived
signed URLs. Do not build a URL with the long-term `ACTION_WEBHOOK_TOKEN`
itself.

- Notification/control links expire after 24 hours by default.
- Final action confirmations expire after 10 minutes.
- Final tokens are bound to one lesson and one action.
- A consumed action nonce cannot be submitted again.

Change lifetimes with `WEBHOOK_LINK_TTL_SECONDS` and
`WEBHOOK_ACTION_TTL_SECONDS`.

## 4. User flow

1. The checker saves the latest schedule to `var/state.json`.
2. ntfy sends `Open SlopePing` when a lesson is new or pending.
3. The control page reads only the cached state.
4. `Review accept` or `Review decline` opens a second confirmation page.
5. The final POST consumes its one-time nonce.
6. SlopePing acquires the shared browser lock, logs in, and re-reads the live row.
7. It acts only if the lesson is still pending and the requested option exists.
8. It writes `var/actions.log`, screenshots, calendar data, and the new state.

Refreshing or repeating the same final form returns HTTP 409. A simultaneous
checker or CLI action also returns a lock conflict instead of starting another
browser.

## 5. Offline UI preview

No remote course change is required:

```bash
python scripts/generate_ui_previews.py \
  --output output/ui-preview \
  --screenshots output/ui-preview/screenshots

open output/ui-preview/control.html
open output/ui-preview/confirmation.html
```

The preview uses anonymous lessons and never accesses Allrounder.

## 6. Runtime diagnostics

```bash
cat var/health.json
tail -f var/logs/webhook_server.log
tail -f var/actions.log
ls -la var/screenshots/
ls -la var/calendar_events/
```

Security responses include `Cache-Control: no-store`, a restrictive Content
Security Policy, `Referrer-Policy: no-referrer`, and anti-framing headers.

## 7. Troubleshooting

- HTTP 403: the signed link is invalid or expired; generate a fresh link.
- HTTP 409: another browser job is running, or the action form was already used.
- Empty control page: run the checker once and verify `var/state.json`.
- Action fails safely: inspect `var/actions.log` and the latest screenshot.
- Phone cannot connect: verify the phone can reach `ACTION_WEBHOOK_BASE_URL`,
  the host binding, firewall, and trusted-network route.
