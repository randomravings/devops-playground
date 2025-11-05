"""
Standalone entry point for setup command (can be run without venv).

This allows running setup directly with: python -m dagster_etl_framework.setup
"""

import sys
from .setup import main

if __name__ == "__main__":
    sys.exit(main())
