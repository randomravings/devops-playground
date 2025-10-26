#!/bin/bash
#
# Example: Using dbci-tools diff.py with Atlas CLI
#
# This script demonstrates how to use the Atlas-powered schema diff tool
# to compare database schemas and generate migration SQL.
#

set -e

echo "=== DBCI Tools - Schema Diff Example ==="
echo ""

# Prerequisites check
if ! command -v atlas &> /dev/null; then
    echo "ERROR: Atlas CLI not found. Install with:"
    echo "  curl -sSf https://atlasgo.sh | sh"
    exit 1
fi

if ! python3 -c "import dbci_tools" 2>/dev/null; then
    echo "ERROR: dbci_tools not installed. Run from project_templates/dbci-tools:"
    echo "  pip install -e ."
    exit 1
fi

# Example 1: Basic schema comparison
echo "Example 1: Basic Schema Comparison"
echo "-----------------------------------"

python3 -m dbci_tools.diff \
    /tmp/schema_v1 \
    /tmp/schema_v2 \
    --output /tmp/example-migration.sql

echo ""
echo "Migration SQL saved to: /tmp/example-migration.sql"
echo ""

# Example 2: With detailed analysis
echo "Example 2: Schema Comparison with Analysis"
echo "-------------------------------------------"

python3 -m dbci_tools.diff \
    /tmp/schema_v1 \
    /tmp/schema_v2 \
    --output /tmp/example-with-analysis.sql \
    --schema-analysis

echo ""
echo "Files generated:"
echo "  - /tmp/example-with-analysis.sql (migration SQL)"
echo "  - /tmp/example-with-analysis.schema-report.md (human-readable report)"
echo "  - /tmp/example-with-analysis.schema-changes.json (structured data)"
echo ""

# Example 3: Guard against drops
echo "Example 3: Fail on Destructive Changes"
echo "---------------------------------------"

if python3 -m dbci_tools.diff \
    /tmp/schema_v2 \
    /tmp/schema_v1 \
    --fail-on-drops; then
    echo "✅ No drops detected"
else
    echo "❌ Drops detected - pipeline should fail"
fi

echo ""

# Example 4: Using PostgreSQL dev database (requires Docker)
echo "Example 4: PostgreSQL-specific Syntax"
echo "--------------------------------------"
echo "For PostgreSQL-specific features, use Docker dev database:"
echo ""
echo "  python3 -m dbci_tools.diff \\"
echo "      schema_v1/ \\"
echo "      schema_v2/ \\"
echo "      --dev-url 'docker://postgres/15/dev?search_path=public'"
echo ""

# Example 5: Integration with Git
echo "Example 5: Compare Current Branch vs Main"
echo "------------------------------------------"
echo "In a CI/CD pipeline, compare schemas across branches:"
echo ""
echo "  # Checkout main branch schema"
echo "  git show main:db/schema | tar -xf - -C /tmp/main-schema"
echo ""
echo "  # Compare with current branch"
echo "  python3 -m dbci_tools.diff \\"
echo "      /tmp/main-schema \\"
echo "      db/schema \\"
echo "      --schema-analysis \\"
echo "      --fail-on-drops"
echo ""

echo "=== Examples Complete ==="
