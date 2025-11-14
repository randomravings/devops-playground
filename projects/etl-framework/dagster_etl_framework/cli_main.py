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


def install_framework():
    """
    Install and setup the ETL framework environment.
    Creates .venv and installs dependencies for the etl-framework.
    """
    print("Installing ETL framework environment...")
    
    # Get the etl-framework directory (where this package is located) 
    framework_path = pathlib.Path(__file__).parent.parent
    venv_dir = framework_path / ".venv"
    requirements_file = framework_path / "pyproject.toml"
    
    print(f"ETL framework directory: {framework_path}")
    
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
    
    # Install the framework in development mode
    print("Installing etl-framework in development mode...")
    subprocess.run([str(pip_exe), "install", "-e", str(framework_path)], check=True)
    print("✅ etl-framework installed in development mode")
    
    # Check for external dependencies
    print("\nChecking external dependencies...")
    
    # Check for Python version
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    if sys.version_info >= (3, 12):
        print(f"✅ Python {python_version} found")
    else:
        print(f"⚠️  Warning: Python {python_version} found, 3.12+ recommended")
    
    print("")
    print("ETL framework installation:")
    print(f"  Framework directory: {framework_path}")
    print(f"  Virtual env:         {venv_dir}")
    print(f"  Project config:      {requirements_file}")
    print("")
    print("[install] ✅ Installation complete")


def setup_project(project_root: pathlib.Path, warehouse: str = "sqlite"):
    """Setup ETL project environment"""
    print(f"Setting up ETL project at {project_root}...")
    
    framework_path = pathlib.Path(__file__).parent.parent
    framework_venv = framework_path / ".venv"
    
    # Check if framework has been installed first
    if not framework_venv.exists():
        print(f"✗ Error: ETL framework not installed")
        print(f"  Framework directory: {framework_path}")
        print(f"  Missing: {framework_venv}")
        print(f"  Run: etl INSTALL")
        sys.exit(1)
    
    print(f"[setup] ✅ Framework installed at: {framework_path}")
    
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
    
    # Use the standalone setup script - explicitly don't start UI
    from .setup_standalone import setup_environment
    
    setup_environment(
        project_dir=str(project_root),
        framework_path=str(framework_path),
        warehouse_type=warehouse,
        start_ui=False
    )
    
    print(f"[setup] ✅ Project setup complete")


def launch_ui(project_root: pathlib.Path, port: int = 3001):
    """Launch Dagster UI for project"""
    print(f"Launching Dagster UI for {project_root}...")
    
    # Check if venv exists
    venv_path = project_root / ".venv"
    if not venv_path.exists():
        print(f"✗ Error: Virtual environment not found at {venv_path}")
        print(f"  Run: etl SETUP {project_root}")
        sys.exit(1)
    
    print(f"[ui] Port: {port}")
    print("")
    
    # Use the setup module to launch UI
    from .setup import SetupManager
    setup_manager = SetupManager(str(project_root))
    
    try:
        actual_port = setup_manager.launch_dagster_ui(port)
        print(f"[ui] ✅ Dagster UI running at http://localhost:{actual_port}")
        print("[ui] Press Ctrl+C to stop")
        
        # Keep running until interrupted
        import time
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print(f"\n[ui] Stopping Dagster UI...")
        print("[ui] ✅ UI stopped")
    except Exception as e:
        print(f"[ui] ⚠️  Error launching UI: {e}")
        sys.exit(1)


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
    
    # Use the commands module to run tests (loads .env file)
    python_exe = venv_path / "bin" / "python"
    result = subprocess.run(
        [
            str(python_exe), "-m", "dagster_etl_framework.commands",
            "test",
            "--project-dir", str(project_root)
        ],
        cwd=str(project_root),
        check=False,
        # Explicitly inherit stdout/stderr
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    
    if result.returncode == 0:
        print(f"[test] ✅ All tests passed")
    else:
        print(f"[test] ⚠️  Some tests failed")
        sys.exit(result.returncode)


def validate_model(project_root: pathlib.Path, hcl_file: pathlib.Path):
    """Validate source model against database schema (HCL)"""
    print(f"Validating model for {project_root}...")
    
    # Validate HCL file is provided and exists
    if not hcl_file:
        print("✗ Error: HCL schema file path is required")
        print("")
        print("Usage:")
        print(f"  etl VALIDATE {project_root} /path/to/schema.hcl")
        print(f"  ./run.sh VALIDATE . /path/to/schema.hcl")
        print("")
        print("Example:")
        print(f"  etl VALIDATE {project_root} ../demo-dw/target/schema.hcl")
        sys.exit(1)
    
    if not hcl_file.exists():
        print(f"✗ Error: HCL file not found: {hcl_file}")
        print("")
        print("Please ensure the database schema has been built:")
        print("  cd /path/to/database-project")
        print("  dbci BUILD .")
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
  INSTALL  - Install and setup ETL framework environment (.venv and dependencies)
  SETUP    - Setup project environment (creates .venv, installs deps)
  RUN      - Run ETL pipeline for specific date
  TEST     - Run project tests
  VALIDATE - Validate source model against database schema (HCL)
  UI       - Launch Dagster UI for project

Examples:
  # Install ETL framework environment
  etl INSTALL
  
  # Setup with default SQLite warehouse
  etl SETUP /path/to/demo-etl
  
  # Setup with Postgres warehouse
  etl SETUP /path/to/demo-etl -w postgres
  
  # Run pipeline for specific date
  etl RUN /path/to/demo-etl -d 2024-02-01
  
  # Run tests
  etl TEST /path/to/demo-etl
  
  # Validate (requires explicit HCL path)
  etl VALIDATE /path/to/demo-etl /path/to/schema.hcl
  
  # Launch Dagster UI
  etl UI /path/to/demo-etl
        """
    )
    
    parser.add_argument(
        "operation",
        choices=["INSTALL", "SETUP", "RUN", "TEST", "VALIDATE", "UI"],
        metavar="OPERATION",
        help="""Operation to perform:
  INSTALL  - Install ETL framework environment (.venv and dependencies)
  SETUP    - Setup project environment (creates .venv, installs project deps)
  RUN      - Run ETL pipeline for specific date partition
  TEST     - Run project tests using pytest
  VALIDATE - Validate source_model.yaml against database schema (HCL file)
  UI       - Launch Dagster web UI for project"""
    )
    
    parser.add_argument(
        "project_root",
        type=pathlib.Path,
        nargs="?",
        metavar="PROJECT_PATH",
        help="Path to ETL project root directory (not required for INSTALL)"
    )
    
    parser.add_argument(
        "hcl_file",
        type=pathlib.Path,
        nargs="?",
        metavar="HCL_FILE",
        help="Path to database schema HCL file (required only for VALIDATE)"
    )
    
    # Operation-specific arguments
    parser.add_argument(
        "-w", "--warehouse",
        default="sqlite",
        choices=["sqlite", "postgres"],
        metavar="TYPE",
        help="Warehouse database type for SETUP operation (choices: sqlite, postgres; default: sqlite)"
    )
    
    parser.add_argument(
        "-d", "--date",
        metavar="YYYY-MM-DD",
        help="Date in YYYY-MM-DD format for RUN operation (e.g., 2024-02-01)"
    )
    
    parser.add_argument(
        "-p", "--port",
        type=int,
        default=3001,
        metavar="PORT",
        help="Port number for UI operation (default: 3001)"
    )
    
    args = parser.parse_args()
    
    # Handle INSTALL separately (doesn't need project_root)
    if args.operation == "INSTALL":
        try:
            install_framework()
        except subprocess.CalledProcessError as e:
            print(f"✗ Error: Installation failed with exit code {e.returncode}", file=sys.stderr)
            sys.exit(e.returncode)
        except Exception as e:
            print(f"✗ Error: {e}", file=sys.stderr)
            sys.exit(1)
        return
    
    # For all other operations, validate project_root
    if args.project_root is None:
        print(f"✗ Error: {args.operation} operation requires a project path", file=sys.stderr)
        sys.exit(1)
    
    # Validate project root exists
    if not args.project_root.exists():
        print(f"✗ Error: Project root directory does not exist: {args.project_root}", file=sys.stderr)
        sys.exit(1)
    
    # Make project root absolute
    project_root = args.project_root.resolve()
    
    try:
        if args.operation == "SETUP":
            setup_project(project_root, args.warehouse)
            
        elif args.operation == "UI":
            launch_ui(project_root, args.port)
            
        elif args.operation == "RUN":
            if not args.date:
                print("✗ Error: --date/-d required for RUN operation", file=sys.stderr)
                print("  Example: etl RUN /path/to/demo-etl -d 2024-02-01", file=sys.stderr)
                sys.exit(1)
            run_pipeline(project_root, args.date)
            
        elif args.operation == "TEST":
            test_project(project_root)
            
        elif args.operation == "VALIDATE":
            if not args.hcl_file:
                print("✗ Error: HCL schema file path required for VALIDATE operation", file=sys.stderr)
                print("  Usage: etl VALIDATE /path/to/project /path/to/schema.hcl", file=sys.stderr)
                print("  Example: etl VALIDATE . ../demo-dw/target/schema.hcl", file=sys.stderr)
                sys.exit(1)
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
