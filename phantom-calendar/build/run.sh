#! /bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$(dirname "$(git -C "$PROJECT_DIR" rev-parse --git-common-dir)")/phantom-calendar/.venv"

if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
  echo "ERROR: venv not found at $VENV_DIR" >&2
  exit 1
fi

source "$VENV_DIR/bin/activate"
cd "$PROJECT_DIR"

echo "=== Phantom Calendar — Development Environment ==="
echo "Python: $(python --version)"
echo "Venv:   $VENV_DIR"
echo ""

nohup uv run main.py &
