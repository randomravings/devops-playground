"""
Integration tests for the full Dagster asset pipeline.

Tests verify the complete pipeline using actual CSV files from tests/data/,
running partitioned assets just like the CLI command:
  dagster asset materialize -m demo_etl --select '*' --partition 2024-02-01
"""

from pathlib import Path
import sqlite3

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
from dagster_etl_framework import SourceCsvIOManager, SqliteIOManager
import dagster as dg


def test_partition_2024_02_01(tmp_path):
    """
    Test materializing partition 2024-02-01 (initial load).
    Equivalent to: dagster asset materialize -m demo_etl --select '*' --partition 2024-02-01
    """
    partition_key = "2024-02-01"
    
    # Use tmp_path for test outputs
    db_path = tmp_path / "warehouse.db"
    storage_dir = tmp_path / "storage"
    
    # Configure resources for testing (SQLite-based warehouse)
    resources = {
        "source_csv_io_manager": SourceCsvIOManager(base_path="tests/data"),
        "io_manager": dg.FilesystemIOManager(base_dir=str(storage_dir)),
        "warehouse_io_manager": SqliteIOManager(db_path=str(db_path)),
    }
    
    # Materialize all assets for this partition
    result = materialize(
        all_assets,
        partition_key=partition_key,
        resources=resources,
    )
    
    assert result.success
    
    # Verify database was created and tables exist
    assert db_path.exists()
    
    conn = sqlite3.connect(str(db_path))
    
    # Verify dim_date has exactly 1 record for this partition
    dim_date = pd.read_sql_query("SELECT * FROM t_dim_date", conn)
    assert len(dim_date) == 1
    assert str(dim_date.iloc[0]["dim_date_sk"]) == "2024-02-01"
    assert dim_date.iloc[0]["is_current"] == True  # Only date, so it's current
    
    # Verify dim_customer
    dim_customer = pd.read_sql_query("SELECT * FROM t_dim_customer", conn)
    assert len(dim_customer) == 3  # Initial load has 3 customers
    assert all(dim_customer["is_current"] == True)
    
    # Verify dim_product
    dim_product = pd.read_sql_query("SELECT * FROM t_dim_product", conn)
    assert len(dim_product) == 3  # Initial load has 3 products
    assert all(dim_product["is_current"] == True)
    
    # Verify fact_order
    fact_order = pd.read_sql_query("SELECT * FROM t_fact_order", conn)
    assert len(fact_order) == 3  # Initial load has 3 orders
    
    # Verify dim_date_sk is populated and matches order_date
    fact_order_with_dates = pd.read_sql_query(
        "SELECT order_date, dim_date_sk FROM t_fact_order", conn
    )
    for _, row in fact_order_with_dates.iterrows():
        # Convert both to date for comparison (handle datetime vs date differences)
        order_date = pd.to_datetime(row['order_date']).date()
        dim_date_sk = pd.to_datetime(row['dim_date_sk']).date()
        assert dim_date_sk == order_date, f"dim_date_sk {dim_date_sk} should match order_date {order_date}"
    assert fact_order_with_dates['dim_date_sk'].notna().all(), "All dim_date_sk values should be populated"
    
    conn.close()


def test_partition_2024_02_02_incremental(tmp_path):
    """
    Test materializing partition 2024-02-02 (delta load) after initial load.
    Tests incremental build by running two partitions in sequence.
    """
    # Use tmp_path for test outputs
    db_path = tmp_path / "warehouse.db"
    storage_dir = tmp_path / "storage"
    
    resources = {
        "source_csv_io_manager": SourceCsvIOManager(base_path="tests/data"),
        "io_manager": dg.FilesystemIOManager(base_dir=str(storage_dir)),
        "warehouse_io_manager": SqliteIOManager(db_path=str(db_path)),
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
    
    conn = sqlite3.connect(str(db_path))
    
    # Verify dim_date now has 2 records (incremental)
    dim_date = pd.read_sql_query("SELECT * FROM t_dim_date ORDER BY dim_date_sk", conn)
    assert len(dim_date) == 2
    assert set(dim_date["dim_date_sk"].astype(str)) == {"2024-02-01", "2024-02-02"}
    
    # SCD Type 2: Only the latest date should be current
    assert dim_date.iloc[0]["is_current"] == False  # 2024-02-01 is historical
    assert dim_date.iloc[1]["is_current"] == True   # 2024-02-02 is current
    
    # Verify dimensions accumulated (not replaced)
    dim_customer = pd.read_sql_query("SELECT * FROM t_dim_customer", conn)
    assert len(dim_customer) > 3  # Should have more than initial 3
    
    dim_product = pd.read_sql_query("SELECT * FROM t_dim_product", conn)
    assert len(dim_product) > 3  # Should have more than initial 3
    
    # Verify facts accumulated
    fact_order = pd.read_sql_query("SELECT * FROM t_fact_order", conn)
    assert len(fact_order) > 3  # Should have more than initial 3
    
    # Verify dim_date_sk is populated across all fact records
    fact_order_with_dates = pd.read_sql_query(
        "SELECT order_date, dim_date_sk FROM t_fact_order", conn
    )
    for _, row in fact_order_with_dates.iterrows():
        # Convert both to date for comparison (handle datetime vs date differences)
        order_date = pd.to_datetime(row['order_date']).date()
        dim_date_sk = pd.to_datetime(row['dim_date_sk']).date()
        assert dim_date_sk == order_date, f"dim_date_sk {dim_date_sk} should match order_date {order_date}"
    assert fact_order_with_dates['dim_date_sk'].notna().all(), "All dim_date_sk values should be populated"
    
    conn.close()
