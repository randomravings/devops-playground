"""
Comprehensive tests for SCD Type 2 dimension processing.

Tests verify correct behavior for:
- Initial loads (INSERT all with is_current=1)
- T1 changes (UPDATE in place, all versions for business key)
- T2 changes (close old record, INSERT new version)
- Mixed T1+T2 changes
- New business keys (INSERT)
- No changes (no operation)
"""

from pathlib import Path
import sqlite3

import pandas as pd
import pytest
from dagster import materialize
import dagster as dg

from demo_etl.assets import all_assets
from dagster_etl_framework import SourceCsvIOManager, SqliteIOManager


@pytest.fixture
def test_resources(tmp_path):
    """Create test resources with temporary database."""
    db_path = tmp_path / "warehouse.db"
    storage_dir = tmp_path / "storage"
    
    return {
        "source_csv_io_manager": SourceCsvIOManager(base_path="tests/data"),
        "io_manager": dg.FilesystemIOManager(base_dir=str(storage_dir)),
        "warehouse_io_manager": SqliteIOManager(db_path=str(db_path)),
    }, db_path


def get_customer_data(db_path):
    """Helper to load customer dimension data."""
    conn = sqlite3.connect(str(db_path))
    df = pd.read_sql_query(
        "SELECT dim_customer_sk, customer_id, email, phone, segment, "
        "address_line1, address_line2, postal_code, "
        "effective_from, effective_to, is_current, extract_date, "
        "t1_hash, t2_hash "
        "FROM t_dim_customer ORDER BY dim_customer_sk",
        conn
    )
    conn.close()
    return df


def test_initial_load(test_resources):
    """Test initial load creates records with is_current=1."""
    resources, db_path = test_resources
    
    # Load 2024-02-01 (initial)
    result = materialize(all_assets, partition_key="2024-02-01", resources=resources)
    assert result.success
    
    df = get_customer_data(db_path)
    
    # Verify initial load
    assert len(df) == 3, "Should have 3 customers"
    assert all(df["is_current"] == 1), "All records should be current"
    assert all(df["effective_to"] == "2999-12-31"), "All records should have far future end date"
    assert all(df["effective_from"] == "2024-02-01"), "All records should start on load date"
    
    # Verify business keys
    assert set(df["customer_id"]) == {"CUST-001", "CUST-002", "CUST-003"}
    
    # Verify SKs are sequential
    assert list(df["dim_customer_sk"]) == [1, 2, 3]


def test_t1_change_updates_in_place(test_resources):
    """Test T1 changes (phone) update records in place without versioning."""
    resources, db_path = test_resources
    
    # Load 2024-02-01 and 2024-02-02
    materialize(all_assets, partition_key="2024-02-01", resources=resources)
    result = materialize(all_assets, partition_key="2024-02-02", resources=resources)
    assert result.success
    
    df = get_customer_data(db_path)
    
    # CUST-001: phone changed 555-1000 -> 555-1001 (T1 change)
    cust_001 = df[df["customer_id"] == "CUST-001"]
    
    # Should still be only 1 record (no versioning for T1)
    assert len(cust_001) == 1, "T1 change should not create new version"
    
    record = cust_001.iloc[0]
    assert record["dim_customer_sk"] == 1, "SK should remain the same"
    assert record["phone"] == "555-1001", "Phone should be updated"
    assert record["is_current"] == 1, "Should still be current"
    assert record["effective_to"] == "2999-12-31", "Should still have far future end date"
    assert record["effective_from"] == "2024-02-01", "Start date should not change"
    # Note: extract_date will be updated to 2024-02-02 for current record (this is expected)


def test_t2_change_creates_new_version(test_resources):
    """Test T2 changes (segment, address) close old record and create new version."""
    resources, db_path = test_resources
    
    # Load 2024-02-01 and 2024-02-02
    materialize(all_assets, partition_key="2024-02-01", resources=resources)
    result = materialize(all_assets, partition_key="2024-02-02", resources=resources)
    assert result.success
    
    df = get_customer_data(db_path)
    
    # CUST-002: segment changed Enterprise -> Premium (T2 change)
    cust_002 = df[df["customer_id"] == "CUST-002"].sort_values("dim_customer_sk")
    
    assert len(cust_002) == 2, "T2 change should create new version"
    
    # Old version (closed)
    old = cust_002.iloc[0]
    assert old["dim_customer_sk"] == 2
    assert old["segment"] == "Enterprise"
    assert old["is_current"] == 0, "Old version should be closed"
    assert old["effective_from"] == "2024-02-01"
    assert old["effective_to"] == "2024-02-01", "Should be closed day before new version"
    assert old["extract_date"] == "2024-02-01", "Extract date should be preserved"
    
    # New version (current)
    new = cust_002.iloc[1]
    assert new["dim_customer_sk"] == 4, "Should have new SK"
    assert new["segment"] == "Premium", "Should have new segment value"
    assert new["is_current"] == 1, "New version should be current"
    assert new["effective_from"] == "2024-02-02"
    assert new["effective_to"] == "2999-12-31"
    assert new["extract_date"] == "2024-02-02"
    
    # T2 hash should be different
    assert old["t2_hash"] != new["t2_hash"], "T2 hash should change"


def test_t2_change_with_address(test_resources):
    """Test T2 changes in address fields create new version."""
    resources, db_path = test_resources
    
    # Load 2024-02-01 and 2024-02-02
    materialize(all_assets, partition_key="2024-02-01", resources=resources)
    result = materialize(all_assets, partition_key="2024-02-02", resources=resources)
    assert result.success
    
    df = get_customer_data(db_path)
    
    # CUST-003: address changed (T2 change)
    cust_003 = df[df["customer_id"] == "CUST-003"].sort_values("dim_customer_sk")
    
    assert len(cust_003) == 2, "T2 change should create new version"
    
    old = cust_003.iloc[0]
    assert old["dim_customer_sk"] == 3
    assert old["address_line1"] == "30 King St Apt 5"
    assert old["address_line2"] is None or pd.isna(old["address_line2"])
    assert old["postal_code"] == "M5H1J9"
    assert old["is_current"] == 0
    assert old["effective_to"] == "2024-02-01"
    
    new = cust_003.iloc[1]
    assert new["dim_customer_sk"] == 5
    assert new["address_line1"] == "45 Queen St W"
    assert new["address_line2"] == "Suite 200"
    assert new["postal_code"] == "M5H2M9"
    assert new["is_current"] == 1
    assert new["effective_from"] == "2024-02-02"


def test_new_customer_insert(test_resources):
    """Test new business keys are inserted with is_current=1."""
    resources, db_path = test_resources
    
    # Load 2024-02-01 and 2024-02-02
    materialize(all_assets, partition_key="2024-02-01", resources=resources)
    result = materialize(all_assets, partition_key="2024-02-02", resources=resources)
    assert result.success
    
    df = get_customer_data(db_path)
    
    # CUST-004: new customer in 2024-02-02
    cust_004 = df[df["customer_id"] == "CUST-004"]
    
    assert len(cust_004) == 1, "New customer should have 1 record"
    
    record = cust_004.iloc[0]
    assert record["dim_customer_sk"] == 6, "Should have next available SK"
    assert record["is_current"] == 1
    assert record["effective_from"] == "2024-02-02"
    assert record["effective_to"] == "2999-12-31"
    assert record["extract_date"] == "2024-02-02"


def test_mixed_t1_t2_change(test_resources):
    """Test record with both T1 and T2 changes creates new version (T2 takes precedence)."""
    resources, db_path = test_resources
    
    # Load all three days
    materialize(all_assets, partition_key="2024-02-01", resources=resources)
    materialize(all_assets, partition_key="2024-02-02", resources=resources)
    result = materialize(all_assets, partition_key="2024-02-03", resources=resources)
    assert result.success
    
    df = get_customer_data(db_path)
    
    # CUST-001 on 2024-02-03: email changed (T1) AND address_line2 added (T2)
    cust_001 = df[df["customer_id"] == "CUST-001"].sort_values("dim_customer_sk")
    
    # Should have 2 versions: original SK=1 and new SK=7
    assert len(cust_001) == 2, "T1+T2 change should create new version"
    
    # Old version (closed on 2024-02-03)
    old = cust_001.iloc[0]
    assert old["dim_customer_sk"] == 1
    assert old["is_current"] == 0
    assert old["effective_to"] == "2024-02-02", "Should be closed day before new version"
    assert old["extract_date"] == "2024-02-01", "extract_date should NEVER change - represents original insertion date"
    # T1 fields should be updated even on closed record
    assert old["phone"] == "555-1001", "T1 field should be updated from 2024-02-02 load"
    
    # New version (current)
    new = cust_001.iloc[1]
    assert new["dim_customer_sk"] == 7
    assert new["is_current"] == 1
    assert new["effective_from"] == "2024-02-03"
    assert new["effective_to"] == "2999-12-31"
    assert new["extract_date"] == "2024-02-03"
    # Should have both T1 and T2 changes
    assert new["email"] == "alice.smith@example.com", "T1 change (email)"
    assert new["phone"] == "555-1001", "T1 change from previous load"
    assert new["address_line2"] == "Floor 3", "T2 change (address)"


def test_t1_updates_all_versions(test_resources):
    """Test T1 changes update ALL versions of a business key, not just current."""
    resources, db_path = test_resources
    
    # Load all three days
    materialize(all_assets, partition_key="2024-02-01", resources=resources)
    materialize(all_assets, partition_key="2024-02-02", resources=resources)
    result = materialize(all_assets, partition_key="2024-02-03", resources=resources)
    assert result.success
    
    df = get_customer_data(db_path)
    
    # CUST-002 has 3 versions: SK=2 (closed), SK=4 (closed), SK=8 (current)
    cust_002 = df[df["customer_id"] == "CUST-002"].sort_values("dim_customer_sk")
    
    assert len(cust_002) == 3, "Should have 3 versions"
    
    # All versions should have same T1 hash (T1 fields are kept in sync)
    t1_hashes = cust_002["t1_hash"].unique()
    assert len(t1_hashes) == 1, "All versions should have same T1 hash"
    
    # All versions should have same phone/email (T1 fields)
    assert all(cust_002["phone"] == "555-2000"), "All versions should have same phone"
    assert all(cust_002["email"] == "bob@example.com"), "All versions should have same email"


def test_no_change_no_operation(test_resources):
    """Test records with no changes are not updated."""
    resources, db_path = test_resources
    
    # Load 2024-02-01, 2024-02-02, and 2024-02-03
    materialize(all_assets, partition_key="2024-02-01", resources=resources)
    materialize(all_assets, partition_key="2024-02-02", resources=resources)
    result = materialize(all_assets, partition_key="2024-02-03", resources=resources)
    assert result.success
    
    df = get_customer_data(db_path)
    
    # CUST-003: no change on 2024-02-03
    cust_003 = df[df["customer_id"] == "CUST-003"].sort_values("dim_customer_sk")
    
    # Should have 2 versions: SK=3 (closed on 02-02), SK=5 (current, unchanged on 02-03)
    assert len(cust_003) == 2
    
    current = cust_003[cust_003["is_current"] == 1].iloc[0]
    assert current["dim_customer_sk"] == 5
    assert current["effective_from"] == "2024-02-02", "Should not change"
    assert current["is_current"] == 1


def test_extract_date_preservation_for_historical_records(test_resources):
    """
    Test extract_date is NEVER updated after initial insertion.
    
    Validates that:
    - extract_date represents when the row was first inserted/extracted
    - extract_date is preserved through all T1 and T2 operations
    - extract_date never changes regardless of current/historical status
    """
    resources, db_path = test_resources
    
    # Load all three days
    materialize(all_assets, partition_key="2024-02-01", resources=resources)
    materialize(all_assets, partition_key="2024-02-02", resources=resources)
    result = materialize(all_assets, partition_key="2024-02-03", resources=resources)
    assert result.success
    
    df = get_customer_data(db_path)
    
    # CUST-002: SK=2 inserted on 02-01, closed on 02-02
    cust_002_v1 = df[(df["customer_id"] == "CUST-002") & (df["dim_customer_sk"] == 2)].iloc[0]
    assert cust_002_v1["is_current"] == 0
    assert cust_002_v1["extract_date"] == "2024-02-01", "Should preserve original insert date"
    
    # CUST-002: SK=4 inserted on 02-02, closed on 02-03
    cust_002_v2 = df[(df["customer_id"] == "CUST-002") & (df["dim_customer_sk"] == 4)].iloc[0]
    assert cust_002_v2["is_current"] == 0
    assert cust_002_v2["extract_date"] == "2024-02-02", "Should preserve insert date from 02-02"
    
    # CUST-001: SK=1 inserted on 02-01, had T1 update on 02-02, closed on 02-03
    cust_001_v1 = df[(df["customer_id"] == "CUST-001") & (df["dim_customer_sk"] == 1)].iloc[0]
    assert cust_001_v1["is_current"] == 0
    assert cust_001_v1["extract_date"] == "2024-02-01", "Should preserve original insert date despite T1 updates"
    
    # CUST-003: SK=3 inserted on 02-01, closed on 02-02
    cust_003_v1 = df[(df["customer_id"] == "CUST-003") & (df["dim_customer_sk"] == 3)].iloc[0]
    assert cust_003_v1["is_current"] == 0
    assert cust_003_v1["extract_date"] == "2024-02-01", "Should preserve original insert date"


def test_sequential_sk_assignment(test_resources):
    """Test surrogate keys are assigned sequentially across all operations."""
    resources, db_path = test_resources
    
    # Load all three days
    materialize(all_assets, partition_key="2024-02-01", resources=resources)
    materialize(all_assets, partition_key="2024-02-02", resources=resources)
    result = materialize(all_assets, partition_key="2024-02-03", resources=resources)
    assert result.success
    
    df = get_customer_data(db_path)
    
    # Verify SKs are sequential: 1,2,3,4,5,6,7,8,9
    expected_sks = list(range(1, 10))
    actual_sks = sorted(df["dim_customer_sk"].tolist())
    assert actual_sks == expected_sks, f"SKs should be sequential: expected {expected_sks}, got {actual_sks}"


def test_is_current_consistency(test_resources):
    """Test only latest version of each business key has is_current=1."""
    resources, db_path = test_resources
    
    # Load all three days
    materialize(all_assets, partition_key="2024-02-01", resources=resources)
    materialize(all_assets, partition_key="2024-02-02", resources=resources)
    result = materialize(all_assets, partition_key="2024-02-03", resources=resources)
    assert result.success
    
    df = get_customer_data(db_path)
    
    # Check each business key has exactly one current record
    for customer_id in ["CUST-001", "CUST-002", "CUST-003", "CUST-004", "CUST-005"]:
        customer_versions = df[df["customer_id"] == customer_id]
        current_count = (customer_versions["is_current"] == 1).sum()
        assert current_count == 1, f"{customer_id} should have exactly 1 current record, found {current_count}"


def test_effective_dates_no_gaps(test_resources):
    """Test effective dates have no gaps (effective_to + 1 day = next effective_from)."""
    resources, db_path = test_resources
    
    # Load all three days
    materialize(all_assets, partition_key="2024-02-01", resources=resources)
    materialize(all_assets, partition_key="2024-02-02", resources=resources)
    result = materialize(all_assets, partition_key="2024-02-03", resources=resources)
    assert result.success
    
    df = get_customer_data(db_path)
    
    # Check CUST-002 which has 3 versions
    cust_002 = df[df["customer_id"] == "CUST-002"].sort_values("dim_customer_sk")
    
    # Version 1: 2024-02-01 to 2024-02-01
    assert cust_002.iloc[0]["effective_from"] == "2024-02-01"
    assert cust_002.iloc[0]["effective_to"] == "2024-02-01"
    
    # Version 2: 2024-02-02 to 2024-02-02
    assert cust_002.iloc[1]["effective_from"] == "2024-02-02"
    assert cust_002.iloc[1]["effective_to"] == "2024-02-02"
    
    # Version 3: 2024-02-03 to 2999-12-31
    assert cust_002.iloc[2]["effective_from"] == "2024-02-03"
    assert cust_002.iloc[2]["effective_to"] == "2999-12-31"


def test_final_state_after_three_loads(test_resources):
    """Test final state matches expected output after all three loads."""
    resources, db_path = test_resources
    
    # Load all three days
    materialize(all_assets, partition_key="2024-02-01", resources=resources)
    materialize(all_assets, partition_key="2024-02-02", resources=resources)
    result = materialize(all_assets, partition_key="2024-02-03", resources=resources)
    assert result.success
    
    df = get_customer_data(db_path)
    
    # Should have exactly 9 records total
    assert len(df) == 9, f"Should have 9 total records, found {len(df)}"
    
    # Verify current records (5 customers, each with 1 current version)
    current = df[df["is_current"] == 1].sort_values("customer_id")
    assert len(current) == 5, "Should have 5 current records"
    assert list(current["customer_id"]) == ["CUST-001", "CUST-002", "CUST-003", "CUST-004", "CUST-005"]
    assert list(current["dim_customer_sk"]) == [7, 8, 5, 6, 9]
    
    # Verify historical records (4 closed versions)
    historical = df[df["is_current"] == 0].sort_values("dim_customer_sk")
    assert len(historical) == 4, "Should have 4 historical records"
    assert list(historical["dim_customer_sk"]) == [1, 2, 3, 4]
