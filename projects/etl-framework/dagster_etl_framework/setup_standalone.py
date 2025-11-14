#!/usr/bin/env python3.12
"""
Standalone setup script for ETL framework.
Can be run without any dependencies installed.
"""

def setup_environment(project_dir: str, framework_path: str, warehouse_type: str, start_ui: bool = False):
    """
    Setup environment function called by CLI.
    
    Args:
        project_dir: Path to the project directory
        framework_path: Path to the framework
        warehouse_type: Type of warehouse (sqlite or postgres)
        start_ui: Whether to start the UI (not used in standalone)
    """
    import sys
    import importlib.util
    from pathlib import Path
    
    # Load setup.py directly without triggering __init__.py
    framework_dir = Path(framework_path) / "dagster_etl_framework"
    setup_file = framework_dir / "setup.py"
    
    spec = importlib.util.spec_from_file_location("setup_module", setup_file)
    setup_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(setup_module)
    
    # Create SetupManager and run setup
    setup_manager = setup_module.SetupManager(project_dir)
    
    # Setup virtual environment
    if not setup_manager.setup_venv():
        print("❌ Failed to setup virtual environment")
        sys.exit(1)
    
    # Install dependencies
    if not setup_manager.install_dependencies(framework_path):
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    # Setup environment configuration
    if not setup_manager.setup_env_config(warehouse_type):
        print("❌ Failed to setup environment configuration")
        sys.exit(1)
    
    print("✅ Environment setup completed successfully")


if __name__ == "__main__":
    import sys
    import importlib.util
    from pathlib import Path
    
    # Remove 'setup' from arguments if present (comes from run.sh)
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        sys.argv.pop(1)
    
    # Load setup.py directly without triggering __init__.py
    framework_dir = Path(__file__).parent
    setup_file = framework_dir / "setup.py"
    
    spec = importlib.util.spec_from_file_location("setup_module", setup_file)
    setup_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(setup_module)
    
    # Run setup main
    sys.exit(setup_module.main())
