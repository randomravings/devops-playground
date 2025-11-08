#!/usr/bin/env bash
set -euo pipefail

# ETL Framework - Slim Bootstrap Script
# Handles virtual environment setup and delegates to Python CLI

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$DIR/.venv"

# Set up and activate virtual environment (only for INSTALL)
setup_venv() {
  if [ ! -d "$VENV" ]; then
    echo "Setting up virtual environment..."
    python3.12 -m venv "$VENV"
    echo "Installing framework..."
    "$VENV/bin/pip" install --quiet -e "$DIR"
    echo "✅ Framework ready"
  fi
}

# Check if .venv exists (for non-INSTALL commands)
check_venv() {
  if [ ! -d "$VENV" ]; then
    echo "✗ Error: ETL framework not installed"
    echo "  Framework directory: $DIR"
    echo "  Missing: $VENV"
    echo "  Run: ./run.sh INSTALL"
    exit 1
  fi
}

# Handle commands
if [ $# -eq 0 ]; then
  echo "Error: No command provided"
  echo "Usage: ./run.sh COMMAND [args...]"
  exit 1
fi

COMMAND="$1"

# Bootstrap based on command
if [ "$COMMAND" = "INSTALL" ]; then
  setup_venv
else
  check_venv
fi

# Delegate to Python CLI
"$VENV/bin/python" -m dagster_etl_framework.cli_main "$@"