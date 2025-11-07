#!/usr/bin/env python3
"""
ETL Framework CLI - Simplified interface matching dbci-tools pattern
Commands: SETUP, RUN, TEST, VALIDATE
"""
import argparse
import pathlib
import subprocess
import sys
import os


def setup_project(project_root: pathlib.Path, warehouse: str = "csv"):
    """Setup ETL project environment"""
    print(f"Setting up ETL project at {project_root}...")
    
    framework_path = str(pathlib.Path(__file__).parent.parent)
    
    # Check if project has source_model.yaml
    source_model = project_root / "source_model.yaml"
    if not source_model.exists():
        # Try subdirectory (e.g., demo_etl/source_model.yaml)
        possible_dirs = [d for d in project_root.iterdir() if d.is_dir() and not d.name.startswith('.')]
        for subdir in possible_dirs:
            if (subdir / "source_model.yaml").exists():
                source_model = subdir / "source_model.yaml"
                break
    
    if not source_model.exists():
        print(f"✗ Error: source_model.yaml not found in {project_root}")
        sys.exit(1)
    
    print(f"[setup] Found source model: {source_model}")
    print(f"[setup] Warehouse type: {warehouse}")
    
    # Use the standalone setup script
    from .setup_standalone import setup_environment
    
    setup_environment(
        project_dir=str(project_root),
        framework_path=framework_path,
        warehouse_type=warehouse,
        start_ui=False
    )
    
    print(f"[setup] ✅ Project setup complete")


def run_pipeline(project_root: pathlib.Path, date: str):
    """Run ETL pipeline"""
    print(f"Running ETL pipeline for {project_root}...")
    
    # Check if venv exists
    venv_path = project_root / ".venv"
    if not venv_path.exists():
        print(f"✗ Error: Virtual environment not found at {venv_path}")
        print(f"  Run: etl SETUP {project_root}")
        sys.exit(1)
    
    print(f"[run] Date: {date}")
    print("")
    
    # Use the commands module to run the pipeline
    python_exe = venv_path / "bin" / "python"
    result = subprocess.run(
        [
            str(python_exe), "-m", "dagster_etl_framework.commands",
            "run",
            "--project-dir", str(project_root),
            "-d", date
        ],
        cwd=str(project_root),
        check=False,
        # Explicitly inherit stdout/stderr to show Dagster output
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    
    print("")
    if result.returncode == 0:
        print(f"[run] ✅ Pipeline completed")
    else:
        print(f"[run] ⚠️  Pipeline failed")
        sys.exit(result.returncode)


def test_project(project_root: pathlib.Path):
    """Run tests for ETL project"""
    print(f"Running tests for {project_root}...")
    
    # Check if venv exists
    venv_path = project_root / ".venv"
    if not venv_path.exists():
        print(f"✗ Error: Virtual environment not found at {venv_path}")
        print(f"  Run: etl SETUP {project_root}")
        sys.exit(1)
    
    # Run pytest
    python_exe = venv_path / "bin" / "python"
    result = subprocess.run(
        [str(python_exe), "-m", "pytest", "-v"],
        cwd=str(project_root),
        check=False
    )
    
    if result.returncode == 0:
        print(f"[test] ✅ All tests passed")
    else:
        print(f"[test] ⚠️  Some tests failed")
        sys.exit(result.returncode)


def validate_model(project_root: pathlib.Path, hcl_file: pathlib.Path = None):
    """Validate source model against database schema (HCL)"""
    print(f"Validating model for {project_root}...")
    
    # Auto-detect HCL file if not provided
    if not hcl_file:
        # Look for demo-dw/target/schema.hcl
        parent = project_root.parent
        demo_dw_hcl = parent / "demo-dw" / "target" / "schema.hcl"
        if demo_dw_hcl.exists():
            hcl_file = demo_dw_hcl
        else:
            print("✗ Error: HCL schema file not found")
            print(f"  Tried: {demo_dw_hcl}")
            print(f"  Usage: etl VALIDATE {project_root} /path/to/schema.hcl")
            sys.exit(1)
    
    if not hcl_file.exists():
        print(f"✗ Error: HCL file not found: {hcl_file}")
        sys.exit(1)
    
    print(f"[validate] HCL schema: {hcl_file}")
    print("")
    
    # Check if venv exists
    venv_path = project_root / ".venv"
    if not venv_path.exists():
        print(f"✗ Error: Virtual environment not found at {venv_path}")
        print(f"  Run: etl SETUP {project_root}")
        sys.exit(1)
    
    # Run validation using the validate module
    python_exe = venv_path / "bin" / "python"
    result = subprocess.run(
        [
            str(python_exe), "-m", "dagster_etl_framework.commands",
            "validate",
            "--project-dir", str(project_root),
            "--hcl-file", str(hcl_file)
        ],
        cwd=str(project_root),
        check=False,
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    
    print("")
    if result.returncode == 0:
        print(f"[validate] ✅ Model validation passed")
    else:
        print(f"[validate] ⚠️  Model validation failed")
        sys.exit(result.returncode)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="ETL Framework - Simplified ETL project management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Operations:
  SETUP    - Setup project environment (creates .venv, installs deps)
  RUN      - Run ETL pipeline for specific date
  TEST     - Run project tests
  VALIDATE - Validate source model against database schema (HCL)

Examples:
  # Setup with default CSV warehouse
  etl SETUP /path/to/demo-etl
  
  # Setup with Postgres warehouse
  etl SETUP /path/to/demo-etl -w postgres
  
  # Run pipeline for specific date
  etl RUN /path/to/demo-etl -d 2024-02-01
  
  # Run tests
  etl TEST /path/to/demo-etl
  
  # Validate (auto-detects ../demo-dw/target/schema.hcl)
  etl VALIDATE /path/to/demo-etl
  
  # Validate with explicit HCL path
  etl VALIDATE /path/to/demo-etl /path/to/schema.hcl
        """
    )
    
    parser.add_argument(
        "operation",
        choices=["SETUP", "RUN", "TEST", "VALIDATE"],
        help="Operation to perform"
    )
    
    parser.add_argument(
        "project_root",
        type=pathlib.Path,
        help="Path to the ETL project root directory"
    )
    
    # Operation-specific arguments
    parser.add_argument(
        "-w", "--warehouse",
        default="csv",
        choices=["csv", "postgres"],
        help="Warehouse type for SETUP (default: csv)"
    )
    
    parser.add_argument(
        "-d", "--date",
        help="Date in YYYY-MM-DD format for RUN operation"
    )
    
    parser.add_argument(
        "hcl_file",
        nargs="?",
        type=pathlib.Path,
        help="Path to HCL schema file for VALIDATE (optional, auto-detects)"
    )
    
    args = parser.parse_args()
    
    # Validate project root exists
    if not args.project_root.exists():
        print(f"✗ Error: Project root directory does not exist: {args.project_root}", file=sys.stderr)
        sys.exit(1)
    
    # Make project root absolute
    project_root = args.project_root.resolve()
    
    try:
        if args.operation == "SETUP":
            setup_project(project_root, args.warehouse)
            
        elif args.operation == "RUN":
            if not args.date:
                print("✗ Error: --date/-d required for RUN operation", file=sys.stderr)
                print("  Example: etl RUN /path/to/demo-etl -d 2024-02-01", file=sys.stderr)
                sys.exit(1)
            run_pipeline(project_root, args.date)
            
        elif args.operation == "TEST":
            test_project(project_root)
            
        elif args.operation == "VALIDATE":
            validate_model(project_root, args.hcl_file)
            
    except subprocess.CalledProcessError as e:
        print(f"✗ Error: Command failed with exit code {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode)
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
