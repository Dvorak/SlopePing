#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

if [[ -n "${SLOPEPING_PYTHON:-}" ]]; then
  PYTHON_BIN="${SLOPEPING_PYTHON}"
elif [[ -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
  PYTHON_BIN="${PROJECT_ROOT}/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

cd "${PROJECT_ROOT}"

"${PYTHON_BIN}" -m ruff format --check .
"${PYTHON_BIN}" -m ruff check .
"${PYTHON_BIN}" -m mypy
"${PYTHON_BIN}" -m pytest
