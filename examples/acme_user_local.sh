#!/usr/bin/env bash
#
# User Workflow Example: Clone repo and initialize with template
#
# This demonstrates a typical developer workflow:
# 1. Clone an existing repository from Gitea
# 2. Set up local workspace organized by user
# 3. Initialize with project template if Jenkinsfile doesn't exist
# 4. Commit and push to feature-init branch
#
# Usage: ./acme_user_local.sh USERNAME REPO WORKSPACE_DIR
#   USERNAME: Required. Gitea user
#   REPO: Required. Repository to clone
#   WORKSPACE_DIR: Required. Base directory for repos (must exist)
#   
#   Repos will be cloned to: WORKSPACE_DIR/USERNAME/REPO
#   Password is assumed to be 'secret' for all users
#
# Prerequisites: Run acme_org.sh first to create the user, org, and repos

set -e

source .venv/bin/activate

# Configuration
USERNAME="${1}"
REPO="${2}"
WORKSPACE_BASE="${3}"
PASSWORD="secret"
ORG="acme"

# Validate required parameters
if [ -z "${USERNAME}" ] || [ -z "${REPO}" ] || [ -z "${WORKSPACE_BASE}" ]; then
    echo "❌ Error: Missing required parameters"
    echo ""
    echo "Usage: $0 USERNAME REPO WORKSPACE_DIR"
    echo ""
    echo "  USERNAME:       Gitea user (e.g., john, jane)"
    echo "  REPO:           Repository to clone (e.g., demo-app, demo-db)"
    echo "  WORKSPACE_DIR:  Base directory for repos (must exist, e.g., ~/Local)"
    echo ""
    echo "Examples:"
    echo "  $0 john demo-app ~/Local"
    echo "  $0 jane demo-db ~/Projects"
    exit 1
fi

# Expand tilde in path
WORKSPACE_BASE=$(eval echo "${WORKSPACE_BASE}")
WORKSPACE="${WORKSPACE_BASE}/${USERNAME}"

echo "============================================================"
echo "User Workflow: Clone Repository for Local Development"
echo "============================================================"
echo "User:      ${USERNAME}"
echo "Org:       ${ORG}"
echo "Repo:      ${REPO}"
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

# Step 1: Clone repository
echo "Step 1: Cloning repository to workspace..."
mkdir -p "${WORKSPACE}"
echo "   Using workspace: ${WORKSPACE}"

# Check if repo directory already exists
if [ -d "${WORKSPACE}/${REPO}" ]; then
    echo "⚠️  Warning: Directory '${WORKSPACE}/${REPO}' already exists"
    if [ -d "${WORKSPACE}/${REPO}/.git" ]; then
        echo "❌ Error: Directory already contains a git repository. Aborting."
        exit 1
    fi
    echo "   Proceeding with clone (no .git directory found)"
fi

dt git clone "${REPO}" --org "${ORG}" --dest "${WORKSPACE}" --username "${USERNAME}" --password "${PASSWORD}"
echo "✅ Repository cloned to ${WORKSPACE}/${REPO}"
echo ""

# Step 2: Check if initialization is needed
REPO_PATH="${WORKSPACE}/${REPO}"
TEMPLATE_PATH="project_templates/${REPO}"

echo "Step 2: Checking if initialization is needed..."
if [ -f "${REPO_PATH}/Jenkinsfile" ]; then
    echo "✅ Repository already initialized (Jenkinsfile exists)"
    echo "   Skipping template initialization"
else
    echo "📦 Jenkinsfile not found - initializing with project template..."
    
    # Check if template exists
    if [ ! -d "${TEMPLATE_PATH}" ]; then
        echo "⚠️  Warning: No project template found at '${TEMPLATE_PATH}'"
        echo "   Skipping initialization"
    else
        echo "   Copying template from: ${TEMPLATE_PATH}"
        
        # Copy template files
        rsync -av --exclude='.git' "${TEMPLATE_PATH}/" "${REPO_PATH}/"
        
        # Navigate to repo
        cd "${REPO_PATH}"
        
        # Configure git user
        git config user.name "${USERNAME}"
        git config user.email "${USERNAME}@${ORG}.demo"
        
        # Check if feature-init branch already exists remotely
        git fetch origin feature-init 2>/dev/null || true
        
        if git rev-parse --verify origin/feature-init >/dev/null 2>&1; then
            echo "⚠️  Warning: feature-init branch already exists on remote"
            echo "   Creating local branch with a unique name: feature-init-local"
            git checkout -b feature-init-local
        else
            # Create and checkout feature-init branch
            git checkout -b feature-init
        fi
        
        echo "✅ Repository initialized with template on $(git branch --show-current) branch"
        echo "   Files copied but not yet committed"
    fi
fi
echo ""

echo "============================================================"
echo "✅ Local workspace ready!"
echo "============================================================"
echo ""
echo "Repository URL:"
echo "http://localhost:3000/${ORG}/${REPO}"
echo ""
echo "Local project location:"
echo "${WORKSPACE}/${REPO}"
echo ""
echo "Next steps:"
echo "  cd ${WORKSPACE}/${REPO}"
if [ -d "${REPO_PATH}/.git/refs/heads/feature-init" ] 2>/dev/null || [ -d "${REPO_PATH}/.git/refs/heads/feature-init" ] 2>/dev/null; then
    BRANCH_NAME=$(cd "${REPO_PATH}" && git branch --show-current 2>/dev/null || echo "feature-init")
    echo "  git checkout ${BRANCH_NAME}"
    echo "  # Review changes, then commit and push:"
    echo "  git add ."
    echo "  git commit -m 'Initialize with template'"
    echo "  git push -u origin ${BRANCH_NAME}"
else
    echo "  # Start developing!"
fi
echo ""
