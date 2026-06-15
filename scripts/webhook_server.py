#!/usr/bin/env python
"""Start the SlopePing webhook server."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Add src to path
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
os.chdir(ROOT)

import uvicorn
from dotenv import load_dotenv


def print_banner() -> None:
    """Print startup banner with helpful information."""
    print("\n" + "=" * 70, flush=True)
    print("  🚀 SlopePing Webhook Server", flush=True)
    print("=" * 70, flush=True)


def check_configuration() -> bool:
    """Check and report webhook configuration."""
    load_dotenv(ROOT / ".env")
    
    webhook_token = os.getenv("ACTION_WEBHOOK_TOKEN", "").strip()
    webhook_url = os.getenv("ACTION_WEBHOOK_BASE_URL", "").strip()
    host = os.getenv("WEBHOOK_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = int(os.getenv("WEBHOOK_PORT", "8000"))
    ntfy_topic = os.getenv("NTFY_TOPIC", "").strip()
    
    print("\n📋 Configuration Check:", flush=True)
    print("-" * 70, flush=True)
    
    if webhook_token:
        print(f"  ✓ ACTION_WEBHOOK_TOKEN: {'*' * len(webhook_token)} (configured)", flush=True)
    else:
        print("  ✗ ACTION_WEBHOOK_TOKEN: NOT SET", flush=True)
        print("    → Set this in .env for security", flush=True)
        return False
    
    if webhook_url:
        print(f"  ✓ ACTION_WEBHOOK_BASE_URL: {webhook_url}", flush=True)
    else:
        print("  ⚠ ACTION_WEBHOOK_BASE_URL: Not set (using default)", flush=True)
        print("    → Phone links need a reachable base URL", flush=True)

    print(f"  ✓ WEBHOOK_HOST: {host}", flush=True)
    print(f"  ✓ WEBHOOK_PORT: {port}", flush=True)
    if host == "0.0.0.0":
        print("  ⚠ WEBHOOK_HOST=0.0.0.0 exposes the server on all interfaces.", flush=True)
    
    if ntfy_topic:
        print(f"  ✓ NTFY_TOPIC: {ntfy_topic[:20]}... (configured)", flush=True)
    else:
        print("  ⚠ NTFY_TOPIC: Not set", flush=True)
        print("    → Notifications won't include action buttons", flush=True)
    
    return True


def print_startup_info() -> None:
    """Print startup information and usage instructions."""
    host = os.getenv("WEBHOOK_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = int(os.getenv("WEBHOOK_PORT", "8000"))
    
    print("\n🌐 Server Information:", flush=True)
    print("-" * 70, flush=True)
    print(f"  Server: Running on {host}:{port}", flush=True)
    print(f"  Health Check: http://localhost:{port}/health", flush=True)
    print(f"  API Docs: http://localhost:{port}/docs", flush=True)
    
    print("\n📱 Testing on Your Phone:", flush=True)
    print("-" * 70, flush=True)
    print("  1. Find your machine's local IP address:", flush=True)
    print("     macOS:  ifconfig | grep 'inet '", flush=True)
    print("     Linux:  hostname -I", flush=True)
    print("     Windows: ipconfig | findstr IPv4", flush=True)
    print("", flush=True)
    print("  2. If you want phone access on your local network, update .env:", flush=True)
    print("     ACTION_WEBHOOK_BASE_URL=http://YOUR_IP:8000", flush=True)
    print("     WEBHOOK_HOST=0.0.0.0", flush=True)
    print("", flush=True)
    print("  3. Phone must be on same network and able to reach this URL", flush=True)
    
    print("\n🧪 Quick Test Commands:", flush=True)
    print("-" * 70, flush=True)
    print("  # Health check", flush=True)
    print(f"  curl http://localhost:{port}/health", flush=True)
    print("", flush=True)
    print("  # Test protected control page with invalid token (should return 403)", flush=True)
    print(f"  curl 'http://localhost:{port}/control?token=wrong'", flush=True)
    
    print("\n📝 Understanding the Workflow:", flush=True)
    print("-" * 70, flush=True)
    print("  1. Run: python run_checker.py", flush=True)
    print("     → Checks schedule and sends ntfy notifications", flush=True)
    print("", flush=True)
    print("  2. Pending lessons show an Open SlopePing action in ntfy", flush=True)
    print("     → Opens the mobile control page", flush=True)
    print("", flush=True)
    print("  3. Confirm the action on the control page", flush=True)
    print("     → Then SlopePing logs in, finds the lesson, clicks action, saves", flush=True)
    print("", flush=True)
    print("  4. Calendar event (.ics) saved to calendar_events/", flush=True)
    print("     → Action history logged to actions.log", flush=True)
    
    print("\n📚 Log Files to Monitor:", flush=True)
    print("-" * 70, flush=True)
    print("  • actions.log - Shows all accept/decline actions (JSON format)", flush=True)
    print("  • calendar_events/ - Generated .ics files for your calendar app", flush=True)
    print("  • screenshots/ - Before/after screenshots of actions", flush=True)
    
    print("\n🔒 Security Reminders:", flush=True)
    print("-" * 70, flush=True)
    print("  ⚠ Keep ACTION_WEBHOOK_TOKEN secret - don't share it", flush=True)
    print("  ⚠ Only expose webhook to trusted networks", flush=True)
    print("  ⚠ The control page still uses a URL token - use trusted networks or HTTPS", flush=True)
    
    print("\n🆘 Troubleshooting:", flush=True)
    print("-" * 70, flush=True)
    print("  Problem: Open SlopePing does not appear in notifications", flush=True)
    print("  Solution: Check ACTION_WEBHOOK_TOKEN and ACTION_WEBHOOK_BASE_URL in .env", flush=True)
    print("", flush=True)
    print("  Problem: Button clicks don't work", flush=True)
    print("  Solution: Test if phone can reach the webhook URL from browser", flush=True)
    print("", flush=True)
    print("  Problem: Action fails with error", flush=True)
    print("  Solution: Check actions.log for error details", flush=True)
    print("", flush=True)
    print("  Problem: Port 8000 already in use", flush=True)
    print("  Solution: Set WEBHOOK_PORT=8001 in .env and restart the server", flush=True)
    
    print("\n" + "=" * 70, flush=True)
    print("  ✅ Webhook server is ready to receive requests", flush=True)
    print("  📖 Press Ctrl+C to stop the server", flush=True)
    print("=" * 70 + "\n", flush=True)


if __name__ == "__main__":
    print_banner()
    
    if not check_configuration():
        print("\n⚠️  Configuration incomplete!", flush=True)
        print("Please set ACTION_WEBHOOK_TOKEN in .env file.", flush=True)
        print("Run: python -c \"import secrets; print(secrets.token_urlsafe(32))\"", flush=True)
        sys.exit(1)
    
    print_startup_info()
    
    # Start the server
    host = os.getenv("WEBHOOK_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = int(os.getenv("WEBHOOK_PORT", "8000"))
    print("Starting server...\n", flush=True)
    uvicorn.run("slopeping.webhook:app", host=host, port=port, reload=False)
