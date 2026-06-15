# SlopePing Webhook Server - Startup Guide

## What Happens When You Run: `python scripts/webhook_server.py`

### Phase 1: Startup Banner and Configuration Check

When you start the webhook server, you'll see:

```
======================================================================
  🚀 SlopePing Webhook Server
======================================================================

📋 Configuration Check:
----------------------------------------------------------------------
  ✓ ACTION_WEBHOOK_TOKEN: ******************************* (configured)
  ✓ ACTION_WEBHOOK_BASE_URL: http://192.168.1.100:8000
  ✓ WEBHOOK_HOST: 127.0.0.1
  ✓ WEBHOOK_PORT: 8000
  ✓ NTFY_TOPIC: your-private-topic (configured)
```

**What this means:**
- ✓ = Configuration is set correctly
- ⚠ = Configuration missing but not critical
- ✗ = Configuration missing and required

**Symbols explained:**
- 🚀 = Starting up
- ✓ = Success/configured
- ✗ = Error/missing
- ⚠ = Warning

### Phase 2: Server Information

```
🌐 Server Information:
----------------------------------------------------------------------
  Server: Running on 127.0.0.1:8000
  Health Check: http://localhost:8000/health
  API Docs: http://localhost:8000/docs
```

**What this means:**
- Server listens on your local machine by default
- You can test locally with `http://localhost:8000/health`
- Visit `http://localhost:8000/docs` to see interactive API documentation
- For phone access on the same trusted network, set `WEBHOOK_HOST=0.0.0.0`

### Phase 3: Phone Setup Instructions

```
📱 Testing on Your Phone:
----------------------------------------------------------------------
  1. Find your machine's local IP address:
     macOS:  ifconfig | grep 'inet '
     Linux:  hostname -I
     Windows: ipconfig | findstr IPv4

  2. Update webhook settings in .env:
     ACTION_WEBHOOK_BASE_URL=http://YOUR_IP:8000
     WEBHOOK_HOST=0.0.0.0

  3. Phone must be on the same trusted network and able to reach this URL
```

**What this means:**
- Don't use `http://localhost:8000` on phone - it won't work
- Use your computer's actual IP address (e.g., `192.168.1.100`)
- Your phone needs to be on the same WiFi network, Tailscale, or another trusted tunnel

### Phase 4: Quick Test Commands

```
🧪 Quick Test Commands:
----------------------------------------------------------------------
  # Health check
  curl http://localhost:8000/health

  # Test with invalid token (should return 403)
  curl 'http://localhost:8000/control?token=wrong'

   # Test protected control page with invalid token (should return 403)
   curl 'http://localhost:8000/control?token=wrong'
```

**What to do:**
- Run these in a new terminal to verify the server is working
- Health check should return: `{"status":"ok","service":"SlopePing Webhook"}`
- Invalid token test should return HTTP 403 error

### Phase 5: Workflow Explanation

```
📝 Understanding the Workflow:
----------------------------------------------------------------------
  1. Run: python run_checker.py
     → Checks schedule and sends ntfy notifications

  2. Pending lessons show safe links in ntfy
     → Open SlopePing (mobile control page)

  3. Open SlopePing on phone
     → Review lesson details
     → Confirm accept or decline on a second page
     → Then SlopePing logs in, finds lesson, clicks action, saves

  4. Calendar event (.ics) saved to calendar_events/
     → Action history logged to actions.log
```

**The complete flow:**
1. Checker finds pending lessons
2. Sends notification with `Open SlopePing` to your phone
3. You open the control page and review the lesson
4. You confirm accept or decline on the second page
5. Webhook receives request and validates token
6. Browser opens, logs in, performs action
7. Calendar event created for your calendar app
8. Action logged to `actions.log`

### Phase 6: Log Files to Monitor

```
📚 Log Files to Monitor:
----------------------------------------------------------------------
  • actions.log - Shows all accept/decline actions (JSON format)
  • calendar_events/ - Generated .ics files for your calendar app
  • screenshots/ - Before/after screenshots of actions
```

**How to use:**
```bash
# Watch action history in real-time
tail -f actions.log | jq '.'

# See only recent actions
tail -20 actions.log

# List generated calendar events
ls -la calendar_events/
```

### Mobile Calendar Export

You can also open a phone-friendly page that lets you download an `.ics` file
for each lesson.

1. Open `http://YOUR_IP:8000/calendar?token=YOUR_TOKEN` on your phone.
2. Tap the lesson you want.
3. Pick a calendar app when the phone asks how to open the file.

This page only exports calendar files. It does not change lesson status.

### Phase 7: Security Reminders

```
🔒 Security Reminders:
----------------------------------------------------------------------
  ⚠ Keep ACTION_WEBHOOK_TOKEN secret - don't share it
  ⚠ Only expose webhook to trusted networks
  ⚠ Token is sent as query parameter - use HTTPS on public URLs
```

**Important:**
- The token is like a password - keep it secure
- Don't use on untrusted WiFi networks
- If exposing to internet, use HTTPS (not HTTP)

### Phase 8: Troubleshooting Guide

```
🆘 Troubleshooting:
----------------------------------------------------------------------
  Problem: Buttons don't appear in notifications
  Solution: Check ACTION_WEBHOOK_TOKEN and ACTION_WEBHOOK_BASE_URL in .env

  Problem: Button clicks don't work
  Solution: Test if phone can reach the webhook URL from browser

  Problem: Action fails with error
  Solution: Check actions.log for error details

  Problem: Port 8000 already in use
  Solution: Set WEBHOOK_PORT=8001 in .env and restart the server
```

## Common Scenarios

### Scenario 1: First-Time Setup

```bash
# Terminal 1: Start webhook
python scripts/webhook_server.py

# Terminal 2: Check it's working
curl http://localhost:8000/health
# Should return: {"status":"ok","service":"SlopePing Webhook"}

# Terminal 3: Start checker
python run_checker.py

# Phone: Subscribe to ntfy topic and wait for notification
# Phone: Tap Open SlopePing, review the lesson, then confirm the action
```

### Scenario 2: Testing on Local Network

```bash
# On your computer
ifconfig | grep "inet " | grep -v 127.0.0.1

# Output example: inet 192.168.1.100 netmask 0xffffff00 broadcast 192.168.1.255

# Update .env
ACTION_WEBHOOK_BASE_URL=http://192.168.1.100:8000
WEBHOOK_HOST=0.0.0.0

# Restart server and test from phone browser
http://192.168.1.100:8000/health
```

### Scenario 3: Debugging an Action

```bash
# Terminal 1: Watch for action errors
tail -f actions.log

# Terminal 2 (Phone): Open SlopePing and confirm an action

# Terminal 1 will show:
# {
#   "timestamp": "2026-06-15T15:42:07.123456+02:00",
#   "action": "accept",
#   "lesson_id": "Do, 15.06.2026|14:00|16:00|Skischule|Extraschicht",
#   "result": "success",
#   "message": "Selected 'Bestätigen' and clicked Speichern.",
#   ...
# }
```

## Real-Time Logs During Action

When an action is confirmed from your phone, you'll see in the webhook terminal:

```
[webhook] 🔄 Processing ACCEPT action
[webhook]    lesson_id: Do, 15.06.2026|14:00|16:00|Skischule|Extraschicht Skischule
[webhook]    Loading configuration...
[webhook]    Starting browser session...
[webhook]    Logging in...
[action] Looking for lesson: Do, 15.06.2026|14:00|16:00|Skischule|Extraschicht Skischule
[parser] Locating Übersicht schedule table.
[parser] Using table#TAB.
[action] Matched lesson_id: Do, 15.06.2026|14:00|16:00|Skischule|Extraschicht Skischule
[action] confirmation_status: pending
[action] Selecting 'Bestätigen'.
[action] Clicking Speichern.
[action] Wrote action log: actions.log
[webhook]    ✅ Action ACCEPT successful
[webhook]    Generating calendar event...
[ics] Created calendar event: calendar_events/Do, 15.06.2026_Extraschicht_Skischu_accept_20260615-153432.ics
[webhook]    📅 Calendar event saved: calendar_events/...
```

**Reading the logs:**
- 🔄 = Processing started
- ✅ = Step completed successfully
- ❌ = Step failed
- 📅 = Calendar file created
- 💓 = Health check received

## Advanced: Saving Logs to File

```bash
# Save all output to a file
python scripts/webhook_server.py > webhook.log 2>&1 &

# Watch the log in real-time
tail -f webhook.log

# Find errors
grep -i "error\|failed\|✗" webhook.log
```

## Pro Tips

1. **Keep Multiple Terminals Open**
   - Terminal 1: Webhook server (logs all requests)
   - Terminal 2: Checker runner
   - Terminal 3: Tail actions.log

2. **Test the API**
   ```bash
   # In a browser or curl
   http://localhost:8000/docs
   # Interactive API documentation - can test endpoints here
   ```

3. **Monitor Calendar Events**
   ```bash
   # Watch for new .ics files
   ls -la calendar_events/ | tail -1
   # Should see newest file when action succeeds
   ```

4. **Restart the Server**
   ```bash
   # If config changed or you need to restart
   # Press Ctrl+C in the webhook terminal
   # Then: python scripts/webhook_server.py
   ```

## Still Having Issues?

Check these in order:

1. **Is webhook running?**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Is token correct in .env?**
   ```bash
   grep ACTION_WEBHOOK_TOKEN .env
   ```

3. **Is phone on same network?**
   ```bash
   # On phone, open browser: http://YOUR_IP:8000/health
   ```

4. **Is lesson actually pending?**
   ```bash
   # Check before clicking button
   python run_checker.py
   # Look for "confirmation_status: pending"
   ```

5. **Check error logs**
   ```bash
   tail -50 actions.log | jq '.[] | select(.result != "success")'
   ```
