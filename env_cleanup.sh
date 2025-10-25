#!/bin/bash
# Cleanup virtual environment and build artifacts

set -e

cd "$(dirname "$0")"

echo "🧹 Cleaning up..."

# Remove virtual environment
if [ -d ".venv" ]; then
    echo "Removing virtual environment..."
    rm -rf .venv
fi

# Remove build artifacts
echo "Removing build artifacts..."
rm -rf devops_tools.egg-info
rm -rf build dist

# Remove Python cache files
echo "Removing Python cache files..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

echo ""
echo "✅ Cleanup complete!"
