"""
Main CLI entry point for the ETL framework.

Provides commands for managing ETL projects: setup, teardown, run, test.
"""

import sys
import argparse
from pathlib import Path


def main():
    """Main CLI entry point."""
    # Show help if no arguments provided
    if len(sys.argv) == 1:
        sys.argv.append("-h")
    
    parser = argparse.ArgumentParser(
        prog="etl-framework",
        description="ETL Framework - Manage ETL projects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  setup      Setup environment (creates .venv, installs deps, starts UI)
  run        Run pipeline for specific date
  test       Run tests
  validate   Validate source model against database schema (HCL)
  teardown   Clean up environment

Examples:
  # Via bash wrapper (recommended)
  ./run.sh setup --project-dir ../demo-etl --warehouse sqlite
  ./run.sh run --project-dir ../demo-etl -d 2024-02-01
  ./run.sh test --project-dir ../demo-etl
  ./run.sh validate --project-dir ../demo-etl --hcl ../demo-dw/target/schema.hcl
  ./run.sh teardown --project-dir ../demo-etl --force

  # Via Python directly
  etl-framework setup --project-dir ../demo-etl --warehouse sqlite
  etl-framework run --project-dir ../demo-etl -d 2024-02-01
  etl-framework validate --project-dir ../demo-etl --hcl ../demo-dw/target/schema.hcl

Help:
  etl-framework <command> -h    Show detailed help for a command
        """
    )
    
    parser.add_argument(
        "command",
        choices=["setup", "teardown", "run", "test", "validate"],
        help="Command to execute"
    )
    parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help="Arguments for the command"
    )
    
    args = parser.parse_args()
    
    # Dispatch to appropriate command
    if args.command == "setup":
        from .setup import main as setup_main
        sys.argv = ["etl-setup"] + args.args
        return setup_main()
    
    elif args.command == "teardown":
        from .setup import teardown as teardown_main
        sys.argv = ["etl-teardown"] + args.args
        return teardown_main()
    
    elif args.command == "run":
        from .commands import run_command
        return run_command(args.args)
    
    elif args.command == "test":
        from .commands import test_command
        return test_command(args.args)
    
    elif args.command == "validate":
        from .commands import validate_command
        return validate_command(args.args)
    
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
