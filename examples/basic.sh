#!/usr/bin/env bash
#
# Bare Minimum Setup - Basic DevOps Environment
#
# This script sets up the absolute minimum:
# - Docker environment (Gitea + Jenkins)
# - Only admin users
# - No teams, repos, or additional configuration
#
# Use this as a clean starting point for custom setups.
#

set -e  # Exit on error

echo "============================================================"
echo "Bare Minimum Setup - DevOps Environment"
echo "============================================================"

# Activate virtual environment
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Run ./env_setup.sh first."
    exit 1
fi

source .venv/bin/activate

# Setup environment (Gitea + Jenkins with admin users only, no org)
echo ""
echo "Setting up Docker environment..."
dt env up

echo ""
echo "============================================================"
echo "✅ Bare minimum environment ready!"
echo "============================================================"
echo ""
echo "Gitea:   http://localhost:3000"
echo "Jenkins: http://localhost:8080"
echo ""
echo "Gitea Admin:   admin / secret"
echo "Jenkins Admin: admin / secret"
echo ""
echo "Next steps:"
echo "  - Use 'dt git user' to create users"
echo "  - Use 'dt git org' to create organizations"
echo "  - Use 'dt git repo' to create repositories"
echo "  - Use 'dt ci creds' to create Jenkins credentials"
echo "  - Teardown with: dt env down"
echo ""
