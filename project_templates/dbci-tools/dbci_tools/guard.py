#!/usr/bin/env python3
import sys, re, pathlib, argparse, json

def check_migration_changes():
    """Check Atlas migration changes for destructive operations."""
    changes_file = pathlib.Path("target/atlas.migration.schema-changes.json")
    if not changes_file.exists():
        # In CI/Jenkins context, this file MUST exist from DIFF stage
        # Return a special violation to fail the build
        return [(
            "missing_migration_file", 
            "atlas.migration.schema-changes.json not found - DIFF stage must run before GUARD"
        )]
    
    try:
        changes = json.loads(changes_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return [(
            "invalid_migration_file", 
            f"Could not parse {changes_file}: {e}"
        )]
    
    violations = []
    
    # Check for dropped tables
    dropped_tables = changes.get("tables", {}).get("dropped", [])
    if dropped_tables:
        violations.append(("dropped_tables", f"Dropping tables is destructive: {', '.join(dropped_tables)}"))
    
    # Check for dropped columns
    dropped_columns = changes.get("columns", {}).get("dropped", {})
    if dropped_columns:
        for table, columns in dropped_columns.items():
            violations.append(("dropped_columns", f"Dropping columns from {table} is destructive: {', '.join(columns)}"))
    
    return violations

def main():
    ap = argparse.ArgumentParser(description="Run DDL guard checks on Atlas migration changes")
    args = ap.parse_args()

    # Check Atlas migration changes (tables/columns dropped)
    violations = check_migration_changes()
    if violations:
        print("\n[ddl_guard] Atlas migration changes:")
        for name, msg in violations:
            print(f"  - {name}: {msg}")
        print("\n[ddl_guard] ❌ Guardrails failed.")
        return 1

    print("[ddl_guard] ✅ All checks passed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
