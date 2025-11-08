"""
Teardown CLI entry point.

This module provides the main entry point for the teardown command.
"""

import sys
from .setup import teardown


if __name__ == "__main__":
    sys.exit(teardown())
