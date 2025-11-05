#!/usr/bin/env bash
set -euo pipefail

# ETL Framework - Bootstrap script
# Delegates to Python CLI

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if etl-framework command is available in current environment
has_etl_framework() {
  command -v etl-framework >/dev/null 2>&1
}

# Check if python3.12 is available
has_python() {
  command -v python3.12 >/dev/null 2>&1
}

# Parse command and project directory
COMMAND="${1:-}"
PROJECT_DIR="."

# Parse --project-dir argument for non-setup commands
if [ "$COMMAND" != "setup" ]; then
  PARSE_NEXT=false
  for arg in "$@"; do
    if [ "$PARSE_NEXT" = true ]; then
      PROJECT_DIR="$arg"
      break
    fi
    if [ "$arg" = "--project-dir" ] || [ "$arg" = "-p" ]; then
      PARSE_NEXT=true
    fi
  done
fi

# For setup command, run directly with python (no venv needed yet)
if [ "$COMMAND" = "setup" ]; then
  if ! has_python; then
    echo "✗ Error: python3.12 not found"
    echo "  Please install Python 3.12:"
    echo "  brew install python@3.12"
    exit 1
  fi
  
  # Run setup directly using standalone script (only uses stdlib)
  python3.12 "$DIR/dagster_etl_framework/setup_standalone.py" "$@"
  exit $?
fi

# For other commands, check if project venv exists and use it
if [ "$COMMAND" = "run" ] || [ "$COMMAND" = "test" ] || [ "$COMMAND" = "teardown" ]; then
  # Resolve to absolute path
  PROJECT_DIR="$(cd "$PROJECT_DIR" 2>/dev/null && pwd || echo "$PROJECT_DIR")"
  PROJECT_VENV="$PROJECT_DIR/.venv"
  
  if [ ! -d "$PROJECT_VENV" ]; then
    echo "✗ Error: Project virtual environment not found at $PROJECT_VENV"
    echo "  Please run setup first:"
    echo "  $0 setup --project-dir $PROJECT_DIR --warehouse csv"
    exit 1
  fi
  
  # Activate project venv
  source "$PROJECT_VENV/bin/activate"
  
  # Verify etl-framework is available
  if ! has_etl_framework; then
    echo "✗ Error: etl-framework not found in project venv"
    echo "  Please run setup first:"
    echo "  $0 setup --project-dir $PROJECT_DIR --warehouse csv"
    exit 1
  fi
  
  # Run the command
  etl-framework "$@"
  exit $?
fi

# For help or unknown commands
if [ -z "$COMMAND" ] || [ "$COMMAND" = "-h" ] || [ "$COMMAND" = "--help" ]; then
  if ! has_python; then
    echo "✗ Error: python3.12 not found"
    echo "  Please install Python 3.12"
    exit 1
  fi
  python3.12 "$DIR/dagster_etl_framework/setup_standalone.py" "$@"
else
  echo "✗ Error: Unknown command '$COMMAND'"
  echo "  Valid commands: setup, run, test, teardown"
  exit 1
fi
