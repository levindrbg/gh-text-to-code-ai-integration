#!/usr/bin/env bash
# Setup: create venv and install dependencies.
# Run from repo root:  bash 00_setup/setup.sh
# Or from 00_setup:    bash setup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$REPO_ROOT/venv"
REQUIREMENTS="$SCRIPT_DIR/requirements.txt"

cd "$REPO_ROOT"

if [[ -d "$VENV_DIR" ]]; then
  echo "venv already exists at $VENV_DIR"
else
  echo "Creating venv at $VENV_DIR ..."
  python -m venv "$VENV_DIR"
fi

if [[ -f "$VENV_DIR/bin/activate" ]]; then
  source "$VENV_DIR/bin/activate"
elif [[ -f "$VENV_DIR/Scripts/activate" ]]; then
  # Windows (Git Bash, etc.)
  source "$VENV_DIR/Scripts/activate"
else
  echo "Error: could not find venv activate script" >&2
  exit 1
fi

echo "Installing requirements ..."
pip install --upgrade pip
pip install -r "$REQUIREMENTS"

echo ""
echo "Setup done. To activate the venv later:"
if [[ -f "$VENV_DIR/bin/activate" ]]; then
  echo "  source $VENV_DIR/bin/activate   # Linux/macOS"
else
  echo "  source $VENV_DIR/Scripts/activate   # Windows (Git Bash)"
  echo "  Or in PowerShell: $VENV_DIR\\Scripts\\Activate.ps1"
fi
echo ""
echo "Remember to create 00_setup/.env with ANTHROPIC_API_KEY (or CLAUDE_API_KEY)."
