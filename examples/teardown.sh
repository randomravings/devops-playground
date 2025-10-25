#!/usr/bin/env bash
#
# Teardown - Clean DevOps Environment
#
# This script tears down the complete DevOps environment:
# - Stops and removes all Docker containers
# - Cleans up volumes and networks
#

set -e  # Exit on error

echo "============================================================"
echo "Teardown - DevOps Environment"
echo "============================================================"

# Activate virtual environment
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Run ./env_setup.sh first."
    exit 1
fi

source .venv/bin/activate

# Teardown environment
echo ""
echo "Tearing down Docker environment..."
dt env down

echo ""
echo "============================================================"
echo "✅ Environment teardown complete!"
echo "============================================================"
echo ""
