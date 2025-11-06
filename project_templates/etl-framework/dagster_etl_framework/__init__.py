"""Dagster ETL Framework - Modular ETL with built-in SCD Type 2 support.

This package provides a declarative framework for building ETL pipelines in Dagster
with automatic handling of:
- Source file loading with schema validation
- Raw data ingestion to staging
- SCD Type 2 dimension processing
- Fact table construction with dimension lookups
- Date dimension generation
- Flexible storage backends (CSV, PostgreSQL)

Example:
    from dagster_etl_framework import (
        create_raw_asset,
        create_dimension_staging_asset,
        create_scd_type2_dimension_asset,
        create_fact_staging_asset,
        create_fact_table_asset,
        create_date_dimension_asset,
        SourceModel,
        Source,
        Dimension,
        Fact,
    )
    
    # Define your source model
    source_model = SourceModel(
        sources={...},
        dimensions={...},
        facts={...},
    )
    
    # Create assets using factory functions
    raw_customers = create_raw_asset(source_model.sources["customers"])
    dim_customers_staging = create_dimension_staging_asset(source_model.dimensions["dim_customers"])
    dim_customers = create_scd_type2_dimension_asset(source_model.dimensions["dim_customers"])
"""

# Core framework functions
from .framework import (
    create_raw_asset,
    create_dimension_staging_asset,
    create_scd_type2_dimension_asset,
    create_fact_staging_asset,
    create_fact_table_asset,
    create_date_dimension_asset,
    log_frame_info,
    add_hash_column,
    split_dim_fields,
    prepare_dim_dataframe,
    process_scd_type2,
    denormalize,
    get_dimension_fields,
)

# Source model definitions
from .source_model import (
    SourceFieldType,
    SourceField,
    Source,
    Relation,
    DimensionField,
    DimensionSource,
    Dimension,
    FactField,
    FactSource,
    DimensionLookup,
    Fact,
    SourceModel,
)

# IO Managers
from .io_managers import (
    CsvIOManager,
    SourceCsvIOManager,
    PostgresIOManager,
)

# Source model loader
from .source_model_loader import (
    load_source_model,
    build_source_model_from_dict,
)

# Resources factory
from .resources import (
    create_resources,
)

# CLI utilities
from .cli import (
    run_partition,
    run_partition_cli,
    create_partition_cli,
)

# Model validation
from .model_validator import (
    ModelValidator,
    validate_model,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
)

from .hcl_parser import (
    HclParser,
    HclTable,
    HclColumn,
)

__version__ = "0.1.0"

__all__ = [
    # Asset factory functions
    "create_raw_asset",
    "create_dimension_staging_asset",
    "create_scd_type2_dimension_asset",
    "create_fact_staging_asset",
    "create_fact_table_asset",
    "create_date_dimension_asset",
    
    # Utility functions
    "log_frame_info",
    "add_hash_column",
    "split_dim_fields",
    "prepare_dim_dataframe",
    "process_scd_type2",
    "denormalize",
    "get_dimension_fields",
    
    # Source model types
    "SourceFieldType",
    "SourceField",
    "Source",
    "Relation",
    "DimensionField",
    "DimensionSource",
    "Dimension",
    "FactField",
    "FactSource",
    "DimensionLookup",
    "Fact",
    "SourceModel",
    
    # IO Managers
    "CsvIOManager",
    "SourceCsvIOManager",
    "PostgresIOManager",
    
    # Source model loader
    "load_source_model",
    "build_source_model_from_dict",
    
    # Resources factory
    "create_resources",
    
    # CLI utilities
    "run_partition",
    "run_partition_cli",
    "create_partition_cli",
    
    # Model validation
    "ModelValidator",
    "validate_model",
    "ValidationResult",
    "ValidationIssue",
    "ValidationSeverity",
    "HclParser",
    "HclTable",
    "HclColumn",
]
