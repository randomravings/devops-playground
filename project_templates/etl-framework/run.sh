#!/usr/bin/env bash
set -euo pipefail

# ETL Framework - Slim Bootstrap Script
# Handles virtual environment setup and delegates to Python CLI

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$DIR/.venv"

# Set up and activate virtual environment
setup_venv() {
  if [ ! -d "$VENV" ]; then
    echo "Setting up virtual environment..."
    python3.12 -m venv "$VENV"
    echo "Installing framework..."
    "$VENV/bin/pip" install --quiet -e "$DIR"
    echo "✅ Framework ready"
  fi
}

# Bootstrap and delegate to Python CLI
setup_venv
"$VENV/bin/python" -m dagster_etl_framework.cli_main "$@"