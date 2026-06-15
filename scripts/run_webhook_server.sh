#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
PYTHON_BIN="${PROJECT_ROOT}/.venv/bin/python"
LOG_DIR="${PROJECT_ROOT}/logs"
LOG_FILE="${LOG_DIR}/webhook_server.log"

mkdir -p "${LOG_DIR}"
cd "${PROJECT_ROOT}"

{
  printf '\n[%s] Starting SlopePing webhook server\n' "$(date '+%Y-%m-%d %H:%M:%S %z')"

  if [[ ! -x "${PYTHON_BIN}" ]]; then
    printf '[%s] ERROR: Python not found or not executable: %s\n' "$(date '+%Y-%m-%d %H:%M:%S %z')" "${PYTHON_BIN}"
    printf '[%s] Hint: create .venv and install dependencies first.\n' "$(date '+%Y-%m-%d %H:%M:%S %z')"
    exit 127
  fi

  if [[ ! -f "${PROJECT_ROOT}/.env" ]] || ! grep -Eq '^[[:space:]]*ACTION_WEBHOOK_TOKEN[[:space:]]*=[[:space:]]*[^[:space:]#]+' "${PROJECT_ROOT}/.env"; then
    printf '[%s] ACTION_WEBHOOK_TOKEN is not configured; webhook server not started.\n' "$(date '+%Y-%m-%d %H:%M:%S %z')"
    exit 0
  fi

  set +e
  "${PYTHON_BIN}" "${PROJECT_ROOT}/scripts/webhook_server.py"
  status=$?
  set -e
  printf '[%s] Webhook server stopped with exit code %s\n' "$(date '+%Y-%m-%d %H:%M:%S %z')" "${status}"
  exit "${status}"
} >> "${LOG_FILE}" 2>&1
