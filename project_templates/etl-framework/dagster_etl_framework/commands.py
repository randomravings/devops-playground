"""
Framework commands for running and testing ETL projects.
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path
from typing import List, Optional


def find_project_dir() -> Path:
    """
    Find the ETL project directory.
    
    Returns current directory, assuming we're called from the project.
    """
    return Path.cwd()


def find_venv(project_dir: Path) -> Optional[Path]:
    """
    Find the virtual environment for a project.
    
    Args:
        project_dir: Project directory path
        
    Returns:
        Path to venv or None if not found
    """
    venv = project_dir / ".venv"
    if venv.exists():
        return venv
    return None


def load_env_file(project_dir: Path) -> None:
    """
    Load environment variables from .env file in project directory.
    
    Args:
        project_dir: Project directory path
    """
    env_file = project_dir / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                # Parse KEY=VALUE
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # Only set if not already in environment
                    if key not in os.environ:
                        os.environ[key] = value


def run_command(args: List[str]) -> int:
    """
    Run ETL pipeline for a specific date.
    
    Args:
        args: Command arguments
        
    Returns:
        Exit code
    """
    parser = argparse.ArgumentParser(
        prog="etl-framework run",
        description="Run ETL pipeline for specific date",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  etl RUN /path/to/demo-etl -d 2024-02-01
  ./run.sh RUN . -d 2024-02-01
        """
    )
    
    parser.add_argument(
        "-i", "--input-dir",
        default="tests/data",
        help="Input directory (default: tests/data)"
    )
    parser.add_argument(
        "-d", "--date",
        required=True,
        help="Date YYYY-MM-DD"
    )
    parser.add_argument(
        "-o", "--output-dir",
        default=".data/warehouse",
        help="Output directory (default: .data/warehouse)"
    )
    parser.add_argument(
        "-p", "--project-dir",
        default=".",
        help="Project directory (default: .)"
    )
    
    parsed_args = parser.parse_args(args)
    
    # Resolve project directory and load .env file BEFORE validation
    project_dir = Path(parsed_args.project_dir).resolve()
    load_env_file(project_dir)
    
    # Validate date format
    import re
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', parsed_args.date):
        print(f"✗ Error: Invalid date format. Expected YYYY-MM-DD, got: {parsed_args.date}")
        return 1
    
    # Validate environment configuration for running pipeline
    warehouse_type = os.getenv("WAREHOUSE_TYPE")
    if not warehouse_type:
        print("✗ Error: WAREHOUSE_TYPE environment variable not set")
        print("")
        print("The pipeline requires warehouse configuration to run.")
        print("Please run setup first:")
        print(f"  etl-framework setup --project-dir {parsed_args.project_dir} --warehouse csv")
        print("")
        print("Or set environment variables manually:")
        print("  export WAREHOUSE_TYPE=csv")
        print("  export WAREHOUSE_PATH=.data/warehouse")
        return 1
    
    # Find venv
    venv = find_venv(project_dir)
    
    if not venv:
        print(f"✗ Error: Virtual environment not found at {project_dir}/.venv")
        print("  Please run 'etl-framework setup' first")
        return 1
    
    # Detect project name from pyproject.toml
    pyproject_path = project_dir / "pyproject.toml"
    if not pyproject_path.exists():
        print(f"✗ Error: pyproject.toml not found in {project_dir}")
        return 1
    
    # Read project name from pyproject.toml
    import re
    project_name = None
    with open(pyproject_path) as f:
        for line in f:
            match = re.match(r'name\s*=\s*["\']([^"\']+)["\']', line.strip())
            if match:
                project_name = match.group(1).replace('-', '_')
                break
    
    if not project_name:
        print(f"✗ Error: Could not determine project name from pyproject.toml")
        return 1
    
    # Activate venv and run using framework's CLI runner
    python_cmd = venv / "bin" / "python"
    
    # Import the project's assets dynamically
    # Construct Python command to run the partition
    cmd = [
        str(python_cmd),
        "-c",
        f"""
import sys
import os
sys.path.insert(0, '{project_dir}')
os.chdir('{project_dir}')

# Import project assets
from {project_name}.assets import all_assets

# Import framework runner
from dagster_etl_framework import run_partition, create_resources

# Set environment variables
os.environ["SOURCE_DATA_PATH"] = '{parsed_args.input_dir}'
os.environ["WAREHOUSE_PATH"] = '{parsed_args.output_dir}'

# Create resources and run
resources = create_resources(
    source_data_path='{parsed_args.input_dir}',
    dagster_storage_path='.dagster/storage'
)

exit_code = run_partition(all_assets, '{parsed_args.date}', resources, verbose=True)
sys.exit(exit_code)
"""
    ]
    
    print("=" * 60)
    print(f"Running ETL pipeline for date: {parsed_args.date}")
    print("=" * 60)
    print(f"Input:  {parsed_args.input_dir}")
    print(f"Output: {parsed_args.output_dir}")
    print("")
    
    try:
        result = subprocess.run(cmd, cwd=project_dir)
        return result.returncode
    except KeyboardInterrupt:
        print("\n✗ Pipeline interrupted by user")
        return 130


def test_command(args: List[str]) -> int:
    """
    Run tests for ETL project.
    
    Args:
        args: Command arguments (passed to pytest)
        
    Returns:
        Exit code
    """
    parser = argparse.ArgumentParser(
        prog="etl-framework test",
        description="Run tests for ETL project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  etl TEST /path/to/demo-etl
  ./run.sh TEST .
        """
    )
    
    parser.add_argument(
        "-p", "--project-dir",
        default=".",
        help="Project directory (default: .)"
    )
    parser.add_argument(
        "pytest_args",
        nargs="*",
        help="Arguments for pytest"
    )
    
    # Parse known args only, let pytest handle the rest
    parsed_args, unknown_args = parser.parse_known_args(args)
    
    # Combine pytest args
    pytest_args = parsed_args.pytest_args + unknown_args
    
    # Find project directory and venv
    project_dir = Path(parsed_args.project_dir).resolve()
    
    # Load .env file for test command as well
    load_env_file(project_dir)
    
    venv = find_venv(project_dir)
    
    if not venv:
        print(f"✗ Error: Virtual environment not found at {project_dir}/.venv")
        print("  Please run 'etl-framework setup' first")
        return 1
    
    # Check for tests directory
    tests_dir = project_dir / "tests"
    if not tests_dir.exists():
        print(f"✗ Error: tests/ directory not found in {project_dir}")
        return 1
    
    # Activate venv and run pytest
    pytest_cmd = venv / "bin" / "pytest"
    
    if not pytest_cmd.exists():
        print(f"✗ Error: pytest not found in virtual environment")
        print("  Please ensure pytest is installed")
        return 1
    
    # Build command
    cmd = [str(pytest_cmd)]
    
    # Add default args if none provided
    if not pytest_args:
        cmd.extend(["tests/", "-v", "--tb=short"])
    else:
        cmd.extend(pytest_args)
    
    print("=" * 60)
    print("Running ETL Tests")
    print("=" * 60)
    print("")
    
    try:
        result = subprocess.run(cmd, cwd=project_dir)
        return result.returncode
    except KeyboardInterrupt:
        print("\n✗ Tests interrupted by user")
        return 130


def validate_command(args: List[str]) -> int:
    """
    Validate ETL source model against database schema (HCL file).
    
    Args:
        args: Command arguments
        
    Returns:
        Exit code (0 if validation passes, 1 if errors found)
    """
    parser = argparse.ArgumentParser(
        prog="etl-framework validate",
        description="Validate ETL source model against database schema",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-detect HCL file (looks for ../demo-dw/target/schema.hcl)
  etl VALIDATE /path/to/demo-etl
  ./run.sh VALIDATE .
  
  # Explicit HCL file path
  etl VALIDATE /path/to/demo-etl /path/to/schema.hcl
  ./run.sh VALIDATE . ../demo-dw/target/schema.hcl
        """
    )
    
    parser.add_argument(
        "-p", "--project-dir",
        default=".",
        help="ETL project directory (default: .)"
    )
    parser.add_argument(
        "-s", "--source-model",
        help="Path to source model YAML file (default: auto-detect from project)"
    )
    parser.add_argument(
        "--hcl-file", "--hcl",
        required=True,
        help="Path to HCL schema file (from dbci-tools BUILD)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed validation results"
    )
    
    parsed_args = parser.parse_args(args)
    
    # Resolve paths
    project_dir = Path(parsed_args.project_dir).resolve()
    hcl_file = Path(parsed_args.hcl_file).resolve()
    
    # Validate HCL file exists
    if not hcl_file.exists():
        print(f"✗ Error: HCL file not found: {hcl_file}")
        print("")
        print("Please run dbci BUILD on the database project first:")
        print("  cd ../demo-dw")
        print("  dbci BUILD .")
        return 1
    
    # Find source model file
    if parsed_args.source_model:
        source_model_file = Path(parsed_args.source_model).resolve()
    else:
        # Auto-detect: look for source_model.yaml in project
        # Try to find the project package directory
        pyproject = project_dir / "pyproject.toml"
        if not pyproject.exists():
            print(f"✗ Error: pyproject.toml not found in {project_dir}")
            return 1
        
        # Read project name from pyproject.toml
        import re
        project_name = None
        with open(pyproject) as f:
            for line in f:
                match = re.match(r'name\s*=\s*["\']([^"\']+)["\']', line.strip())
                if match:
                    project_name = match.group(1).replace('-', '_')
                    break
        
        if not project_name:
            print(f"✗ Error: Could not determine project name from pyproject.toml")
            return 1
        
        # Look for source_model.yaml in project package
        source_model_file = project_dir / project_name / "source_model.yaml"
        if not source_model_file.exists():
            print(f"✗ Error: source_model.yaml not found at {source_model_file}")
            print("  Please specify with --source-model flag")
            return 1
    
    print("=" * 60)
    print("Validating ETL Source Model")
    print("=" * 60)
    print(f"Source Model: {source_model_file}")
    print(f"HCL Schema:   {hcl_file}")
    print("")
    
    # Load source model
    sys.path.insert(0, str(project_dir))
    
    try:
        from dagster_etl_framework import load_source_model, validate_model
        
        source_model = load_source_model(source_model_file)
        print(f"✓ Loaded source model with {len(source_model.dimensions)} dimensions and {len(source_model.facts)} facts")
        
        # Run validation
        result = validate_model(source_model, hcl_file)
        
        print(f"✓ Validated {result.tables_validated} tables and {result.columns_validated} columns")
        print("")
        
        # Report results
        if not result.issues:
            print("=" * 60)
            print("✅ Validation passed! No issues found.")
            print("=" * 60)
            return 0
        
        # Show errors
        errors = result.get_errors()
        if errors:
            print(f"❌ Found {len(errors)} error(s):")
            print("")
            for issue in errors:
                print(f"  {issue}")
            print("")
        
        # Show warnings
        warnings = result.get_warnings()
        if warnings:
            print(f"⚠️  Found {len(warnings)} warning(s):")
            print("")
            for issue in warnings:
                print(f"  {issue}")
            print("")
        
        # Show info if verbose
        if parsed_args.verbose:
            infos = result.get_infos()
            if infos:
                print(f"ℹ️  Found {len(infos)} info message(s):")
                print("")
                for issue in infos:
                    print(f"  {issue}")
                print("")
        
        # Summary
        print("=" * 60)
        if result.has_errors:
            print(f"❌ Validation failed: {len(errors)} error(s), {len(warnings)} warning(s)")
            print("=" * 60)
            return 1
        else:
            print(f"✅ Validation passed with {len(warnings)} warning(s)")
            print("=" * 60)
            return 0
            
    except Exception as e:
        print(f"✗ Error during validation: {e}")
        if parsed_args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    """Entry point when running as module: python -m dagster_etl_framework.commands"""
    if len(sys.argv) < 2:
        print("Usage: python -m dagster_etl_framework.commands <command> [args...]")
        print("Commands: run, test, validate")
        sys.exit(1)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    if command == "run":
        sys.exit(run_command(args))
    elif command == "test":
        sys.exit(test_command(args))
    elif command == "validate":
        sys.exit(validate_command(args))
    else:
        print(f"Unknown command: {command}")
        print("Available commands: run, test, validate")
        sys.exit(1)
