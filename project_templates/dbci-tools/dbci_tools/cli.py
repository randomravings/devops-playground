#!/usr/bin/env python3
"""
DBCI CLI - Database Continuous Integration Command Line Interface
Orchestrates all DBCI operations: BUILD, LINT, DIFF, GUARD, and ALL
"""
import argparse
import pathlib
import subprocess
import tempfile
import sys
import os

def get_dbci_dir():
    """Get the DBCI tools directory (where this script is located)"""
    return pathlib.Path(__file__).parent.parent

def get_config_file():
    """Get the sqlfluff config file path"""
    return get_dbci_dir() / ".sqlfluff"

def build_schema(project_root: pathlib.Path) -> pathlib.Path:
    """Build/normalize schema files"""
    print("Building project...")
    
    source_dir = project_root / "db" / "schema"
    output_dir = project_root / ".out" / "db" / "schema"
    
    # Run dbci-normalize
    subprocess.run([
        "dbci-normalize", 
        str(source_dir), 
        "--output", str(output_dir)
    ], check=True)
    
    return output_dir

def lint_schema(schema_dir: pathlib.Path):
    """Run SQL linting on schema files"""
    print("Running linting...")
    
    config_file = get_config_file()
    
    subprocess.run([
        "dbci-lint",
        "--config", str(config_file),
        "--dialect", "postgres",
        str(schema_dir)
    ], check=True)

def guard_schema():
    """Run schema validation guard"""
    print("Running guard...")
    
    subprocess.run(["dbci-guard"], check=True)

def diff_schema(project_root: pathlib.Path):
    """Compare current schema with main branch"""
    print("Running diff...")
    
    schema_dir = project_root / ".out" / "db" / "schema"
    out_dir = project_root / ".out"
    
    # Ensure we have current normalized files
    if not schema_dir.exists():
        print("Current schema not found, building first...")
        build_schema(project_root)
    
    # Create temporary directory for git checkout
    with tempfile.TemporaryDirectory(prefix="dbci-diff-") as tmp_dir:
        tmp_path = pathlib.Path(tmp_dir)
        main_out = tmp_path / "main" / "db" / "schema"
        
        print(f"Using temporary directory: {tmp_dir}")
        
        # Normalize main branch to temporary directory
        print("Getting schema from origin/main...")
        subprocess.run([
            "dbci-git-normalize",
            str(project_root),
            "-o", str(main_out),
            "-s", "db/schema",
            "-b", "origin/main"
        ], check=True)
        
        # Compare and output results to project .out directory
        subprocess.run([
            "dbci-diff",
            str(main_out),
            str(schema_dir),
            "-o", str(out_dir / "schema-changes.diff"),
            "--generate-script"
        ], check=True)
    
    print(f"Diff results saved to {out_dir}/")

def run_all(project_root: pathlib.Path):
    """Run all DBCI operations in sequence"""
    schema_dir = build_schema(project_root)
    lint_schema(schema_dir)
    guard_schema()
    diff_schema(project_root)

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="DBCI - Database Continuous Integration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Operations:
  BUILD  - Normalize SQL schema files from db/schema to .out/db/schema
  LINT   - Run SQL linting on normalized schema files  
  DIFF   - Compare current schema with main branch and generate change scripts
  GUARD  - Run schema validation checks
  ALL    - Execute all operations in sequence (BUILD → LINT → GUARD → DIFF)

Examples:
  dbci BUILD /path/to/project
  dbci LINT /path/to/project  
  dbci ALL /path/to/project
        """
    )
    
    parser.add_argument(
        "operation",
        choices=["BUILD", "LINT", "DIFF", "GUARD", "ALL"],
        help="Operation to perform"
    )
    
    parser.add_argument(
        "project_root",
        type=pathlib.Path,
        help="Path to the project root directory"
    )
    
    args = parser.parse_args()
    
    # Validate project root exists
    if not args.project_root.exists():
        print(f"Error: Project root directory does not exist: {args.project_root}", file=sys.stderr)
        sys.exit(1)
    
    # Make project root absolute
    project_root = args.project_root.resolve()
    
    try:
        if args.operation == "BUILD":
            build_schema(project_root)
        elif args.operation == "LINT":
            schema_dir = project_root / ".out" / "db" / "schema"
            if not schema_dir.exists():
                print("Schema directory not found, building first...")
                build_schema(project_root)
            lint_schema(schema_dir)
        elif args.operation == "DIFF":
            diff_schema(project_root)
        elif args.operation == "GUARD":
            guard_schema()
        elif args.operation == "ALL":
            run_all(project_root)
            
    except subprocess.CalledProcessError as e:
        print(f"Error: Command failed with exit code {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()