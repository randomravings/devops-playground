#!/usr/bin/env bash
#
# Acme Organization Setup - Complete DevOps Environment
#
# This script sets up a complete working environment for the Acme organization:
# - Docker environment (Gitea + Jenkins)
# - Acme organization with developers team
# - Users: john, jane (developers team members)
# - Repositories: demo-app, demo-db, dbci-tools
# - Branch protection and webhooks configured
# - Jenkins organization folder with credentials
#
# This represents a realistic small-team development setup.
#

set -e  # Exit on error

ORG_NAME="acme"
ORG_NAME_UPPER=$(echo "${ORG_NAME}" | tr '[:lower:]' '[:upper:]')

echo "============================================================"
echo "Acme Organization Setup - ${ORG_NAME_UPPER}"
echo "============================================================"

# Activate virtual environment
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Run ./env_setup.sh first."
    exit 1
fi

source .venv/bin/activate

# 1. Setup environment (without creating org yet)
echo ""
echo "1. Setting up Docker environment..."
dt env up

# 2. Create Acme organization explicitly
echo ""
echo "2. Creating '$ORG_NAME' organization..."
dt git org "$ORG_NAME" --owner admin --description "Acme Corporation"

# 3. Create users
echo ""
echo "3. Creating users..."
dt git user john --password secret --org "$ORG_NAME"
dt git user jane --password secret --org "$ORG_NAME"

# 4. Create developers team
echo ""
echo "4. Creating 'developers' team..."
dt git team developers --org "$ORG_NAME" --permission write

# 5. Add team members
echo ""
echo "5. Adding team members..."
dt git add-member developers --org "$ORG_NAME" --username john
dt git add-member developers --org "$ORG_NAME" --username jane

# 6. Create repositories
echo ""
echo "6. Creating repositories..."
dt git repo demo-app --org "$ORG_NAME" --description "Demo application"
dt git repo demo-db --org "$ORG_NAME" --description "Demo database"
dt git repo dbci-tools --org "$ORG_NAME" --description "Database CI tools"

# 7. Setup branch protection
echo ""
echo "7. Setting up branch protection with status checks..."
dt git protect demo-app --org "$ORG_NAME" --team developers
dt git protect demo-db --org "$ORG_NAME" --team developers --enable-status-check

# 7b. Enable auto-delete branches after merge
echo ""
echo "7b. Enabling auto-delete branches after merge..."
dt git auto-delete-branch demo-app --org "$ORG_NAME"
dt git auto-delete-branch demo-db --org "$ORG_NAME"
dt git auto-delete-branch dbci-tools --org "$ORG_NAME"

# 8. Setup Jenkins webhook
echo ""
echo "8. Setting up Jenkins webhook..."
dt git webhook

# 9. Create Jenkins credentials
echo ""
echo "9. Creating Jenkins credentials..."
dt ci creds gitea-credentials --username admin --password secret --description "Gitea admin credentials for Jenkins"

# 10. Create Jenkins organization folder
echo ""
echo "10. Creating Jenkins organization folder for '$ORG_NAME'..."
dt ci org "${ORG_NAME}-folder" --org "$ORG_NAME" --credentials gitea-credentials --description "Jenkins org folder for $ORG_NAME repos"

# 11. Initialize dbci-tools repository (using Python for this complex step)
echo ""
echo "11. Initializing dbci-tools repository..."
python3 << 'PYTHON_SCRIPT'
import tempfile
from pathlib import Path
from devops_tools import config, gitea, project

cfg = config.get_config()
org_name = "acme"

if gitea.repo_file_exists("dbci-tools", org_name, "pyproject.toml"):
    print("   dbci-tools already initialized; skipping.")
else:
    with tempfile.TemporaryDirectory() as tmpdir:
        clone_dest = Path(tmpdir)
        
        print("   Cloning dbci-tools...")
        gitea.clone_repo(
            "dbci-tools",
            org_name,
            str(clone_dest),
            cfg.gitea_admin_user,
            cfg.gitea_admin_password,
        )
        
        repo_path = clone_dest / "dbci-tools"
        
        print("   Copying template content...")
        project.init_dbci_tools(str(repo_path))
        
        print("   Committing and pushing...")
        project.init_commit(str(repo_path), "Initial commit: Add dbci-tools template")
        
        print("   ✅ dbci-tools initialized")
PYTHON_SCRIPT

echo ""
echo "============================================================"
echo "✅ Acme Organization Setup Complete!"
echo "============================================================"
echo ""
echo "Gitea:   http://localhost:3000"
echo "Jenkins: http://localhost:8080"
echo ""
echo "Credentials:"
echo "  Gitea Admin:   admin / secret"
echo "  Jenkins Admin: admin / secret"
echo "  Team Members:  john / secret, jane / secret"
echo ""
echo "Organization: $ORG_NAME"
echo "  Team: developers (john, jane)"
echo "  Repos: demo-app, demo-db, dbci-tools"
echo ""
echo "Next steps:"
echo "  - Browse Gitea org: http://localhost:3000/$ORG_NAME"
echo "  - Clone repos: dt git clone demo-app --org $ORG_NAME --dest ~/Local"
echo "  - Init projects: dt p maven ~/Local/my-project"
echo "  - Teardown: dt env down"
echo ""
