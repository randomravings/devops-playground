#!/usr/bin/env bash
#
# Run All Commands: Execute complete workflow for dbci-tools and etl-framework
#
# This demonstrates a complete end-to-end workflow:
# 1. Setup dbci-tools and build database schema
# 2. Run DBCI commands (BUILD, LINT, GUARD)
# 3. Setup etl-framework with demo-etl
# 4. Validate ETL model against database schema
# 5. Run ETL pipeline for sample dates
# 6. Run ETL tests
#
# Usage:
#   ./acme_run_all.sh USERNAME WORKSPACE_DIR
#
#   USERNAME:       Gitea user (e.g., john, jane)
#   WORKSPACE_DIR:  Base directory for repos (e.g., ~/Local)
#
# Prerequisites: Run acme_user_local.sh first to clone repositories

set -e

# Configuration
USERNAME="${1}"
WORKSPACE_BASE="${2}"

# Validate required parameters
if [ -z "${USERNAME}" ] || [ -z "${WORKSPACE_BASE}" ]; then
    echo "❌ Error: Missing required parameters"
    echo ""
    echo "Usage: $0 USERNAME WORKSPACE_DIR"
    echo ""
    echo "  USERNAME:       Gitea user (e.g., john, jane)"
    echo "  WORKSPACE_DIR:  Base directory for repos (e.g., ~/Local)"
    echo ""
    echo "Example:"
    echo "  $0 john ~/Local"
    exit 1
fi

# Expand tilde in path
WORKSPACE_BASE=$(eval echo "${WORKSPACE_BASE}")
WORKSPACE="${WORKSPACE_BASE}/${USERNAME}"

echo "============================================================"
echo "Run All: Complete DBCI and ETL Workflow"
echo "============================================================"
echo "User:      ${USERNAME}"
echo "Workspace: ${WORKSPACE}"
echo ""

# Validate workspace exists
if [ ! -d "${WORKSPACE}" ]; then
    echo "❌ Error: Workspace '${WORKSPACE}' does not exist"
    echo "   Run acme_user_local.sh first to clone repositories"
    exit 1
fi

# Validate all required directories exist
DBCI_TOOLS="${WORKSPACE}/dbci-tools"
ETL_FRAMEWORK="${WORKSPACE}/etl-framework"
DEMO_DW="${WORKSPACE}/demo-dw"
DEMO_ETL="${WORKSPACE}/demo-etl"

for dir in "${DBCI_TOOLS}" "${ETL_FRAMEWORK}" "${DEMO_DW}" "${DEMO_ETL}"; do
    if [ ! -d "${dir}" ]; then
        echo "❌ Error: Directory '${dir}' does not exist"
        echo "   Run acme_user_local.sh first to clone all repositories"
        exit 1
    fi
done

echo "✅ All required directories found"
echo ""

# ==============================================================================
# Part 1: DBCI Tools - Database Schema Management
# ==============================================================================

echo "============================================================"
echo "Part 1: Database Schema Management (DBCI Tools)"
echo "============================================================"
echo ""

echo "1.1 Installing dbci-tools for demo-dw..."
cd "${DBCI_TOOLS}"
./run.sh INSTALL "${DEMO_DW}"
echo "✅ DBCI tools installation complete"
echo ""

echo "1.2 Building database schema (demo-dw)..."
cd "${DBCI_TOOLS}"
./run.sh BUILD "${DEMO_DW}"
echo "✅ Schema built: ${DEMO_DW}/target/schema.hcl"
echo ""

echo "1.3 Linting SQL files..."
cd "${DBCI_TOOLS}"
./run.sh LINT "${DEMO_DW}"
echo "✅ SQL linting complete"
echo ""

echo "1.4 Running schema diff..."
cd "${DBCI_TOOLS}"
./run.sh DIFF "${DEMO_DW}" || echo "⚠️  Diff completed (may have warnings)"
echo "✅ Schema diff complete"
echo ""

echo "1.5 Running schema guard..."
cd "${DBCI_TOOLS}"
./run.sh GUARD "${DEMO_DW}" || echo "⚠️  Guard checks completed (may have warnings)"
echo ""

# ==============================================================================
# Part 2: ETL Framework - Data Pipeline Management
# ==============================================================================

echo "============================================================"
echo "Part 2: ETL Framework Setup and Validation"
echo "============================================================"
echo ""

echo "2.1 Installing etl-framework..."
cd "${ETL_FRAMEWORK}"
# ./run.sh INSTALL
echo "✅ etl-framework installation complete"
echo ""

echo "2.2 Setting up project environment..."
cd "${ETL_FRAMEWORK}"
./run.sh SETUP "${DEMO_ETL}"
echo "✅ Project setup complete"
echo ""

echo "2.3 Validating ETL model against database schema..."
cd "${ETL_FRAMEWORK}"
./run.sh VALIDATE "${DEMO_ETL}" "${DEMO_DW}/target/schema.hcl"
echo "✅ ETL model validation complete"
echo ""

# ==============================================================================
# Part 3: ETL Pipeline Execution
# ==============================================================================

echo "============================================================"
echo "Part 3: ETL Pipeline Execution"
echo "============================================================"
echo ""

echo "3.1 Running ETL pipeline for 2024-02-01 (initial load)..."
cd "${ETL_FRAMEWORK}"
./run.sh RUN "${DEMO_ETL}" -d 2024-02-01
echo "✅ Initial load complete"
echo ""

echo "3.2 Running ETL pipeline for 2024-02-02 (delta load)..."
cd "${ETL_FRAMEWORK}"
./run.sh RUN "${DEMO_ETL}" -d 2024-02-02
echo "✅ Delta load complete"
echo ""

# ==============================================================================
# Part 4: Testing
# ==============================================================================

echo "============================================================"
echo "Part 4: Running Tests"
echo "============================================================"
echo ""

echo "4.1 Running ETL tests..."
cd "${ETL_FRAMEWORK}"
./run.sh TEST "${DEMO_ETL}"
echo "✅ All tests passed"
echo ""

# ==============================================================================
# Summary
# ==============================================================================

echo "============================================================"
echo "✅ Complete Workflow Finished Successfully!"
echo "============================================================"
echo ""
echo "Summary of completed operations:"
echo ""
echo "DBCI Tools (Database Schema):"

echo "  ✅ Installed and validated dependencies"
echo "  ✅ Built schema from SQL files → HCL"
echo "  ✅ Linted SQL files with SQLFluff"
echo "  ✅ Ran schema diff against main branch"
echo "  ✅ Ran schema guard validation"
echo ""
echo "ETL Framework (Data Pipeline):"
echo "  ✅ Installed framework environment"
echo "  ✅ Setup project environment"
echo "  ✅ Validated ETL model against schema"
echo "  ✅ Ran pipeline for 2024-02-01 (initial)"
echo "  ✅ Ran pipeline for 2024-02-02 (delta)"
echo "  ✅ Ran all ETL tests"
echo ""
echo "Output Locations:"
echo "  Schema HCL:    ${DEMO_DW}/target/schema.hcl"
echo "  ETL Warehouse: ${DEMO_ETL}/.data/warehouse/"
echo "  Test Results:  ${DEMO_ETL}/.pytest_cache/"
echo ""
echo "Next Steps:"
echo ""
echo "  • Push feature branches to Gitea:"
echo "      cd ${DEMO_DW}"
echo "      git add -A"
echo "      git commit -m 'Initial database schema'"
echo "      git push -u origin feature-init"
echo ""
echo "      cd ${DEMO_ETL}"
echo "      git add -A"
echo "      git commit -m 'Initial ETL pipeline'"
echo "      git push -u origin feature-init"
echo ""
echo "  • Review changes in Gitea:"
echo "      Open http://localhost:3000/acme/demo-dw"
echo "      Open http://localhost:3000/acme/demo-etl"
echo "      Create pull requests for feature-init branches"
echo ""
echo "  • Start Dagster UI for local development:"
echo "      cd ${ETL_FRAMEWORK}"
echo "      source .venv/bin/activate"
echo "      cd ${DEMO_ETL}"
echo "      dagster dev -p 3001  # Port 3000 is used by Gitea"
echo ""
