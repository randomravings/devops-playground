"""
Resource Definitions

Simple wrapper around the framework's generic resource factory.
"""

from dagster_etl_framework import create_resources


def get_resources() -> dict:
    """
    Get resource definitions for the demo ETL project.
    
    Uses the framework's generic create_resources() with project-specific defaults.
    
    Resources are configured using environment variables:
    - WAREHOUSE_TYPE: 'csv' or 'postgres' (REQUIRED)
    - WAREHOUSE_PATH: Path for CSV warehouse (required when WAREHOUSE_TYPE=csv)
    - POSTGRES_*: PostgreSQL connection settings (required when WAREHOUSE_TYPE=postgres)
    - SOURCE_DATA_PATH: Override source data path (default: tests/data)
    - DAGSTER_STORAGE_PATH: Override Dagster storage (default: .dagster/storage)
    """
    return create_resources(
        source_data_path="tests/data",
        dagster_storage_path=".dagster/storage"
    )
