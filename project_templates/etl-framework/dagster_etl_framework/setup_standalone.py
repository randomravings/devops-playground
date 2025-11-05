#!/usr/bin/env python3.12
"""
Standalone setup script for ETL framework.
Can be run without any dependencies installed.
"""

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
