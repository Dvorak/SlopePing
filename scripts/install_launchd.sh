#!/usr/bin/env bash
set -euo pipefail

CHECKER_LABEL="com.slopeping"
WEBHOOK_LABEL="com.slopeping.webhook"
PROJECT_ROOT="$(pwd -P)"
CHECKER_SCRIPT="${PROJECT_ROOT}/scripts/run_checker.sh"
WEBHOOK_SCRIPT="${PROJECT_ROOT}/scripts/run_webhook_server.sh"
PLIST_DIR="${HOME}/Library/LaunchAgents"
CHECKER_PLIST_PATH="${PLIST_DIR}/${CHECKER_LABEL}.plist"
WEBHOOK_PLIST_PATH="${PLIST_DIR}/${WEBHOOK_LABEL}.plist"
LOG_DIR="${PROJECT_ROOT}/logs"

if [[ ! -f "${PROJECT_ROOT}/run_checker.py" ]]; then
  echo "ERROR: run this script from the project root:"
  echo "  cd /path/to/SlopePing"
  echo "  ./scripts/install_launchd.sh"
  exit 1
fi

chmod +x "${CHECKER_SCRIPT}" "${WEBHOOK_SCRIPT}"

mkdir -p "${PLIST_DIR}" "${LOG_DIR}"

cat > "${CHECKER_PLIST_PATH}" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${CHECKER_LABEL}</string>

  <key>ProgramArguments</key>
  <array>
    <string>${CHECKER_SCRIPT}</string>
  </array>

  <key>WorkingDirectory</key>
  <string>${PROJECT_ROOT}</string>

  <key>StartCalendarInterval</key>
  <array>
    <dict>
      <key>Hour</key>
      <integer>8</integer>
      <key>Minute</key>
      <integer>0</integer>
    </dict>
    <dict>
      <key>Hour</key>
      <integer>13</integer>
      <key>Minute</key>
      <integer>0</integer>
    </dict>
    <dict>
      <key>Hour</key>
      <integer>20</integer>
      <key>Minute</key>
      <integer>0</integer>
    </dict>
  </array>

  <key>StandardOutPath</key>
  <string>${LOG_DIR}/checker.launchd.out.log</string>

  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/checker.launchd.err.log</string>
</dict>
</plist>
PLIST

cat > "${WEBHOOK_PLIST_PATH}" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${WEBHOOK_LABEL}</string>

  <key>ProgramArguments</key>
  <array>
    <string>${WEBHOOK_SCRIPT}</string>
  </array>

  <key>WorkingDirectory</key>
  <string>${PROJECT_ROOT}</string>

  <key>RunAtLoad</key>
  <true/>

  <key>KeepAlive</key>
  <dict>
    <key>SuccessfulExit</key>
    <false/>
  </dict>

  <key>ThrottleInterval</key>
  <integer>60</integer>

  <key>StandardOutPath</key>
  <string>${LOG_DIR}/webhook.launchd.out.log</string>

  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/webhook.launchd.err.log</string>
</dict>
</plist>
PLIST

plutil -lint "${CHECKER_PLIST_PATH}"
plutil -lint "${WEBHOOK_PLIST_PATH}"

launchctl bootout "gui/$(id -u)" "${CHECKER_PLIST_PATH}" >/dev/null 2>&1 || true
launchctl bootout "gui/$(id -u)" "${WEBHOOK_PLIST_PATH}" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "${CHECKER_PLIST_PATH}"
launchctl bootstrap "gui/$(id -u)" "${WEBHOOK_PLIST_PATH}"
launchctl enable "gui/$(id -u)/${CHECKER_LABEL}"
launchctl enable "gui/$(id -u)/${WEBHOOK_LABEL}"

echo "Installed ${CHECKER_LABEL}"
echo "Checker plist: ${CHECKER_PLIST_PATH}"
echo "Installed ${WEBHOOK_LABEL}"
echo "Webhook plist: ${WEBHOOK_PLIST_PATH}"
echo "Project: ${PROJECT_ROOT}"
echo "Checker schedule: 08:00, 13:00, 20:00"
echo "Checker log: ${LOG_DIR}/checker.log"
echo "Webhook log: ${LOG_DIR}/webhook_server.log"
