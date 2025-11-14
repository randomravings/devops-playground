"""
Entry point for running dagster-etl-framework as a module.

Usage:
    python -m dagster_etl_framework setup --project-dir . --warehouse sqlite
    python -m dagster_etl_framework run --project-dir . --date 2024-02-01
"""

import sys
from .main import main

if __name__ == "__main__":
    sys.exit(main())
