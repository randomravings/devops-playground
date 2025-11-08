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

def get_config_file(project_root: pathlib.Path):
    """Get the sqlfluff config file path from project root"""
    return project_root / ".sqlfluff"

def build_schema(project_root: pathlib.Path) -> pathlib.Path:
    """
    Build schema by generating HCL from source SQL files using Atlas.
    
    Returns: hcl_file path
    """
    print("Building schema...")
    
    source_dir = project_root / "db" / "schema"
    target_dir = project_root / "target"
    hcl_output_file = target_dir / "schema.hcl"
    
    if not source_dir.exists():
        print(f"Error: Source directory does not exist: {source_dir}")
        sys.exit(1)
    
    # Ensure target directory exists
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Use ATLAS_DEV_URL env var if set, otherwise use docker://
    dev_url = os.getenv("ATLAS_DEV_URL", "docker://postgres/15/dev?search_path=public")
    
    # Generate HCL from source SQL files
    print(f"[build] Generating HCL schema from {source_dir}...")
    print(f"[build] Using dev database: {dev_url}")
    result = subprocess.run([
        "atlas", "schema", "inspect",
        "--url", f"file://{source_dir.absolute()}",
        "--dev-url", dev_url
    ], capture_output=True, text=True, check=False)
    
    if result.returncode != 0:
        print(f"[build] Error: Atlas inspect failed")
        print(result.stderr)
        sys.exit(1)
    
    hcl_output_file.write_text(result.stdout, encoding="utf-8")
    print(f"[build] ✅ Schema HCL: {hcl_output_file}")
    
    return hcl_output_file

def lint_schema(project_root: pathlib.Path):
    """
    Run SQL linting on source schema files using SQLFluff.
    Lints the original SQL files directly.
    """
    print("Linting schema...")
    
    source_dir = project_root / "db" / "schema"
    config_file = get_config_file(project_root)
    
    if not source_dir.exists():
        print(f"Error: Source directory does not exist: {source_dir}")
        sys.exit(1)
    
    # Run SQLFluff on source files
    print(f"[lint] Running SQLFluff on {source_dir}...")
    result = subprocess.run([
        "dbci-lint",
        "--config", str(config_file),
        "--dialect", "postgres",
        str(source_dir)
    ], check=False)
    
    if result.returncode == 0:
        print("[lint] ✅ All linting checks passed")
    else:
        print("[lint] ⚠️  Linting found issues (see above)")
    
    return result.returncode

def guard_schema(project_root: pathlib.Path):
    """Run schema validation guard"""
    print("Running guard...")
    
    # Guard checks target/atlas.migration.schema-changes.json in project root
    subprocess.run(["dbci-guard"], cwd=str(project_root), check=True)

def install_dbci_tools():
    """
    Install and setup the DBCI tools environment.
    Creates .venv and installs dependencies for the dbci-tools framework.
    """
    print("Installing DBCI tools environment...")
    
    # Get the dbci-tools directory (where this package is located)
    dbci_dir = get_dbci_dir()
    venv_dir = dbci_dir / ".venv"
    
    print(f"DBCI tools directory: {dbci_dir}")
    
    # Create virtual environment if it doesn't exist
    if not venv_dir.exists():
        print(f"Creating virtual environment at {venv_dir}...")
        subprocess.run([
            sys.executable, "-m", "venv", str(venv_dir)
        ], check=True)
        print("✅ Virtual environment created")
    else:
        print("✅ Virtual environment already exists")
    
    # Determine pip executable path
    if os.name == 'nt':  # Windows
        pip_exe = venv_dir / "Scripts" / "pip"
    else:  # Unix/Linux/macOS
        pip_exe = venv_dir / "bin" / "pip"
    
    # Upgrade pip
    print("Upgrading pip...")
    subprocess.run([str(pip_exe), "install", "--upgrade", "pip"], check=True)
    
    # Install the package in development mode (this installs dependencies from pyproject.toml)
    print("Installing dbci-tools in development mode...")
    subprocess.run([str(pip_exe), "install", "-e", str(dbci_dir)], check=True)
    print("✅ dbci-tools installed in development mode")
    
    # Check for external dependencies
    print("\nChecking external dependencies...")
    
    # Check for Atlas CLI
    atlas_check = subprocess.run(["which", "atlas"], capture_output=True)
    if atlas_check.returncode != 0:
        print("⚠️  Warning: Atlas CLI not found in PATH")
        print("   Install from: https://atlasgo.io/getting-started")
    else:
        atlas_version = subprocess.run(["atlas", "version"], capture_output=True, text=True)
        print(f"✅ Atlas CLI found: {atlas_version.stdout.strip()}")
    
    print("")
    print("DBCI tools installation:")
    print(f"  Tools directory: {dbci_dir}")
    print(f"  Virtual env:     {venv_dir}")
    print(f"  Dependencies:    pyproject.toml")
    print("")
    print("[install] ✅ Installation complete")

def diff_schema(project_root: pathlib.Path):
    """Compare current schema with main branch"""
    print("Running diff...")
    
    source_dir = project_root / "db" / "schema"
    target_dir = project_root / "target"
    
    # Ensure target directory exists
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Ensure source directory exists
    if not source_dir.exists():
        print(f"Error: Source directory does not exist: {source_dir}")
        sys.exit(1)
    
    # Create temporary directory for main branch checkout
    with tempfile.TemporaryDirectory(prefix="dbci-diff-") as tmp_dir:
        tmp_path = pathlib.Path(tmp_dir)
        main_schema_dir = tmp_path / "main" / "db" / "schema"
        main_hcl = target_dir / "main.hcl"
        
        print(f"Using temporary directory: {tmp_dir}")
        
        # Get main branch schema files
        print("Getting schema from origin/main...")
        result = subprocess.run([
            "dbci-git-normalize",
            str(project_root),
            "-o", str(main_schema_dir),
            "-s", "db/schema",
            "-b", "origin/main"
        ], check=False, capture_output=False, text=True)  # Show git-normalize output for debugging
        
        # Handle empty main branch
        if result.returncode != 0 or not list(main_schema_dir.glob("*.sql")):
            if result.returncode != 0:
                print(f"⚠️  dbci-git-normalize failed with exit code {result.returncode}")
            print("ℹ️  Info: No schema found in origin/main (branch may be empty)")
            print("    Comparing against empty schema...")
            main_schema_dir.mkdir(parents=True, exist_ok=True)
            # Create empty main.hcl for consistency
            main_hcl.write_text('schema "public" {\n  comment = "standard public schema"\n}\n', encoding="utf-8")
            print(f"[diff] ✅ Empty main.hcl saved: {main_hcl}")
        else:
            # Generate HCL from main branch for inspection
            print("[diff] Generating main.hcl for inspection...")
            
            # Use ATLAS_DEV_URL env var if set, otherwise use docker://
            dev_url = os.getenv("ATLAS_DEV_URL", "docker://postgres/15/dev?search_path=public")
            
            inspect_result = subprocess.run([
                "atlas", "schema", "inspect",
                "--url", f"file://{main_schema_dir.absolute()}",
                "--dev-url", dev_url
            ], capture_output=True, text=True, check=False)
            
            if inspect_result.returncode == 0:
                main_hcl.write_text(inspect_result.stdout, encoding="utf-8")
                print(f"[diff] ✅ Main branch HCL saved: {main_hcl}")
            else:
                print(f"[diff] Warning: Could not generate main.hcl from main branch")
                main_hcl.write_text('schema "public" {\n  comment = "standard public schema"\n}\n', encoding="utf-8")
        
        # Compare SQL directories using Atlas diff
        print(f"[diff] Comparing schemas using Atlas...")
        print(f"[diff]   FROM: {main_schema_dir}")
        print(f"[diff]   TO:   {source_dir}")
        
        subprocess.run([
            "dbci-diff",
            str(main_schema_dir),
            str(source_dir),
            "-o", str(target_dir / "atlas.migration.sql"),
            "--schema-analysis"
        ], check=True)
    
    print(f"Diff results saved to {target_dir}/")

def run_all(project_root: pathlib.Path):
    """Run all DBCI operations in sequence"""
    lint_schema(project_root)  # LINT first - operates on source files only
    build_schema(project_root)
    diff_schema(project_root)
    guard_schema(project_root)  # GUARD must run after DIFF to check migration changes

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="DBCI - Database Continuous Integration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Operations:
  INSTALL - Install and setup DBCI tools environment (.venv and dependencies)
  BUILD   - Generate HCL schema from source SQL files using Atlas
  LINT    - Run SQLFluff linting on source SQL files
  DIFF    - Compare current schema with main branch using Atlas, save main.hcl
  GUARD   - Run schema validation checks
  ALL     - Execute all operations in sequence (LINT → BUILD → DIFF → GUARD)

Examples:
  dbci INSTALL                    # Install DBCI tools environment
  dbci BUILD /path/to/project
  dbci LINT /path/to/project  
  dbci ALL /path/to/project
        """
    )
    
    parser.add_argument(
        "operation",
        choices=["INSTALL", "BUILD", "LINT", "DIFF", "GUARD", "ALL"],
        help="Operation to perform"
    )
    
    parser.add_argument(
        "project_root",
        type=pathlib.Path,
        nargs="?",
        help="Path to the project root directory (not used for INSTALL)"
    )
    
    args = parser.parse_args()
    
    # Handle INSTALL separately (doesn't need project_root)
    if args.operation == "INSTALL":
        try:
            install_dbci_tools()
        except subprocess.CalledProcessError as e:
            print(f"Error: Installation failed with exit code {e.returncode}", file=sys.stderr)
            sys.exit(e.returncode)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return
    
    # For all other operations, validate project_root
    if args.project_root is None:
        print(f"Error: {args.operation} operation requires a project path", file=sys.stderr)
        sys.exit(1)
    
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
            lint_schema(project_root)
        elif args.operation == "DIFF":
            diff_schema(project_root)
        elif args.operation == "GUARD":
            guard_schema(project_root)
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