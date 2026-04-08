#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
PYTHON_BIN="$(command -v python3 || command -v python)"

if [[ -z "${PYTHON_BIN}" ]]; then
  echo "Python is required but was not found in PATH." >&2
  exit 1
fi

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi

"${VENV_DIR}/bin/python" -m ensurepip --upgrade >/dev/null
"${VENV_DIR}/bin/python" -m pip install --upgrade pip >/dev/null
"${VENV_DIR}/bin/python" -m pip install -r "${ROOT_DIR}/requirements.txt" >/dev/null

exec "${VENV_DIR}/bin/python" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
