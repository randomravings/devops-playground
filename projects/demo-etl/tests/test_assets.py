"""
Integration tests for the full Dagster asset pipeline.

Tests verify the complete pipeline using actual CSV files from tests/data/,
running partitioned assets just like the CLI command:
  dagster asset materialize -m demo_etl --select '*' --partition 2024-02-01 -c tests/config_test.yaml
"""

from pathlib import Path

import pandas as pd
import pytest
from dagster import (
    materialize,
    build_asset_context,
    DagsterInstance,
)

from demo_etl.assets import (
    all_assets,
    daily_partitions,
)
from dagster_etl_framework import CsvIOManager, SourceCsvIOManager
import dagster as dg


def test_partition_2024_02_01(tmp_path):
    """
    Test materializing partition 2024-02-01 (initial load).
    Equivalent to: dagster asset materialize -m demo_etl --select '*' --partition 2024-02-01 -c tests/config_test.yaml
    """
    partition_key = "2024-02-01"
    
    # Use tmp_path for test outputs
    warehouse_dir = tmp_path / "warehouse"
    storage_dir = tmp_path / "storage"
    
    # Configure resources for testing (CSV-based warehouse)
    resources = {
        "source_csv_io_manager": SourceCsvIOManager(base_path="tests/data"),
        "io_manager": dg.FilesystemIOManager(base_dir=str(storage_dir)),
        "warehouse_io_manager": CsvIOManager(base_path=str(warehouse_dir)),
    }
    
    # Materialize all assets for this partition
    result = materialize(
        all_assets,
        partition_key=partition_key,
        resources=resources,
    )
    
    assert result.success
    
    # Verify warehouse files were created
    assert (warehouse_dir / "dim_customers.csv").exists()
    assert (warehouse_dir / "dim_products.csv").exists()
    assert (warehouse_dir / "dim_date.csv").exists()
    assert (warehouse_dir / "fact_orders.csv").exists()
    
    # Verify dim_date has exactly 1 record for this partition
    dim_date = pd.read_csv(warehouse_dir / "dim_date.csv")
    assert len(dim_date) == 1
    assert str(dim_date.iloc[0]["dim_date_id"]) == "2024-02-01"
    
    # Verify dim_customers
    dim_customers = pd.read_csv(warehouse_dir / "dim_customers.csv")
    assert len(dim_customers) == 3  # Initial load has 3 customers
    assert all(dim_customers["is_current"] == True)
    
    # Verify dim_products
    dim_products = pd.read_csv(warehouse_dir / "dim_products.csv")
    assert len(dim_products) == 3  # Initial load has 3 products
    assert all(dim_products["is_current"] == True)
    
    # Verify fact_orders
    fact_orders = pd.read_csv(warehouse_dir / "fact_orders.csv")
    assert len(fact_orders) == 3  # Initial load has 3 orders


def test_partition_2024_02_02_incremental(tmp_path):
    """
    Test materializing partition 2024-02-02 (delta load) after initial load.
    Tests incremental build by running two partitions in sequence.
    """
    # Use tmp_path for test outputs
    warehouse_dir = tmp_path / "warehouse"
    storage_dir = tmp_path / "storage"
    
    resources = {
        "source_csv_io_manager": SourceCsvIOManager(base_path="tests/data"),
        "io_manager": dg.FilesystemIOManager(base_dir=str(storage_dir)),
        "warehouse_io_manager": CsvIOManager(base_path=str(warehouse_dir)),
    }
    
    # First materialize 2024-02-01 (initial)
    result1 = materialize(
        all_assets,
        partition_key="2024-02-01",
        resources=resources,
    )
    assert result1.success
    
    # Then materialize 2024-02-02 (delta)
    result2 = materialize(
        all_assets,
        partition_key="2024-02-02",
        resources=resources,
    )
    assert result2.success
    
    # Verify dim_date now has 2 records (incremental)
    dim_date = pd.read_csv(warehouse_dir / "dim_date.csv")
    assert len(dim_date) == 2
    assert set(dim_date["dim_date_id"].astype(str)) == {"2024-02-01", "2024-02-02"}
    
    # Verify dimensions accumulated (not replaced)
    dim_customers = pd.read_csv(warehouse_dir / "dim_customers.csv")
    assert len(dim_customers) > 3  # Should have more than initial 3
    
    dim_products = pd.read_csv(warehouse_dir / "dim_products.csv")
    assert len(dim_products) > 3  # Should have more than initial 3
    
    # Verify facts accumulated
    fact_orders = pd.read_csv(warehouse_dir / "fact_orders.csv")
    assert len(fact_orders) > 3  # Should have more than initial 3
