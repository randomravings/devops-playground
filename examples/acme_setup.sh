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

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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

# 2. Create Jenkins organization folder
echo ""
echo "2. Creating Jenkins organization folder for '$ORG_NAME'..."
dt ci org new "${ORG_NAME}"

# 3. Create Acme organization explicitly
echo ""
echo "3. Creating '$ORG_NAME' organization..."
dt git org new "$ORG_NAME" -d "Acme Corporation"

# 4. Create users
echo ""
echo "4. Creating users..."
dt git user new john -o "$ORG_NAME"
dt git user new jane -o "$ORG_NAME"

# 5. Create developers team
echo ""
echo "5. Creating 'developers' team..."
dt git team new developers -o "$ORG_NAME" -m write

# 6. Add team members
echo ""
echo "6. Adding team members..."
dt git member new john -o acme -t developers
dt git member new jane -o acme -t developers

# 7. Create repositories
echo ""
echo "7. Creating repositories..."
dt git repo new dbci-tools -o "$ORG_NAME" -d "Database CI tools"
dt git repo new etl-framework -o "$ORG_NAME" -d "ETL Framework tools"
dt git repo new demo-dw -o "$ORG_NAME" -d "Demo database"
dt git repo new demo-etl -o "$ORG_NAME" -d "Demo ETL application"

# 8. Setup branch protection
echo ""
echo "8. Setting up branch protection with status checks..."
dt git repo protect new demo-dw -o "$ORG_NAME" -t developers --status-check
dt git repo protect new demo-etl -o "$ORG_NAME" -t developers --status-check

# 9. Initialize dbci-tools repository
echo ""
echo "9. Initializing dbci-tools repository..."
dt git repo init dbci-tools -o "$ORG_NAME" -d "$DIR/../projects/dbci-tools"
dt git repo init etl-framework -o "$ORG_NAME" -d "$DIR/../projects/etl-framework"

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
echo "  Repos: dbci-tools, demo-db, demo-etl"
echo ""
echo "Next steps:"
echo "  - Browse Gitea org: http://localhost:3000/$ORG_NAME"
echo "  - Clone repos: dt git clone demo-app --org $ORG_NAME --dest ~/Local"
echo "  - Init projects: dt p maven ~/Local/my-project"
echo "  - Teardown: dt env down"
echo ""
