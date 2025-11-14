"""
Asset Definitions - Wiring Layer

This module wires the generic ETL framework to specific model configurations.
All reusable logic lives in etl_framework.py.
"""

import datetime
import dagster as dg
import pandas as pd
from dagster import (
    AssetExecutionContext, DailyPartitionsDefinition, Definitions, asset, 
    define_asset_job, load_assets_from_current_module
)

from dagster_etl_framework import (
    load_source_model,
    create_raw_asset,
    create_dimension_staging_asset,
    create_scd_type2_dimension_asset,
    create_fact_staging_asset,
    create_fact_table_asset,
    create_date_dimension_asset,
)

# === Configuration ===

daily_partitions = DailyPartitionsDefinition(start_date="2000-01-01")
_SOURCE_MODEL = load_source_model("demo_etl/source_model.yaml")

# === Raw Assets ===

raw_customer_addresses = create_raw_asset("customer_addresses", _SOURCE_MODEL, daily_partitions)
raw_customers = create_raw_asset("customers", _SOURCE_MODEL, daily_partitions)
raw_product_groups = create_raw_asset("product_groups", _SOURCE_MODEL, daily_partitions)
raw_products = create_raw_asset("products", _SOURCE_MODEL, daily_partitions)
raw_orders = create_raw_asset("orders", _SOURCE_MODEL, daily_partitions)
raw_order_items = create_raw_asset("order_items", _SOURCE_MODEL, daily_partitions)

# === Staging Assets ===

stg_customer = create_dimension_staging_asset("customer", _SOURCE_MODEL, daily_partitions)
stg_product = create_dimension_staging_asset("product", _SOURCE_MODEL, daily_partitions)
stg_order = create_fact_staging_asset("order", _SOURCE_MODEL, daily_partitions)

# === Dimension Assets ===

dim_customer = create_scd_type2_dimension_asset("customer", _SOURCE_MODEL, daily_partitions)
dim_product = create_scd_type2_dimension_asset("product", _SOURCE_MODEL, daily_partitions)

# Date dimension - partitioned, generates one row per partition date
# Must exist BEFORE facts for proper dimensional modeling and FK constraints
dim_date = create_date_dimension_asset(daily_partitions)

# === Fact Assets ===

fact_order = create_fact_table_asset("order", _SOURCE_MODEL, daily_partitions)

# === Definitions ===

all_assets = load_assets_from_current_module()

job = define_asset_job(name="demo_etl_job", selection="*")

# Resources are provided at materialization time by CLI or tests
# Don't bind resources at module import time - this happens before .env is loaded
definitions = Definitions(
    assets=all_assets,
    jobs=[job],
    resources={}  # Resources will be provided when materializing
)
