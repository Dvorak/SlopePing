#!/usr/bin/env bash
set -euo pipefail

LABELS=("com.slopeping" "com.slopeping.webhook")

for label in "${LABELS[@]}"; do
  plist_path="${HOME}/Library/LaunchAgents/${label}.plist"

  launchctl bootout "gui/$(id -u)" "${plist_path}" >/dev/null 2>&1 || true

  if [[ -f "${plist_path}" ]]; then
    rm "${plist_path}"
    echo "Removed ${plist_path}"
  else
    echo "No plist found at ${plist_path}"
  fi

  echo "Uninstalled ${label}"
done
