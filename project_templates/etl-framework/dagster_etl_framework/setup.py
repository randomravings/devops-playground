"""
Setup utilities for ETL projects.

Provides reusable setup functionality for creating virtual environments,
installing dependencies, configuring warehouses, and launching Dagster.
Also provides teardown functionality for cleaning up environments.
"""

import os
import sys
import subprocess
import shutil
import argparse
from pathlib import Path
from typing import Optional, List, Tuple


class SetupManager:
    """Manages setup for ETL projects using the framework."""
    
    def __init__(self, project_dir: str, python_version: str = "3.12"):
        """
        Initialize setup manager.
        
        Args:
            project_dir: Path to the ETL project directory
            python_version: Required Python version (default: 3.12)
        """
        self.project_dir = Path(project_dir).resolve()
        self.python_version = python_version
        self.venv_dir = self.project_dir / ".venv"
        self.marker_file = self.venv_dir / ".setup_complete"
        self.framework_dir = Path(__file__).parent.parent
        
    def find_python(self) -> Optional[str]:
        """Find Python executable with required version."""
        candidates = [
            f"python{self.python_version}",
            f"/opt/homebrew/bin/python{self.python_version}",
            f"/usr/local/bin/python{self.python_version}",
        ]
        
        for candidate in candidates:
            if shutil.which(candidate):
                return candidate
        
        return None
    
    def setup_venv(self) -> bool:
        """
        Set up virtual environment with Python.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.venv_dir.exists():
            print(f"→ Creating virtual environment with Python {self.python_version}...")
            
            python_cmd = self.find_python()
            if not python_cmd:
                print(f"✗ Error: Python {self.python_version} not found. Please install it first:")
                print(f"  brew install python@{self.python_version}")
                return False
            
            try:
                # Get version for display
                version_output = subprocess.check_output(
                    [python_cmd, "--version"],
                    stderr=subprocess.STDOUT,
                    text=True
                ).strip()
                print(f"  Using: {python_cmd} ({version_output})")
                
                # Create venv
                subprocess.run([python_cmd, "-m", "venv", str(self.venv_dir)], check=True)
                print("✓ Virtual environment created")
            except subprocess.CalledProcessError as e:
                print(f"✗ Error creating virtual environment: {e}")
                return False
        else:
            print("✓ Virtual environment exists")
        
        return True
    
    def install_dependencies(self, framework_path: Optional[str] = None) -> bool:
        """
        Install Python dependencies in virtual environment.
        
        Args:
            framework_path: Optional path to framework (uses auto-detection if not provided)
            
        Returns:
            True if successful, False otherwise
        """
        if self.marker_file.exists():
            print("✓ Dependencies already installed")
            return True
        
        print("")
        print("→ Installing dependencies...")
        
        pip_cmd = str(self.venv_dir / "bin" / "pip")
        
        try:
            # Upgrade pip
            print("  Upgrading pip...")
            subprocess.run(
                [pip_cmd, "install", "--upgrade", "pip", "-q"],
                check=True
            )
            
            # Determine framework path
            if framework_path:
                fw_path = Path(framework_path).resolve()
            else:
                # Auto-detect: look for etl-framework as sibling directory
                fw_path = self.project_dir.parent / "etl-framework"
            
            if not fw_path.exists():
                print(f"  ✗ Error: Framework not found at {fw_path}")
                print("     Please specify correct path using --framework-path option")
                return False
            
            # Install framework
            print(f"  Installing dagster-etl-framework from {fw_path}...")
            subprocess.run(
                [pip_cmd, "install", "-e", str(fw_path), "-q"],
                check=True
            )
            print(f"  ✓ Installed dagster-etl-framework")
            
            # Install project package with test dependencies
            print("  Installing project package and dependencies...")
            subprocess.run(
                [pip_cmd, "install", "-e", f"{self.project_dir}[test]", "-q"],
                check=True
            )
            
            # Mark installation complete
            self.marker_file.touch()
            print("✓ Dependencies installed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"✗ Error installing dependencies: {e}")
            return False
    
    def setup_env_config(self, warehouse_type: str) -> bool:
        """
        Set up environment configuration from template.
        
        Args:
            warehouse_type: Type of warehouse ('csv' or 'postgres')
            
        Returns:
            True if successful, False otherwise
        """
        env_file = self.project_dir / ".env"
        env_template = self.framework_dir / f".env.{warehouse_type}.template"
        
        # Check if template exists
        if not env_template.exists():
            print(f"✗ Error: Environment template not found: {env_template}")
            return False
        
        # Check if .env exists
        if env_file.exists():
            print("✓ Loading environment from existing .env file")
            
            # Read existing warehouse type
            existing_type = None
            try:
                with open(env_file) as f:
                    for line in f:
                        if line.startswith("WAREHOUSE_TYPE="):
                            existing_type = line.split("=", 1)[1].strip()
                            break
            except Exception as e:
                print(f"⚠️  Warning: Could not read existing .env: {e}")
            
            # Verify warehouse type matches
            if existing_type and existing_type != warehouse_type:
                print(f"⚠️  Warning: Existing .env has WAREHOUSE_TYPE={existing_type}")
                print(f"   But you specified --warehouse {warehouse_type}")
                print("   Recreating .env from template...")
                shutil.copy(env_template, env_file)
                print(f"✓ Created .env from {env_template.name}")
        else:
            # Create .env from template
            print(f"→ Creating .env file from {env_template.name}...")
            shutil.copy(env_template, env_file)
            print(f"✓ Created .env with {warehouse_type} warehouse configuration")
        
        # Validate configuration
        return self.validate_env_config(warehouse_type)
    
    def validate_env_config(self, warehouse_type: str) -> bool:
        """
        Validate environment configuration.
        
        Args:
            warehouse_type: Type of warehouse to validate
            
        Returns:
            True if valid, False otherwise
        """
        env_file = self.project_dir / ".env"
        
        # Load .env
        env_vars = {}
        try:
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if "=" in line:
                            key, value = line.split("=", 1)
                            env_vars[key.strip()] = value.strip()
        except Exception as e:
            print(f"✗ Error reading .env: {e}")
            return False
        
        # Validate based on warehouse type
        if warehouse_type == "csv":
            if "WAREHOUSE_PATH" not in env_vars:
                print("✗ Error: WAREHOUSE_PATH not set in .env")
                return False
            print(f"  Using CSV warehouse: {env_vars['WAREHOUSE_PATH']}")
            
        elif warehouse_type == "postgres":
            required = ["POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"]
            missing = [k for k in required if k not in env_vars]
            if missing:
                print(f"✗ Error: PostgreSQL configuration incomplete in .env")
                print(f"  Missing: {', '.join(missing)}")
                return False
            print(f"  Using PostgreSQL warehouse: {env_vars['POSTGRES_USER']}@{env_vars['POSTGRES_HOST']}/{env_vars['POSTGRES_DB']}")
        
        return True
    
    def find_available_port(self, preferred_ports: Optional[List[int]] = None) -> Optional[int]:
        """
        Find an available port for Dagster UI.
        
        Args:
            preferred_ports: List of ports to try (default: [3000, 3001, 3002, 3003])
            
        Returns:
            Available port number or None if none found
        """
        if preferred_ports is None:
            preferred_ports = [3000, 3001, 3002, 3003]
        
        for port in preferred_ports:
            # Check if port is in use
            result = subprocess.run(
                ["lsof", "-i", f":{port}"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:  # Port not in use
                return port
        
        print(f"✗ Error: No available ports found (tried: {preferred_ports})")
        print("  Please free up one of these ports or stop existing Dagster instances")
        return None
    
    def check_dagster_running(self) -> bool:
        """
        Check if Dagster is already running.
        
        Returns:
            True if running, False otherwise
        """
        result = subprocess.run(
            ["pgrep", "-f", "dagster.*dev"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("")
            print("⚠️  Warning: Dagster appears to be already running")
            print("   Use 'teardown.sh' to stop it first, or check running processes:")
            print("   ps aux | grep 'dagster.*dev'")
            return True
        
        return False
    
    def launch_dagster_ui(self, port: Optional[int] = None) -> int:
        """
        Launch Dagster UI.
        
        Args:
            port: Port number to use (auto-detect if None)
            
        Returns:
            Exit code from dagster dev command
        """
        if port is None:
            port = self.find_available_port()
            if port is None:
                return 1
        
        print("")
        print("=" * 60)
        print("Launching Dagster UI")
        print("=" * 60)
        print("")
        print(f"  → UI will be available at http://localhost:{port}")
        print("  → Press Ctrl+C to stop")
        print("")
        
        dagster_cmd = str(self.venv_dir / "bin" / "dagster")
        
        # Use os.execv to replace current process
        os.execv(dagster_cmd, [dagster_cmd, "dev", "-p", str(port)])
        return 0  # Never reached


class TeardownManager:
    """Manages teardown for ETL projects."""
    
    def __init__(self, project_dir: str):
        """
        Initialize teardown manager.
        
        Args:
            project_dir: Path to the ETL project directory
        """
        self.project_dir = Path(project_dir).resolve()
        self.venv_dir = self.project_dir / ".venv"
    
    def stop_dagster(self) -> bool:
        """
        Stop running Dagster processes.
        
        Returns:
            True if processes were stopped, False if none were running
        """
        print("→ Checking for running Dagster processes...")
        
        # Find processes using Dagster ports
        result = subprocess.run(
            ["lsof", "-ti", ":3000,:4000,:4040"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            print(f"  Found Dagster processes on ports 3000, 4000, or 4040")
            print(f"  Stopping {len(pids)} process(es)...")
            
            for pid in pids:
                try:
                    subprocess.run(["kill", "-9", pid], check=False)
                except Exception:
                    pass
            
            # Give processes time to terminate
            subprocess.run(["sleep", "1"], check=False)
            print("✓ Dagster processes stopped")
            return True
        else:
            print("✓ No Dagster processes running")
            return False
    
    def check_items_to_remove(self) -> List[Tuple[str, Path]]:
        """
        Check what items exist and need cleanup.
        
        Returns:
            List of tuples (description, path) for items to remove
        """
        items = []
        
        # Virtual environment
        if self.venv_dir.exists():
            items.append(("Virtual environment (.venv/)", self.venv_dir))
        
        # Egg info
        egg_info = list(self.project_dir.glob("*.egg-info"))
        for egg in egg_info:
            items.append((f"Egg info ({egg.name})", egg))
        
        # Dagster storage
        dagster_dir = self.project_dir / ".dagster"
        if dagster_dir.exists():
            items.append(("Dagster storage (.dagster/)", dagster_dir))
        
        # Temporary Dagster directories
        tmp_dirs = list(self.project_dir.glob(".tmp*"))
        if tmp_dirs:
            items.append((f"Temporary Dagster directories ({len(tmp_dirs)} found)", None))
        
        # Output directory
        output_dir = self.project_dir / "output"
        if output_dir.exists():
            items.append(("ETL output directory (output/)", output_dir))
        
        # Environment file
        env_file = self.project_dir / ".env"
        if env_file.exists():
            items.append(("Environment file (.env)", env_file))
        
        # Test data cache
        data_dir = self.project_dir / ".data"
        if data_dir.exists():
            items.append(("Test data cache (.data/)", data_dir))
        
        # Pytest cache
        pytest_cache = self.project_dir / ".pytest_cache"
        if pytest_cache.exists():
            items.append(("Pytest cache (.pytest_cache/)", pytest_cache))
        
        # Python cache
        pycache_dirs = list(self.project_dir.rglob("__pycache__"))
        if pycache_dirs:
            items.append((f"Python cache directories ({len(pycache_dirs)} found)", None))
        
        # Compiled Python files
        pyc_files = list(self.project_dir.rglob("*.pyc"))
        if pyc_files:
            items.append((f"Compiled Python files ({len(pyc_files)} found)", None))
        
        return items
    
    def cleanup_files(self) -> None:
        """Remove files and directories."""
        print("→ Cleaning up files and directories...")
        
        # Remove virtual environment
        if self.venv_dir.exists():
            print("  Removing virtual environment...")
            shutil.rmtree(self.venv_dir)
        
        # Remove egg-info
        for egg_info in self.project_dir.glob("*.egg-info"):
            print(f"  Removing {egg_info.name}...")
            shutil.rmtree(egg_info)
        
        # Remove Dagster storage
        dagster_dir = self.project_dir / ".dagster"
        if dagster_dir.exists():
            print("  Removing Dagster storage...")
            shutil.rmtree(dagster_dir)
        
        # Remove temporary Dagster directories
        tmp_dirs = list(self.project_dir.glob(".tmp*"))
        if tmp_dirs:
            print(f"  Removing {len(tmp_dirs)} temporary directories...")
            for tmp_dir in tmp_dirs:
                shutil.rmtree(tmp_dir)
        
        # Remove output directory
        output_dir = self.project_dir / "output"
        if output_dir.exists():
            print("  Removing output directory...")
            shutil.rmtree(output_dir)
        
        # Remove environment file
        env_file = self.project_dir / ".env"
        if env_file.exists():
            print("  Removing environment file...")
            env_file.unlink()
        
        # Remove test data cache
        data_dir = self.project_dir / ".data"
        if data_dir.exists():
            print("  Removing test data cache...")
            shutil.rmtree(data_dir)
        
        # Remove pytest cache
        pytest_cache = self.project_dir / ".pytest_cache"
        if pytest_cache.exists():
            print("  Removing pytest cache...")
            shutil.rmtree(pytest_cache)
        
        # Remove Python cache files
        print("  Removing Python cache files...")
        for pycache_dir in self.project_dir.rglob("__pycache__"):
            shutil.rmtree(pycache_dir, ignore_errors=True)
        
        for pyc_file in self.project_dir.rglob("*.pyc"):
            pyc_file.unlink(missing_ok=True)
        
        for pyo_file in self.project_dir.rglob("*.pyo"):
            pyo_file.unlink(missing_ok=True)
        
        print("✓ Cleanup complete")


def main():
    """Main CLI entry point for setup command."""
    parser = argparse.ArgumentParser(
        description="Setup ETL project environment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  ./run.sh setup --project-dir ../demo-etl --warehouse csv
        """
    )
    
    parser.add_argument(
        "--warehouse",
        required=True,
        choices=["csv", "postgres"],
        help="csv or postgres"
    )
    parser.add_argument(
        "--framework-path",
        help="Path to framework (auto-detected)"
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Path to ETL project (default: .)"
    )
    parser.add_argument(
        "--no-ui",
        action="store_true",
        help="Don't launch Dagster UI"
    )
    parser.add_argument(
        "--python-version",
        default="3.12",
        help="Python version (default: 3.12)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("ETL Project Setup")
    print("=" * 60)
    print("")
    
    # Create setup manager
    manager = SetupManager(args.project_dir, args.python_version)
    
    # Run setup steps
    if not manager.setup_venv():
        return 1
    
    if not manager.install_dependencies(args.framework_path):
        return 1
    
    print("")
    if not manager.setup_env_config(args.warehouse):
        return 1
    
    print("")
    print("✓ Setup complete!")
    print("")
    
    # Launch UI if requested
    if not args.no_ui:
        if manager.check_dagster_running():
            return 1
        return manager.launch_dagster_ui()
    else:
        print("Virtual environment ready. To activate:")
        print(f"  source {manager.venv_dir}/bin/activate")
        print("")
        print("To launch Dagster UI:")
        print("  dagster dev -p 3000")
        print("")
        return 0


def teardown():
    """Main CLI entry point for teardown command."""
    parser = argparse.ArgumentParser(
        description="Clean up ETL project environment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  ./run.sh teardown --project-dir ../demo-etl --force
        """
    )
    
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Path to ETL project (default: .)"
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Skip confirmation"
    )
    parser.add_argument(
        "--ui-only",
        action="store_true",
        help="Only stop UI, keep environment"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("ETL Project Teardown")
    print("=" * 60)
    print("")
    
    # Create teardown manager
    manager = TeardownManager(args.project_dir)
    
    # Stop Dagster processes
    manager.stop_dagster()
    print("")
    
    if args.ui_only:
        print("✓ Teardown complete (UI only)")
        print("")
        print("Virtual environment preserved. To restart Dagster UI:")
        print("  ./setup.sh")
        return 0
    
    # Check what needs to be removed
    items = manager.check_items_to_remove()
    
    if not items:
        print("✓ Nothing to clean up. Environment is already clean.")
        print("")
        return 0
    
    # Show what will be removed
    print("The following items will be removed:")
    for description, _ in items:
        print(f"  - {description}")
    print("")
    print("Note: warehouse/ directory will be preserved (contains ETL outputs)")
    print("")
    
    # Ask for confirmation
    if not args.force:
        try:
            response = input("Do you want to proceed with cleanup? [y/N] ")
            if response.lower() not in ['y', 'yes']:
                print("Teardown cancelled.")
                return 0
        except (KeyboardInterrupt, EOFError):
            print("\nTeardown cancelled.")
            return 0
    
    print("")
    manager.cleanup_files()
    
    print("")
    print("✓ Teardown complete!")
    print("")
    print("To set up the environment again, run:")
    print("  ./setup.sh")
    print("")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
