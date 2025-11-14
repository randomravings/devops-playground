"""
Generic CLI utility for running ETL partitions.

Provides a reusable command-line interface for materializing
Dagster assets for specific dates/partitions.
"""

import sys
import argparse
from pathlib import Path
from typing import List, Optional
import dagster as dg
from dagster import materialize, AssetsDefinition
from dotenv import load_dotenv


def load_project_env(project_dir: str = "."):
    """Load .env file from project directory if it exists."""
    env_file = Path(project_dir) / ".env"
    if env_file.exists():
        print(f"→ Loading environment from: {env_file.resolve()}")
        load_dotenv(env_file)
        print(f"✓ Loaded .env file")
    else:
        print(f"→ No .env file found at: {env_file.resolve()}")


def run_partition(
    assets: List[AssetsDefinition],
    partition_key: str,
    resources: dict,
    verbose: bool = True
) -> int:
    """
    Materialize assets for a specific partition.
    
    This is a generic partition runner that can be used with any ETL project.
    
    Args:
        assets: List of Dagster asset definitions to materialize
        partition_key: Partition key (e.g., "2024-02-01" for daily partitions)
        resources: Resource definitions (e.g., from create_resources())
        verbose: Print detailed output
    
    Returns:
        0 on success, 1 on failure
    
    Example:
        from dagster_etl_framework import run_partition, create_resources
        from my_project.assets import all_assets
        
        resources = create_resources()
        exit_code = run_partition(
            assets=all_assets,
            partition_key="2024-02-01",
            resources=resources
        )
    """
    if verbose:
        print(f"Materializing assets for partition: {partition_key}")
        print("")
    
    try:
        result = materialize(
            assets,
            partition_key=partition_key,
            resources=resources
        )
        
        if result.success:
            if verbose:
                print("")
                print("=" * 60)
                print("✅ Pipeline completed successfully!")
                print("=" * 60)
            return 0
        else:
            if verbose:
                print("\n✗ Pipeline completed with errors")
            return 1
            
    except Exception as e:
        if verbose:
            print(f"\n✗ Error running pipeline: {e}")
            import traceback
            traceback.print_exc()
        return 1


def create_partition_cli(
    assets: List[AssetsDefinition],
    description: str = "Run the ETL pipeline for a specific date",
    default_source_path: str = "tests/data"
) -> argparse.ArgumentParser:
    """
    Create a CLI parser for running partitioned ETL pipelines.
    
    This provides a reusable CLI interface that any ETL project can use.
    
    Args:
        assets: List of Dagster asset definitions to materialize
        description: CLI description
        default_source_path: Default path for source data
    
    Returns:
        Configured ArgumentParser ready for use
    
    Example:
        from dagster_etl_framework import create_partition_cli, create_resources
        from my_project.assets import all_assets
        
        def main():
            parser = create_partition_cli(all_assets)
            args = parser.parse_args()
            
            # Set environment for resources
            import os
            os.environ["SOURCE_DATA_PATH"] = args.input_dir
            os.environ["WAREHOUSE_PATH"] = args.output_dir
            
            resources = create_resources()
            return run_partition(all_assets, args.date, resources)
        
        if __name__ == "__main__":
            sys.exit(main())
    """
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  python run_date.py -i {default_source_path} -d 2024-02-01 -o .data/warehouse
  python run_date.py --input-dir {default_source_path} --date 2024-02-01 --output-dir .data/warehouse
        """
    )
    
    parser.add_argument(
        "-i", "--input-dir",
        default=default_source_path,
        help=f"Input directory containing source data (default: {default_source_path})"
    )
    parser.add_argument(
        "-d", "--date",
        required=True,
        help="Date in YYYY-MM-DD format (partition key)"
    )
    parser.add_argument(
        "-o", "--output-dir",
        default=".data/warehouse",
        help="Output warehouse directory (default: .data/warehouse)"
    )
    parser.add_argument(
        "-p", "--project-dir",
        default=".",
        help="Project directory containing .env file (default: .)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=True,
        help="Print detailed output (default: True)"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress detailed output"
    )
    
    return parser


def run_partition_cli(
    assets: List[AssetsDefinition],
    description: str = "Run the ETL pipeline for a specific date",
    default_source_path: str = "tests/data"
) -> int:
    """
    Run a complete partition CLI with argument parsing and execution.
    
    This is a convenience function that combines create_partition_cli() and run_partition()
    into a single call suitable for use as a main() function.
    
    Args:
        assets: List of Dagster asset definitions to materialize
        description: CLI description
        default_source_path: Default path for source data
    
    Returns:
        Exit code (0 for success, 1 for failure)
    
    Example:
        # In your project's run_date.py:
        from dagster_etl_framework import run_partition_cli
        from my_project.assets import all_assets
        
        if __name__ == "__main__":
            sys.exit(run_partition_cli(all_assets))
    """
    parser = create_partition_cli(assets, description, default_source_path)
    args = parser.parse_args()
    
    # Load .env from project directory first
    load_project_env(args.project_dir)
    
    # Validate input directory
    input_path = Path(args.input_dir)
    if not input_path.exists():
        print(f"✗ Error: Input directory does not exist: {args.input_dir}", file=sys.stderr)
        return 1
    
    verbose = args.verbose and not args.quiet
    
    if verbose:
        print("=" * 60)
        print(f"ETL Pipeline - Running partition: {args.date}")
        print("=" * 60)
        print(f"Input directory: {args.input_dir}")
        print(f"Output directory: {args.output_dir}")
        print("")
    
    # Set environment variables for resource configuration
    import os
    
    # Always set SOURCE_DATA_PATH from CLI argument
    os.environ["SOURCE_DATA_PATH"] = args.input_dir
    
    # Debug: Show current configuration from .env
    current_warehouse_type = os.environ.get("WAREHOUSE_TYPE")
    current_sqlite_path = os.environ.get("SQLITE_DB_PATH")
    
    if verbose:
        print(f"→ WAREHOUSE_TYPE from .env: {current_warehouse_type or '(not set)'}")
        print(f"→ SQLITE_DB_PATH from .env: {current_sqlite_path or '(not set)'}")
    
    # If not set in .env, use CLI defaults
    if not current_warehouse_type:
        os.environ["WAREHOUSE_TYPE"] = "sqlite"
        if verbose:
            print(f"→ Setting WAREHOUSE_TYPE=sqlite (CLI default)")
    
    if not current_sqlite_path and os.environ.get("WAREHOUSE_TYPE") == "sqlite":
        os.environ["SQLITE_DB_PATH"] = args.output_dir
        if verbose:
            print(f"→ Setting SQLITE_DB_PATH from CLI --output-dir: {args.output_dir}")
    elif current_sqlite_path and verbose:
        print(f"→ Using SQLITE_DB_PATH from .env: {current_sqlite_path}")
    
    # Import here to use updated environment
    from dagster_etl_framework import create_resources
    
    resources = create_resources(
        source_data_path=args.input_dir,
        dagster_storage_path=".dagster/storage"
    )
    
    exit_code = run_partition(assets, args.date, resources, verbose=verbose)
    
    if verbose and exit_code == 0:
        # Show warehouse info based on type
        warehouse_type = os.getenv("WAREHOUSE_TYPE")
        
        if warehouse_type == "sqlite":
            db_path = os.getenv("SQLITE_DB_PATH")
            print(f"\nSQLite database: {db_path}")
            db_file = Path(db_path)
            if db_file.exists():
                size_mb = db_file.stat().st_size / (1024 * 1024)
                print(f"  Size: {size_mb:.2f} MB")
        elif warehouse_type == "postgres":
            print(f"\nData written to PostgreSQL database")
    
    return exit_code
