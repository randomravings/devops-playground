#!/usr/bin/env bash
#
# User Workflow Example: Clone repos for local development
#
# This demonstrates a typical developer workflow:
# 1. Clone repositories from Gitea
# 2. Set up local workspace organized by user
# 3. Create feature branches on specific repos
#
# Usage:
#   ./acme_user_local.sh USERNAME WORKSPACE_DIR
#
#   USERNAME:       Gitea user (e.g., john, jane)
#   WORKSPACE_DIR:  Base directory for repos (must exist, e.g., ~/Local)
#
#   Repos will be cloned to: WORKSPACE_DIR/USERNAME/REPO
#   Password is assumed to be 'secret' for all users
#
# Prerequisites: Run acme_org.sh first to create the user, org, and repos

set -e

# Get script directory for template paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

source .venv/bin/activate

# Configuration
USERNAME="${1}"
WORKSPACE_BASE="${2}"
PASSWORD="secret"
ORG="acme"

# Validate required parameters
if [ -z "${USERNAME}" ] || [ -z "${WORKSPACE_BASE}" ]; then
    echo "❌ Error: Missing required parameters"
    echo ""
    echo "Usage: $0 USERNAME WORKSPACE_DIR"
    echo ""
    echo "  USERNAME:       Gitea user (e.g., john, jane)"
    echo "  WORKSPACE_DIR:  Base directory for repos (must exist, e.g., ~/Local)"
    echo ""
    echo "Example:"
    echo "  $0 john ~/Local"
    exit 1
fi

# Expand tilde in path
WORKSPACE_BASE=$(eval echo "${WORKSPACE_BASE}")
WORKSPACE="${WORKSPACE_BASE}/${USERNAME}"

echo "============================================================"
echo "User Workflow: Clone Repositories for Local Development"
echo "============================================================"
echo "User:      ${USERNAME}"
echo "Org:       ${ORG}"
echo "Workspace: ${WORKSPACE}"
echo ""

# Validation: Check if base workspace directory exists
echo "Validating workspace base directory..."
if [ ! -d "${WORKSPACE_BASE}" ]; then
    echo "❌ Error: Base workspace directory '${WORKSPACE_BASE}' does not exist"
    echo "   Please create it first: mkdir -p ${WORKSPACE_BASE}"
    exit 1
fi
echo "✅ Workspace base directory exists: ${WORKSPACE_BASE}"
echo ""

# Validation: Check if user exists
echo "Validating user '${USERNAME}' exists..."
if ! dt git user-exists "${USERNAME}" &>/dev/null; then
    echo "❌ Error: User '${USERNAME}' does not exist in Gitea"
    echo "   Prerequisites: Run acme_org.sh first to create the user and org"
    echo "   Or manually: dt git user ${USERNAME} --password secret --org ${ORG}"
    exit 1
fi
echo ""

mkdir -p "${WORKSPACE}"



# Clone repositories
echo "Cloning repositories..."
echo ""

echo "1. Cloning dbci-tools..."
dt git clone dbci-tools --org "${ORG}" --dest "${WORKSPACE}" --username "${USERNAME}" --password "${PASSWORD}"
echo "✅ dbci-tools cloned"
echo ""

echo "2. Cloning etl-framework..."
dt git clone etl-framework --org "${ORG}" --dest "${WORKSPACE}" --username "${USERNAME}" --password "${PASSWORD}"
echo "✅ etl-framework cloned"
echo ""

echo "3. Cloning demo-dw..."
dt git clone demo-dw --org "${ORG}" --dest "${WORKSPACE}" --username "${USERNAME}" --password "${PASSWORD}"
echo "✅ demo-dw cloned"

# Check if demo-dw needs initialization
if [ ! -f "${WORKSPACE}/demo-dw/Jenkinsfile" ]; then
    echo "   Jenkinsfile not found - initializing with template"
    rsync -av --exclude='.git' "${PROJECT_ROOT}/projects/demo-dw/" "${WORKSPACE}/demo-dw/"
    cd "${WORKSPACE}/demo-dw"
    git config user.name "${USERNAME}"
    git config user.email "${USERNAME}@${ORG}.demo"
    git checkout -b feature-init
    echo "   ✅ Copied template and created feature-init branch in demo-dw"
else
    echo "   Repository already initialized"
fi
echo ""

echo "4. Cloning demo-etl..."
dt git clone demo-etl --org "${ORG}" --dest "${WORKSPACE}" --username "${USERNAME}" --password "${PASSWORD}"
echo "✅ demo-etl cloned"

# Check if demo-etl needs initialization
if [ ! -f "${WORKSPACE}/demo-etl/pyproject.toml" ]; then
    echo "   pyproject.toml not found - initializing with template"
    rsync -av --exclude='.git' "${PROJECT_ROOT}/projects/demo-etl/" "${WORKSPACE}/demo-etl/"
    cd "${WORKSPACE}/demo-etl"
    git config user.name "${USERNAME}"
    git config user.email "${USERNAME}@${ORG}.demo"
    git checkout -b feature-init
    echo "   ✅ Copied template and created feature-init branch in demo-etl"
else
    echo "   Repository already initialized"
fi
echo ""

echo "============================================================"
echo "✅ Local workspace ready!"
echo "============================================================"
echo ""
echo "Cloned repositories:"
echo "  ${WORKSPACE}/dbci-tools"
echo "  ${WORKSPACE}/etl-framework"
echo "  ${WORKSPACE}/demo-dw"
echo "  ${WORKSPACE}/demo-etl"
echo ""
echo "Repository URLs:"
echo "  http://localhost:3000/${ORG}/dbci-tools"
echo "  http://localhost:3000/${ORG}/etl-framework"
echo "  http://localhost:3000/${ORG}/demo-dw"
echo "  http://localhost:3000/${ORG}/demo-etl"
echo ""
