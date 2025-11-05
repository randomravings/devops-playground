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
    os.environ["SOURCE_DATA_PATH"] = args.input_dir
    os.environ["WAREHOUSE_TYPE"] = os.getenv("WAREHOUSE_TYPE", "csv")
    os.environ["WAREHOUSE_PATH"] = args.output_dir
    
    # Import here to use updated environment
    from dagster_etl_framework import create_resources
    
    resources = create_resources(
        source_data_path=args.input_dir,
        dagster_storage_path=".dagster/storage"
    )
    
    exit_code = run_partition(assets, args.date, resources, verbose=verbose)
    
    if verbose and exit_code == 0:
        # List warehouse files
        output_path = Path(args.output_dir)
        if output_path.exists():
            print(f"\nWarehouse files in {args.output_dir}:")
            csv_files = sorted(output_path.glob("*.csv"))
            if csv_files:
                for csv_file in csv_files:
                    print(f"  - {csv_file.name}")
            else:
                print("  (no CSV files found)")
    
    return exit_code
