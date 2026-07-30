#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
PYTHON_BIN="${PROJECT_ROOT}/.venv/bin/python"
if [[ -x "${PYTHON_BIN}" ]]; then
  LOG_DIR="$("${PYTHON_BIN}" "${PROJECT_ROOT}/scripts/runtime_path.py" logs_dir)"
else
  LOG_DIR="${PROJECT_ROOT}/var/logs"
fi
LOG_FILE="${LOG_DIR}/checker.log"

mkdir -p "${LOG_DIR}"
cd "${PROJECT_ROOT}"

if [[ -x "${PYTHON_BIN}" ]]; then
  "${PYTHON_BIN}" "${PROJECT_ROOT}/scripts/maintain_runtime.py" ||
    printf '[%s] WARNING: Runtime maintenance failed; continuing.\\n' "$(date '+%Y-%m-%d %H:%M:%S %z')" >&2
fi

{
  printf '\n[%s] Starting SlopePing checker\n' "$(date '+%Y-%m-%d %H:%M:%S %z')"

  if [[ ! -x "${PYTHON_BIN}" ]]; then
    printf '[%s] ERROR: Python not found or not executable: %s\n' "$(date '+%Y-%m-%d %H:%M:%S %z')" "${PYTHON_BIN}"
    printf '[%s] Hint: create .venv and install dependencies first.\n' "$(date '+%Y-%m-%d %H:%M:%S %z')"
    exit 127
  fi

  set +e
  "${PYTHON_BIN}" "${PROJECT_ROOT}/run_checker.py" "$@"
  status=$?
  set -e
  printf '[%s] Finished SlopePing checker with exit code %s\n' "$(date '+%Y-%m-%d %H:%M:%S %z')" "${status}"
  exit "${status}"
} >> "${LOG_FILE}" 2>&1
