"""
Generic resource factory for Dagster ETL projects.

Provides environment-based resource configuration with support for:
- CSV or PostgreSQL warehouse backends
- Source CSV file reading
- Dagster internal storage

Configuration via environment variables with strict validation.
Note: .env file loading is handled by CLI - this module only reads environment variables.
"""

import os
import dagster as dg
from dagster_etl_framework.io_managers import SourceCsvIOManager, PostgresIOManager, SqliteIOManager


def create_resources(
    source_data_path: str = "tests/data",
    dagster_storage_path: str = ".dagster/storage"
) -> dict:
    """
    Create resource definitions with environment-based configuration.
    
    This is a generic resource factory that works for any ETL project.
    Resources are configured using environment variables with sensible defaults.
    
    Environment Variables:
        WAREHOUSE_TYPE: Type of warehouse storage - 'sqlite' or 'postgres' (default: 'sqlite')
        
        For SQLite mode (WAREHOUSE_TYPE=sqlite or default):
            SQLITE_DB_PATH: Path to SQLite database file (default: '.data/warehouse.db')
        
        For PostgreSQL mode (WAREHOUSE_TYPE=postgres):
            POSTGRES_HOST: PostgreSQL host (REQUIRED)
            POSTGRES_DB: PostgreSQL database (REQUIRED)
            POSTGRES_USER: PostgreSQL user (REQUIRED)
            POSTGRES_PASSWORD: PostgreSQL password (REQUIRED)
            POSTGRES_SCHEMA: PostgreSQL schema (default: public)
        
        Optional:
            SOURCE_DATA_PATH: Override source CSV files path
            DAGSTER_STORAGE_PATH: Override Dagster internal storage path
    
    Args:
        source_data_path: Default path to source CSV files (can be overridden by SOURCE_DATA_PATH env var)
        dagster_storage_path: Default path for Dagster internal storage (can be overridden by DAGSTER_STORAGE_PATH env var)
    
    Returns:
        Dictionary of resource definitions for Dagster
    
    Raises:
        ValueError: If required environment variables are missing or invalid
    
    Example:
        # In your project's assets.py or definitions:
        from dagster_etl_framework import create_resources
        
        resources = create_resources(
            source_data_path="data/input",
            dagster_storage_path=".dagster/storage"
        )
    """
    # Warehouse type - REQUIRED, no default
    warehouse_type = os.getenv("WAREHOUSE_TYPE")
    if not warehouse_type:
        raise ValueError(
            "WAREHOUSE_TYPE environment variable is required.\n"
            "Set it to 'sqlite' or 'postgres' in your .env file or environment.\n"
            "Example:\n"
            "  export WAREHOUSE_TYPE=sqlite"
        )
    warehouse_type = warehouse_type.lower()
    
    # Select appropriate warehouse IO manager
    if warehouse_type == "postgres":
        # Validate required Postgres settings
        required_postgres_vars = ["POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"]
        missing_vars = [var for var in required_postgres_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(
                f"WAREHOUSE_TYPE=postgres requires the following environment variables: "
                f"{', '.join(missing_vars)}\n"
                f"Example:\n"
                f"  export POSTGRES_HOST=localhost\n"
                f"  export POSTGRES_DB=warehouse\n"
                f"  export POSTGRES_USER=etl_user\n"
                f"  export POSTGRES_PASSWORD=your_password"
            )
        
        warehouse_io_manager = PostgresIOManager(
            host=os.getenv("POSTGRES_HOST"),
            db=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            schema=os.getenv("POSTGRES_SCHEMA", "public")
        )
    elif warehouse_type == "sqlite":
        sqlite_db_path = os.getenv("SQLITE_DB_PATH")
        if not sqlite_db_path:
            raise ValueError(
                "SQLITE_DB_PATH environment variable is required when WAREHOUSE_TYPE=sqlite.\n"
                "Set it in your .env file or environment.\n"
                "Example:\n"
                "  export SQLITE_DB_PATH=.data/warehouse.db"
            )
        print(f"→ [create_resources] Using SQLite: {sqlite_db_path}")
        
        warehouse_io_manager = SqliteIOManager(db_path=sqlite_db_path)
    else:
        raise ValueError(
            f"Invalid WAREHOUSE_TYPE='{warehouse_type}'. Must be 'sqlite' or 'postgres'."
        )
    
    # Allow environment variables to override function parameters
    # These have reasonable function parameter defaults, so env vars are truly optional overrides
    actual_source_path = os.getenv("SOURCE_DATA_PATH") or source_data_path
    actual_storage_path = os.getenv("DAGSTER_STORAGE_PATH") or dagster_storage_path
    
    return {
        "source_csv_io_manager": SourceCsvIOManager(base_path=actual_source_path),
        "io_manager": dg.FilesystemIOManager(base_dir=actual_storage_path),
        "warehouse_io_manager": warehouse_io_manager,
    }
