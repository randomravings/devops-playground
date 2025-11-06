#!/usr/bin/env bash
set -euo pipefail

# ETL Framework - Slim Bootstrap Script
# Handles virtual environment setup and delegates to Python CLI

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$DIR/.etl-venv"

# Set up and activate virtual environment
setup_venv() {
  if [ ! -d "$VENV" ]; then
    echo "Setting up virtual environment..."
    python3.12 -m venv "$VENV"
    source "$VENV/bin/activate"
    python -m pip install -e "$DIR"
  else
    source "$VENV/bin/activate"
  fi
}

# Bootstrap and delegate to Python CLI
setup_venv
etl "$@"