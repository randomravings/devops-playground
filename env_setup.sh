#!/bin/bash
# Setup virtual environment for devops_tools

set -e

cd "$(dirname "$0")"

echo "🔧 Setting up virtual environment..."

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
else
    echo "Virtual environment already exists."
fi

# Activate and upgrade pip
source .venv/bin/activate
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null

# Install package in editable mode
echo "Installing devops_tools package..."
pip install -e . > /dev/null

echo ""
echo "✅ Setup complete!"
echo ""
echo "Usage:"
echo "  source .venv/bin/activate      # Activate venv"
echo "  python examples/full_setup.py  # Run example scripts"
echo "  devops-tools --help            # Use CLI"
echo "  deactivate                     # Exit venv"
