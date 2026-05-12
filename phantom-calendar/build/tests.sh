#!/usr/bin/env bash
# Run all Phantom Calendar unit tests.
# Usage: bash build/tests.sh  (from phantom-calendar/ or anywhere inside the repo)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$(dirname "$(git -C "$PROJECT_DIR" rev-parse --git-common-dir)")/phantom-calendar/.venv"

if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
  echo "ERROR: venv not found at $VENV_DIR" >&2
  echo "Run: python3.14 -m venv $VENV_DIR && pip install -r $PROJECT_DIR/requirements.txt" >&2
  exit 1
fi

source "$VENV_DIR/bin/activate"
cd "$PROJECT_DIR"

echo "=== Phantom Calendar — Unit Tests ==="
echo "Python: $(python --version)"
echo "Venv:   $VENV_DIR"
echo ""

# Smoke imports
echo "--- Smoke imports ---"
python tests/smoke_imports.py

# Unit tests
echo ""
echo "--- Unit tests ---"
python -m pytest tests/ -v

echo ""
echo "All tests passed."
