"""
Generic ETL framework for building dimensional data warehouses with Dagster.

This module provides reusable factory functions and utilities for:
- Loading raw data from source systems
- Creating staging layers with denormalization
- Building SCD Type 2 dimension tables
- Creating fact tables with dimension lookups

The framework is designed to work with a declarative source model
that defines sources, dimensions, facts, and their relationships.
"""

import datetime
from pathlib import Path
from typing import List

import pandas as pd
from dagster import (
    AssetExecutionContext, InputContext, asset, AssetIn
)

from dagster_etl_framework.source_model import SourceFieldType, DimensionField, SourceModel


# === Utility Functions ===

def log_frame_info(
    context: AssetExecutionContext,
    df: pd.DataFrame,
):
    """Log DataFrame schema information for debugging."""
    # Mark index fields with asterisk
    key_fields = [f"{name}*: {str(df.index.get_level_values(name).dtype)}" for name in df.index.names]
    # Regular column fields
    col_fields = [f"{col}: {str(dtype)}" for col, dtype in df.dtypes.items()]
    # Combine and format
    fields_list = "\n  ".join(key_fields + col_fields)
    context.log.debug(f"\nDataFrame fields:\n  {fields_list}")


def add_hash_column(
    df: pd.DataFrame,
    loc: int,
    columns: List[str],
    hash_field_name: str
) -> pd.DataFrame:
    """Add a hash column for change detection."""
    hash_value = "0"
    if columns:
        # Generate hash as string to work with both SQLite and PostgreSQL VARCHAR columns
        hash_value = pd.util.hash_pandas_object(df[columns], index=False).astype(str)
    df.insert(loc, hash_field_name, hash_value)
    return df


def split_dim_fields(
    fields: List[DimensionField]
) -> tuple[List[str], List[str], List[str]]:
    """Split dimension fields into keys, T1, and T2 field lists."""
    keys = [field.alias or field.name for field in fields if field.type == SourceFieldType.KEY]
    t1_fields = [field.alias or field.name for field in fields if field.type == SourceFieldType.T1]
    t2_fields = [field.alias or field.name for field in fields if field.type == SourceFieldType.T2]
    return keys, t1_fields, t2_fields


# === DataFrame Preparation Functions ===

def prepare_dim_dataframe(
    context: AssetExecutionContext,
    df: pd.DataFrame,
    fields: List[DimensionField],
    dimension_name: str,
) -> pd.DataFrame:
    """Prepare a dataframe for dimension processing with SCD Type 2 metadata."""
    # First, apply any field aliases/renames
    rename_map = {}
    for field in fields:
        if field.alias and field.alias != field.name:
            # Use source_field if specified, otherwise use name
            source_name = field.source_field or field.name
            rename_map[source_name] = field.alias
    
    if rename_map:
        df.rename(columns=rename_map, inplace=True)
    
    keys, t1_fields, t2_fields = split_dim_fields(fields)
    
    # Don't set index here - keep keys as regular columns
    # Add SCD metadata columns as regular columns with dimension-specific name
    dim_key_name = f"dim_{dimension_name}_sk"
    df.insert(0, dim_key_name, -1)
    add_hash_column(df, 1, t1_fields, "t1_hash")
    add_hash_column(df, 2, t2_fields, "t2_hash")
    df.insert(3, "effective_from", None)
    df.insert(4, "effective_to", None)
    df.insert(5, "is_current", True)
    
    # Add audit columns (extract_date should already exist from source, created_at and updated_at will be set during processing)
    if 'created_at' not in df.columns:
        df['created_at'] = None
    if 'updated_at' not in df.columns:
        df['updated_at'] = None
    
    # Store metadata for SCD processing
    df.attrs['keys'] = keys
    df.attrs['t1_fields'] = t1_fields
    df.attrs['t2_fields'] = t2_fields
    df.attrs['dim_key_name'] = dim_key_name


# === SCD Type 2 Processing ===

def process_scd_type2(
    context: AssetExecutionContext,
    new_records: pd.DataFrame,
    warehouse_io_manager,
    table_name: str,
    load_date: pd.Timestamp,
) -> pd.DataFrame:
    """
    Generic SCD Type 2 processor for dimension tables.
    
    Uses UPDATE for T1 changes and T2 record closures, INSERT for new records and T2 new versions.
    
    Args:
        context: Asset execution context for logging
        new_records: DataFrame with new records (must have business keys in attrs['keys'])
        warehouse_io_manager: IO manager for reading existing dimension data
        table_name: Name of the dimension table (e.g., "dim_customer")
        load_date: Date of the current load
        
    Returns:
        DataFrame with SCD Type 2 processing applied and operations metadata
    """
    # Get business keys and dimension key name from metadata
    business_keys = new_records.attrs.get('keys', [])
    dim_key_name = new_records.attrs.get('dim_key_name', 'dim_sk')
    
    # table_name already includes schema prefix (e.g., "t_dim_customer")
    # Format it for SQL (add quotes for databases that need them)
    formatted_table_name = warehouse_io_manager._format_table_name(table_name)
    
    # Try to load existing dimension from database (current records only for comparison)
    try:
        with warehouse_io_manager._get_connection() as conn:
            # Load only current records for SCD comparison
            existing = pd.read_sql(
                f"SELECT * FROM {formatted_table_name} WHERE is_current = TRUE", 
                conn
            )
        context.log.info(f"Loaded {len(existing)} current dimension records")
        
        # Get next dimension key ID - check all records, not just current
        with warehouse_io_manager._get_connection() as conn:
            max_sk_result = pd.read_sql(
                f"SELECT MAX({dim_key_name}) as max_sk FROM {formatted_table_name}",
                conn
            )
        max_sk = max_sk_result['max_sk'].iloc[0]
        next_dim_id = int(max_sk) + 1 if pd.notna(max_sk) else 1
        context.log.info(f"Current MAX({dim_key_name}) = {max_sk}, next_dim_id will start at {next_dim_id}")
        
        # Track operations per row
        result_records = []
        operations = {}
        
        # Debug: Log business keys being used
        context.log.info(f"Business keys for matching: {business_keys}")
        context.log.info(f"Number of existing current records: {len(existing)}")
        if len(existing) > 0:
            context.log.info(f"Existing business key values: {existing[business_keys].values.tolist()}")
        
        for _, new_row in new_records.iterrows():
            # Debug: Log the new record's business key
            new_bk_values = [new_row[k] for k in business_keys]
            context.log.debug(f"Processing record with business key: {new_bk_values}")
            
            # Find matching records by business key
            mask = pd.Series([True] * len(existing))
            for key in business_keys:
                mask &= (existing[key] == new_row[key])
            
            matching = existing[mask]
            
            context.log.debug(f"Found {len(matching)} matching records for business key: {new_bk_values}")
            
            if len(matching) == 0:
                # New business key - INSERT new record
                new_row = new_row.copy()
                new_row[dim_key_name] = next_dim_id
                new_row['effective_from'] = load_date.strftime('%Y-%m-%d')
                new_row['effective_to'] = '2999-12-31'
                new_row['is_current'] = 1  # Use integer 1 instead of True for consistency
                new_row['created_at'] = pd.Timestamp.now()
                new_row['updated_at'] = pd.Timestamp.now()
                
                idx = len(result_records)
                result_records.append(new_row)
                operations[idx] = "INSERT"
                context.log.info(f"New business key: {[new_row[k] for k in business_keys]} -> INSERT with SK={next_dim_id}")
                next_dim_id += 1
                
            else:
                # Get current record
                current = matching.iloc[0].copy()
                
                # Check for changes
                t1_changed = current['t1_hash'] != new_row['t1_hash']
                t2_changed = current['t2_hash'] != new_row['t2_hash']
                
                # Debug: Log hash comparison
                context.log.info(f"Hash comparison for {[new_row[k] for k in business_keys]}: "
                                f"T1 current={current['t1_hash']} new={new_row['t1_hash']} changed={t1_changed}, "
                                f"T2 current={current['t2_hash']} new={new_row['t2_hash']} changed={t2_changed}")
                
                if t2_changed:
                    # T2 change: Close old record (UPDATE) and insert new version (INSERT)
                    # Step 1: UPDATE to close the current record
                    current['effective_to'] = (load_date - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
                    current['is_current'] = 0  # Use integer 0 instead of False for consistency
                    current['updated_at'] = pd.Timestamp.now()
                    
                    idx = len(result_records)
                    result_records.append(current)
                    operations[idx] = "UPDATE"
                    context.log.info(f"T2 change for key: {[new_row[k] for k in business_keys]} -> UPDATE SK={current[dim_key_name]} to close")
                    
                    # Step 2: INSERT new version with new SK
                    new_version = new_row.copy()
                    new_version[dim_key_name] = next_dim_id
                    new_version['effective_from'] = load_date.strftime('%Y-%m-%d')
                    new_version['effective_to'] = '2999-12-31'
                    new_version['is_current'] = 1  # Use integer 1 instead of True for consistency
                    new_version['created_at'] = pd.Timestamp.now()
                    new_version['updated_at'] = pd.Timestamp.now()
                    
                    idx = len(result_records)
                    result_records.append(new_version)
                    operations[idx] = "INSERT"
                    context.log.info(f"T2 change for key: {[new_row[k] for k in business_keys]} -> INSERT new version with SK={next_dim_id}")
                    next_dim_id += 1
                    
                elif t1_changed:
                    # T1 change: UPDATE ALL records for this business key (not just current)
                    # T1 attributes should be consistent across all versions
                    
                    # Load ALL records for this business key from the database
                    with warehouse_io_manager._get_connection() as conn:
                        # Build WHERE clause with proper quoting for column names
                        quote = warehouse_io_manager._get_quote_char()
                        placeholder = warehouse_io_manager._get_placeholder()
                        where_conditions = " AND ".join([f'{quote}{k}{quote} = {placeholder}' for k in business_keys])
                        business_key_values = [new_row[k] for k in business_keys]
                        
                        query = f"SELECT * FROM {formatted_table_name} WHERE {where_conditions}"
                        all_versions = pd.read_sql(query, conn, params=business_key_values)
                    
                    context.log.info(f"T1 change for business key {business_key_values}: updating {len(all_versions)} records")
                    
                    # Update T1 fields for ALL versions of this business key
                    t1_fields = new_records.attrs.get('t1_fields', [])
                    for _, record in all_versions.iterrows():
                        record = record.copy()
                        record['t1_hash'] = new_row['t1_hash']
                        record['updated_at'] = pd.Timestamp.now()
                        
                        # NEVER update extract_date - it represents when the row was first inserted
                        
                        # Update T1 columns
                        for col in t1_fields:
                            if col in new_row.index:
                                record[col] = new_row[col]
                        
                        idx = len(result_records)
                        result_records.append(record)
                        operations[idx] = "UPDATE"
                        context.log.info(f"  -> UPDATE SK={record[dim_key_name]} for business key {business_key_values}")
                else:
                    # No change - no operation needed (skip this record)
                    context.log.debug(f"No change for key: {[new_row[k] for k in business_keys]}")
        
        # If no operations needed, return empty dataframe
        if len(result_records) == 0:
            context.log.info("No changes detected - no operations needed")
            # Return empty dataframe with same structure as new_records
            empty_df = new_records.head(0).copy()
            empty_df.attrs['operations'] = {}
            empty_df.attrs['primary_key'] = [dim_key_name]
            return empty_df
        
        # Build final dataframe
        df = pd.DataFrame(result_records)
        
        # Debug: Check is_current column after DataFrame creation
        context.log.info(f"DEBUG: After DataFrame creation - is_current dtype={df['is_current'].dtype if 'is_current' in df.columns else 'N/A'}")
        if 'is_current' in df.columns:
            context.log.info(f"DEBUG: is_current values: {df['is_current'].tolist()}")
        
    except Exception as e:
        # Table doesn't exist or other error - treat as first load
        context.log.info(f"First load or table not found ({e}) - creating new dimension")
        df = new_records.copy()
        df[dim_key_name] = range(1, len(df) + 1)
        df['effective_from'] = load_date.strftime('%Y-%m-%d')
        df['effective_to'] = '2999-12-31'
        df['is_current'] = 1  # Use integer 1 instead of True for consistency
        current_time = pd.Timestamp.now()
        df['created_at'] = current_time
        df['updated_at'] = current_time
        
        # All records are INSERTs on first load
        operations = {idx: "INSERT" for idx in range(len(df))}
    
    # Reorder columns: dim_key, business_keys, effective_from, effective_to, is_current, t1_hash, t2_hash, remaining
    scd_cols = [dim_key_name] + business_keys + ['effective_from', 'effective_to', 'is_current', 't1_hash', 't2_hash']
    remaining_cols = [c for c in df.columns if c not in scd_cols]
    ordered_cols = scd_cols + remaining_cols
    
    # Replace pandas NA types with None for database compatibility, but preserve boolean False values
    # Convert column by column to avoid treating False as NA
    for col in df.columns:
        if df[col].dtype == 'bool':
            # For boolean columns, only convert actual NA values to None, not False
            df[col] = df[col].apply(lambda x: None if pd.isna(x) else x)
        else:
            # For other columns, use standard NA replacement
            df[col] = df[col].where(pd.notna(df[col]), None)
    
    # Debug: Check is_current after NA replacement
    if 'is_current' in df.columns:
        context.log.info(f"DEBUG: After NA replacement - is_current values: {df['is_current'].tolist()}")
    
    # Reorder columns
    df = df[ordered_cols]
    
    # CRITICAL: Reset index to ensure it matches operations dict keys (0, 1, 2, ...)
    df = df.reset_index(drop=True)
    
    # Set metadata for IO manager
    df.attrs['operations'] = operations
    df.attrs['primary_key'] = [dim_key_name]
    df.attrs['business_keys'] = business_keys  # For index creation on business keys
    
    context.log.info(f"SCD Type 2 result: {len(df)} operations "
                    f"(inserts={sum(1 for op in operations.values() if op == 'INSERT')}, "
                    f"updates={sum(1 for op in operations.values() if op == 'UPDATE')})")
    
    # Debug: Log operations and corresponding SK values
    for idx in range(len(df)):
        op = operations.get(idx, "INSERT")
        sk_val = df.iloc[idx][dim_key_name]
        context.log.info(f"Operation {idx}: {op} with {dim_key_name}={sk_val}")
    
    return df


# === Source Model Utilities ===

def denormalize(
    context: AssetExecutionContext,
    ldf: pd.DataFrame,
    rdf: pd.DataFrame,
    source_model: SourceModel,
) -> pd.DataFrame:
    """Join two DataFrames based on source model relationships."""
    # Get source objects from attrs (set by SourceCsvIOManager)
    lsrc = ldf.attrs.get('source')
    rsrc = rdf.attrs.get('source')
    
    if not lsrc:
        raise ValueError("Source not found in attrs for left DataFrame")
    if not rsrc:
        raise ValueError("Source not found in attrs for right DataFrame")
    
    lnm = lsrc.name
    rnm = rsrc.name

    rels = source_model.relations.get(lnm, {})
    if not rels:
        raise ValueError(f"No relations defined for source: {lnm}")

    rel = rels.get(rnm)
    if not rel:
        raise ValueError(f"Relation not found for source: {lnm} to {rnm}")
    
    # Get the join keys
    left_keys = rel.foreign_key
    right_keys = rsrc.primary_key
    
    if not right_keys:
        raise ValueError(f"Source {rnm} does not have primary_key defined")
    
    if len(left_keys) != len(right_keys):
        raise ValueError(
            f"Foreign key count ({len(left_keys)}) does not match primary key count ({len(right_keys)}) "
            f"for relation {lnm} -> {rnm}"
        )
    
    # Reset index to make all columns available for merging
    ldf_reset = ldf.reset_index(drop=True)
    rdf_reset = rdf.reset_index(drop=True)
    
    # Preserve dtypes before join
    left_dtypes = ldf_reset.dtypes.to_dict()
    right_dtypes = rdf_reset.dtypes.to_dict()
    
    # Use merge instead of join to preserve all columns
    df = ldf_reset.merge(
        rdf_reset,
        how="left",
        left_on=left_keys,
        right_on=right_keys,
        suffixes=('', '_dup')
    )
    duplicates = [col for col in df.columns if col.endswith("_dup")]
    if duplicates:
        df = df.drop(columns=duplicates)
    
    # Restore dtypes after join
    dtypes_to_apply = {}
    for col in df.columns:
        if col in left_dtypes:
            dtypes_to_apply[col] = left_dtypes[col]
        elif col in right_dtypes:
            dtypes_to_apply[col] = right_dtypes[col]
    
    for col, dtype in dtypes_to_apply.items():
        if col in df.columns and df[col].dtype != dtype:
            try:
                df[col] = df[col].astype(dtype)
            except Exception as e:
                context.log.warning(f"Could not restore dtype for {col}: {e}")
    
    # Preserve attrs from the left DataFrame (primary source)
    df.attrs = ldf.attrs.copy()
    
    log_frame_info(context, df)
    return df


def get_dimension_fields(
    model: SourceModel,
    dimension_name: str,
    dfs: List[pd.DataFrame]
) -> List[DimensionField]:
    """Extract field definitions from a dimension based on the sources in the DataFrames."""
    dimension = model.dimensions.get(dimension_name)
    if not dimension:
        raise ValueError(f"Dimension not found: {dimension_name}")
    
    fields: List[DimensionField] = []
    for idx, df in enumerate(dfs):
        source_obj = df.attrs.get('source')
        if not source_obj:
            raise ValueError("DataFrame missing 'source' attribute in attrs")
        
        src_name = source_obj.name
        dim_source = dimension.sources.get(src_name)
        if not dim_source:
            raise ValueError(f"Source {src_name} not found in dimension {dimension_name}")
        
        # Only get KEY fields from the first (primary) DataFrame
        if idx == 0:
            fields.extend([
                field for field in dim_source.fields 
                if field.type in (SourceFieldType.KEY, SourceFieldType.T1, SourceFieldType.T2)
            ])
        else:
            fields.extend([
                field for field in dim_source.fields 
                if field.type in (SourceFieldType.T1, SourceFieldType.T2)
            ])
    
    return fields


# === Asset Factory Functions ===

def create_raw_asset(source_name: str, source_model: SourceModel, daily_partitions):
    """Factory function to create raw asset loaders for each source."""
    @asset(
        name=f"raw_{source_name}",
        description=f"Raw {source_name.replace('_', ' ')} from source CSV",
        metadata={"source_name": source_name},
        partitions_def=daily_partitions,
        required_resource_keys={"source_csv_io_manager"}
    )
    def _raw_asset(context: AssetExecutionContext) -> pd.DataFrame:
        source = source_model.sources[source_name]
        
        # Get partition date from context
        load_date = datetime.datetime.strptime(context.partition_key, '%Y-%m-%d').date()
        
        input_context = InputContext(
            name=f"{source_name}_csv",
            asset_key=context.asset_key,
            upstream_output=None,
            dagster_type=None,
            resource_config=None,
            resources=context.resources,
            log_manager=context.log,
            definition_metadata={
                "load_date": load_date,
                "source": source,
            }
        )
        return context.resources.source_csv_io_manager.load_input(input_context)
    
    return _raw_asset


def create_dimension_staging_asset(dimension_name: str, source_model: SourceModel, daily_partitions):
    """Factory function to create dimension staging assets with denormalization.
    
    Args:
        dimension_name: Name of dimension (without 'dim_' prefix)
        source_model: Source model configuration
        daily_partitions: Partition definition
    """
    # Dimension name is already without prefix in source model
    dimension = source_model.dimensions[dimension_name]
    source_names = list(dimension.sources.keys())
    
    asset_ins = {
        f"raw_{src}": AssetIn(key=f"raw_{src}")
        for src in source_names
    }
    
    @asset(
        name=f"stg_{dimension_name}",
        description=f"{dimension_name.replace('_', ' ').title()} dimension data from all extract dates",
        ins=asset_ins,
        partitions_def=daily_partitions,
    )
    def _staging_asset(context: AssetExecutionContext, **kwargs) -> pd.DataFrame:
        dfs = [kwargs[f"raw_{src}"] for src in source_names]
        
        # Start with the first (primary) DataFrame
        df = dfs[0]
        
        # Sequentially denormalize remaining DataFrames
        for additional_df in dfs[1:]:
            df = denormalize(context, df, additional_df, source_model)
        
        # Add extract_date from partition key
        partition_date = pd.to_datetime(context.partition_key).date()
        df['extract_date'] = partition_date
        
        # Get dimension fields and prepare for SCD Type 2
        fields = get_dimension_fields(source_model, dimension_name, dfs)
        prepare_dim_dataframe(context, df, fields, dimension_name)
        
        log_frame_info(context, df)
        return df
    
    return _staging_asset


def create_scd_type2_dimension_asset(
    dimension_name: str,
    source_model: SourceModel,
    daily_partitions,
):
    """Factory function to create SCD Type 2 dimension assets.
    
    Args:
        dimension_name: Name of dimension (without 'dim_' prefix)
        source_model: Source model configuration (for consistency, not used)
        daily_partitions: Partition definition
    """
    # Add dim_ prefix for asset name
    asset_name = f"dim_{dimension_name}"
    staging_asset_key = f"stg_{dimension_name}"
    description = f"{dimension_name.replace('_', ' ').title()} dimension with SCD Type 2"
    
    @asset(
        name=asset_name,
        description=description,
        io_manager_key="warehouse_io_manager",
        partitions_def=daily_partitions,
        ins={staging_asset_key: AssetIn(key=staging_asset_key)},
    )
    def dimension_asset(
        context: AssetExecutionContext,
        **kwargs,
    ) -> pd.DataFrame:
        """Generic SCD Type 2 dimension asset."""
        load_date = pd.Timestamp(context.partition_key)
        staging_data = kwargs[staging_asset_key]
        
        warehouse_io_manager = context.resources.warehouse_io_manager
        
        # Get the table name with schema prefix (e.g., "t_dim_customer")
        table_name = f"t_{asset_name}"
        
        return process_scd_type2(
            context=context,
            new_records=staging_data,
            warehouse_io_manager=warehouse_io_manager,
            table_name=table_name,
            load_date=load_date,
        )
    
    return dimension_asset


def create_fact_staging_asset(fact_name: str, source_model: SourceModel, daily_partitions):
    """Factory function to create fact staging assets with denormalization.
    
    Args:
        fact_name: Name of fact (without 'fact_' prefix)
        source_model: Source model configuration
        daily_partitions: Partition definition
    """
    # Fact name is already without prefix in source model
    fact = source_model.facts[fact_name]
    source_names = list(fact.sources.keys())
    
    # Determine the primary source based on foreign key relationships
    primary_source = None
    related_sources = []
    
    for src_name in source_names:
        src_relations = source_model.relations.get(src_name, {})
        if src_relations:
            for rel_target, rel in src_relations.items():
                if rel_target in source_names and rel_target != src_name:
                    if primary_source is None:
                        primary_source = src_name
                    if rel_target not in related_sources:
                        related_sources.append(rel_target)
    
    ordered_sources = [primary_source] + [s for s in source_names if s != primary_source] if primary_source else source_names
    
    asset_ins = {
        f"raw_{src}": AssetIn(key=f"raw_{src}")
        for src in ordered_sources
    }
    
    @asset(
        name=f"stg_{fact_name}",
        description=f"{fact_name.replace('_', ' ').title()} fact staging with denormalized sources",
        ins=asset_ins,
        partitions_def=daily_partitions,
    )
    def _staging_asset(context: AssetExecutionContext, **kwargs) -> pd.DataFrame:
        dfs = [kwargs[f"raw_{src}"] for src in ordered_sources]
        
        # Start with the first (primary) DataFrame
        df = dfs[0]
        
        # Sequentially denormalize remaining DataFrames
        for additional_df in dfs[1:]:
            df = denormalize(context, df, additional_df, source_model)
        
        # Add date field from partition key
        partition_date = pd.to_datetime(context.partition_key).date()
        df['date'] = partition_date
        
        context.log.info(f"Added 'date' field with value {partition_date}. Final columns: {list(df.columns)}")
        return df
    
    return _staging_asset


def create_fact_table_asset(fact_name: str, source_model: SourceModel, daily_partitions):
    """Factory function to create fact table assets with dimension lookups.
    
    Args:
        fact_name: Name of fact (without 'fact_' prefix)
        source_model: Source model configuration
        daily_partitions: Partition definition
    """
    # Fact name is already without prefix in source model
    asset_name = f"fact_{fact_name}"
    fact = source_model.facts[fact_name]
    staging_name = f"stg_{fact_name}"
    
    # Derive dimension lookups from source relations
    dimension_lookups = []
    
    for source_name in fact.sources.keys():
        source_relations = source_model.relations.get(source_name, {})
        
        for related_source, relation in source_relations.items():
            for dim_name, dimension in source_model.dimensions.items():
                dim_sources = list(dimension.sources.keys())
                if dim_sources and dim_sources[0] == related_source:
                    # Use dimension name directly (already without prefix)
                    dimension_lookups.append({
                        'dimension': f"dim_{dim_name}",
                        'business_keys': relation.foreign_key,
                        'surrogate_key': f"dim_{dim_name}_sk",
                        'lookup_strategy': 'current'
                    })
                    break
    
    # Date dimension is NOT added as a surrogate key lookup
    # Facts use their natural date columns (e.g., order_date) which directly reference dim_date_sk
    
    # Create asset dependencies - EXCLUDE dim_date (no lookup needed)
    dimension_deps = [lookup['dimension'] for lookup in dimension_lookups]
    dimension_ins = {dim: AssetIn(key=dim) for dim in dimension_deps}
    dimension_ins[staging_name] = AssetIn(key=staging_name)
    
    @asset(
        name=asset_name,
        description=f"{fact_name.replace('_', ' ').title()} fact table with dimension surrogate keys",
        io_manager_key="warehouse_io_manager",
        partitions_def=daily_partitions,
        ins=dimension_ins,
        deps=["dim_date"],  # Ensure date dimension exists before materializing facts
    )
    def _fact_asset(context: AssetExecutionContext, **kwargs) -> pd.DataFrame:
        """Create fact table for single partition by joining staging with dimensions."""
        staging_df = kwargs[staging_name]
        dim_dataframes = {dim: kwargs[dim] for dim in dimension_ins.keys() if dim != staging_name}
        
        fact_df = staging_df.copy()
        
        # Date dimension: Map order_date to dim_date_sk
        # Since date dimension uses date as surrogate key, dim_date_sk = order_date
        if 'order_date' in fact_df.columns:
            fact_df['dim_date_sk'] = pd.to_datetime(fact_df['order_date']).dt.date
            context.log.info(f"Mapped order_date to dim_date_sk for {len(fact_df)} records")
        
        partition_key = context.partition_key
        partition_date = datetime.datetime.strptime(partition_key, '%Y-%m-%d').date()
        
        # Perform dimension lookups for other dimensions
        for lookup in dimension_lookups:
            dim_name = lookup['dimension']
            business_keys = lookup['business_keys']
            surrogate_key = lookup['surrogate_key']
            strategy = lookup.get('lookup_strategy', 'merge')
            
            dim_df = dim_dataframes[dim_name]
            
            # Get the dimension key column name from the dimension dataframe
            # It should be named dim_<name>_sk (e.g., dim_customers_sk, dim_products_sk)
            dim_key_cols = [col for col in dim_df.columns if col.startswith('dim_') and col.endswith('_sk')]
            if not dim_key_cols:
                raise ValueError(f"Could not find dimension key column in {dim_name}")
            dim_key_name = dim_key_cols[0]
            
            if strategy == "current":
                # For SCD Type 2 dimensions, lookup current version
                dim_lookup = dim_df[dim_df['is_current'] == True][business_keys + [dim_key_name]].copy()
                dim_lookup = dim_lookup.rename(columns={dim_key_name: surrogate_key})
            else:
                # For regular dimensions, do direct merge on business keys
                dim_lookup = dim_df[business_keys + [dim_key_name]].copy()
                dim_lookup = dim_lookup.rename(columns={dim_key_name: surrogate_key})
            
            fact_df = fact_df.merge(dim_lookup, on=business_keys, how='left')
            
            missing_count = fact_df[surrogate_key].isna().sum()
            if missing_count > 0:
                context.log.warning(f"{missing_count} records have missing {surrogate_key} ({dim_name})")
        
        # Collect all foreign keys that should be removed (they've been replaced by surrogate keys)
        foreign_keys_to_remove = set()
        for lookup in dimension_lookups:
            foreign_keys_to_remove.update(lookup['business_keys'])
        
        # Collect output columns from fact definition (excluding foreign keys)
        output_columns = []
        for source_name, source in fact.sources.items():
            for field in source.fields:
                field_name = field.alias or field.name
                if field_name in fact_df.columns and field_name not in output_columns:
                    # Exclude foreign keys that have been replaced by surrogate keys
                    if field_name not in foreign_keys_to_remove:
                        output_columns.append(field_name)
        
        # Order: keys first, then other surrogate keys, then remaining attributes
        key_fields = [field.alias or field.name for source in fact.sources.values() for field in source.fields if field.type == SourceFieldType.KEY]
        other_surrogate_keys = [lookup['surrogate_key'] for lookup in dimension_lookups]
        
        # Add dim_date_sk if it exists in the dataframe (special case for date dimension)
        if 'dim_date_sk' in fact_df.columns and 'dim_date_sk' not in other_surrogate_keys:
            other_surrogate_keys.append('dim_date_sk')
            
        all_surrogate_keys = other_surrogate_keys
        other_fields = [f for f in output_columns if f not in key_fields]
        ordered_columns = key_fields + other_surrogate_keys + other_fields
        final_columns = [col for col in ordered_columns if col in fact_df.columns]
        
        # Create final dataframe with proper types
        fact_final = pd.DataFrame()
        for col in final_columns:
            if col in all_surrogate_keys:
                # Handle special case for date surrogate keys
                if col == 'dim_date_sk':
                    # Date surrogate keys should remain as dates
                    fact_final[col] = pd.to_datetime(fact_df[col]).dt.date
                else:
                    # Regular surrogate keys are integers
                    fact_final[col] = fact_df[col].astype('Int64')
            else:
                fact_final[col] = fact_df[col]
        
        # Add audit columns
        fact_final['extract_date'] = partition_date
        current_time = pd.Timestamp.now()
        fact_final['created_at'] = current_time
        fact_final['updated_at'] = current_time
        
        # Log summary
        context.log.info(f"Created {fact_name} with {len(fact_final)} records for partition {context.partition_key}")
        for lookup in dimension_lookups:
            valid_count = fact_final[lookup['surrogate_key']].notna().sum()
            context.log.info(f"  - {valid_count} with valid {lookup['surrogate_key']}")
        
        # Set primary key for SQLite table creation
        fact_final.attrs['primary_key'] = key_fields
        
        return fact_final
    
    return _fact_asset


def create_date_dimension_asset(partitions_def):
    """Factory function to create date dimension asset.
    
    The date dimension is partitioned and generates a single row for each partition date.
    This ensures the date dimension exists BEFORE facts are created, which is critical for:
    - Foreign key constraints in databases
    - Query optimizer performance
    - Proper dimensional modeling (dimensions before facts)
    
    Args:
        partitions_def: DailyPartitionsDefinition for the date dimension
    
    Returns:
        Partitioned date dimension asset that generates one row per partition
    """
    @asset(
        name="dim_date",
        description="Date dimension - partitioned by date, one row per partition",
        partitions_def=partitions_def,
        io_manager_key="warehouse_io_manager",
    )
    def _date_dimension_asset(context: AssetExecutionContext) -> pd.DataFrame:
        """Generate date dimension row for the current partition date."""
        
        # Get the partition date
        partition_key = context.partition_key
        partition_date = datetime.datetime.strptime(partition_key, '%Y-%m-%d').date()
        
        context.log.info(f"Generating date dimension row for partition: {partition_date}")
        
        # Generate date attributes
        year = partition_date.year
        month = partition_date.month
        day = partition_date.day
        quarter = (month - 1) // 3 + 1
        day_of_week = partition_date.weekday()
        day_of_year = partition_date.timetuple().tm_yday
        week_of_year = partition_date.isocalendar()[1]
        
        row = {
            'dim_date_sk': partition_date,
            'is_current': False,  # Initially set to False; will be updated to True for latest date after successful load
            'year': year,
            'quarter': quarter,
            'month': month,
            'day': day,
            'day_of_week': day_of_week,
            'day_of_year': day_of_year,
            'week_of_year': week_of_year,
            'day_name': partition_date.strftime('%A'),
            'month_name': partition_date.strftime('%B'),
            'is_weekend': day_of_week >= 5,
            'is_month_start': day == 1,
            'is_month_end': (partition_date + datetime.timedelta(days=1)).day == 1,
            'is_quarter_start': month in [1, 4, 7, 10] and day == 1,
            'is_quarter_end': month in [3, 6, 9, 12] and (partition_date + datetime.timedelta(days=1)).day == 1,
            'is_year_start': month == 1 and day == 1,
            'is_year_end': month == 12 and day == 31
        }
        
        df = pd.DataFrame([row])
        
        # Set up DataFrame metadata for date dimension processing
        df.attrs['primary_key'] = ['dim_date_sk']
        df.attrs['load_mode'] = 'date_dim'  # Special mode for date dimension
        
        context.log.info(f"Generated date dimension row for {partition_date}")
        return df
    
    return _date_dimension_asset
