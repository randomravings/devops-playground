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
    hash_value = 0
    if columns:
        hash_value = pd.util.hash_pandas_object(df[columns], index=False)
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
    dim_key_name = f"dim_{dimension_name}_id"
    df.insert(0, dim_key_name, -1)
    add_hash_column(df, 1, t1_fields, "t1_hash")
    add_hash_column(df, 2, t2_fields, "t2_hash")
    df.insert(3, "valid_from", pd.NA)
    df.insert(4, "valid_to", pd.NA)
    df.insert(5, "is_current", True)
    
    # Store metadata for SCD processing
    df.attrs['keys'] = keys
    df.attrs['t1_fields'] = t1_fields
    df.attrs['t2_fields'] = t2_fields
    df.attrs['dim_key_name'] = dim_key_name


# === SCD Type 2 Processing ===

def process_scd_type2(
    context: AssetExecutionContext,
    new_records: pd.DataFrame,
    warehouse_path: Path,
    dim_file_name: str,
    load_date: pd.Timestamp,
) -> pd.DataFrame:
    """
    Generic SCD Type 2 processor for dimension tables.
    
    Args:
        context: Asset execution context for logging
        new_records: DataFrame with new records (must have business keys in attrs['keys'])
        warehouse_path: Path to warehouse directory
        dim_file_name: Name of the dimension CSV file (e.g., "dim_customers.csv")
        load_date: Date of the current load
        
    Returns:
        DataFrame with SCD Type 2 processing applied
    """
    # Get business keys and dimension key name from metadata
    business_keys = new_records.attrs.get('keys', [])
    dim_key_name = new_records.attrs.get('dim_key_name', 'dim_id')
    dim_file = warehouse_path / dim_file_name
    
    if dim_file.exists():
        # Load existing dimension
        existing = pd.read_csv(dim_file)
        context.log.info(f"Loaded existing dimension with {len(existing)} rows")
        
        # Get next dimension key ID
        next_dim_id = existing[dim_key_name].max() + 1
        
        # Process each new record
        result_records = []
        
        for _, new_row in new_records.iterrows():
            # Find matching records by business key
            mask = pd.Series([True] * len(existing))
            for key in business_keys:
                mask &= (existing[key] == new_row[key])
            
            matching = existing[mask]
            
            if len(matching) == 0:
                # New business key - insert new record
                new_row[dim_key_name] = next_dim_id
                new_row['valid_from'] = load_date.strftime('%Y-%m-%d')
                new_row['valid_to'] = '2999-12-31'
                new_row['is_current'] = True
                result_records.append(new_row)
                next_dim_id += 1
                context.log.info(f"New business key: {[new_row[k] for k in business_keys]}")
            else:
                # Get current record
                current = matching[matching['is_current'] == True].iloc[0]
                
                # Check for changes
                t1_changed = current['t1_hash'] != new_row['t1_hash']
                t2_changed = current['t2_hash'] != new_row['t2_hash']
                
                if t2_changed:
                    # T2 change: Close old record and insert new
                    current['valid_to'] = (load_date - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
                    current['is_current'] = False
                    result_records.append(current)
                    
                    new_row[dim_key_name] = next_dim_id
                    new_row['valid_from'] = load_date.strftime('%Y-%m-%d')
                    new_row['valid_to'] = '2999-12-31'
                    new_row['is_current'] = True
                    result_records.append(new_row)
                    next_dim_id += 1
                    context.log.info(f"T2 change for key: {[new_row[k] for k in business_keys]}")
                elif t1_changed:
                    # T1 change: Update existing record in place
                    current['t1_hash'] = new_row['t1_hash']
                    # Update T1 columns (non-descriptive attributes)
                    for col in new_row.index:
                        if col not in [dim_key_name, 'valid_from', 'valid_to', 'is_current', 't1_hash', 't2_hash'] + business_keys:
                            current[col] = new_row[col]
                    result_records.append(current)
                    context.log.info(f"T1 change for key: {[new_row[k] for k in business_keys]}")
                else:
                    # No change - keep existing record
                    result_records.append(current)
        
        # Add all historical (non-current) records
        historical = existing[existing['is_current'] == False]
        for _, row in historical.iterrows():
            result_records.append(row)
        
        # Build final dataframe
        df = pd.DataFrame(result_records)
        
    else:
        # First load - all records are new
        context.log.info("First load - creating new dimension")
        df = new_records.copy()
        df[dim_key_name] = range(1, len(df) + 1)
        df['valid_from'] = load_date.strftime('%Y-%m-%d')
        df['valid_to'] = '2999-12-31'
        df['is_current'] = True
    
    # Reorder columns: dim_key, business_keys, valid_from, valid_to, is_current, t1_hash, t2_hash, remaining
    scd_cols = [dim_key_name] + business_keys + ['valid_from', 'valid_to', 'is_current', 't1_hash', 't2_hash']
    remaining_cols = [c for c in df.columns if c not in scd_cols]
    ordered_cols = scd_cols + remaining_cols
    
    context.log.info(f"Final dimension has {len(df)} rows ({len(df[df['is_current'] == True])} current)")
    return df[ordered_cols]


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
    # Add dim_ prefix for asset name and file name
    asset_name = f"dim_{dimension_name}"
    dim_file_name = f"dim_{dimension_name}.csv"
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
        warehouse_path = Path(warehouse_io_manager.base_path)
        
        return process_scd_type2(
            context=context,
            new_records=staging_data,
            warehouse_path=warehouse_path,
            dim_file_name=dim_file_name,
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
                        'surrogate_key': f"{dim_name}_dim_id",
                        'lookup_strategy': 'current'
                    })
                    break
    
    # Add date dimension - but NOT as a dependency or lookup!
    # The date_dim_id is populated directly from the partition date
    date_dim_id_column = 'date_dim_id'
    
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
        
        # Add date_dim_id directly from partition date (no lookup needed)
        partition_key = context.partition_key
        partition_date = datetime.datetime.strptime(partition_key, '%Y-%m-%d').date()
        fact_df[date_dim_id_column] = partition_date
        context.log.info(f"Populated {date_dim_id_column} with partition date: {partition_date}")
        
        # Perform dimension lookups for other dimensions
        for lookup in dimension_lookups:
            dim_name = lookup['dimension']
            business_keys = lookup['business_keys']
            surrogate_key = lookup['surrogate_key']
            strategy = lookup.get('lookup_strategy', 'merge')
            
            dim_df = dim_dataframes[dim_name]
            
            # Get the dimension key column name from the dimension dataframe
            # It should be named dim_<name>_id (e.g., dim_customers_id, dim_products_id)
            dim_key_cols = [col for col in dim_df.columns if col.startswith('dim_') and col.endswith('_id')]
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
        
        # Order: keys first, then date_dim_id, then other surrogate keys, then remaining attributes
        key_fields = [field.alias or field.name for source in fact.sources.values() for field in source.fields if field.type == SourceFieldType.KEY]
        other_surrogate_keys = [lookup['surrogate_key'] for lookup in dimension_lookups]
        all_surrogate_keys = [date_dim_id_column] + other_surrogate_keys
        other_fields = [f for f in output_columns if f not in key_fields]
        ordered_columns = key_fields + [date_dim_id_column] + other_surrogate_keys + other_fields
        final_columns = [col for col in ordered_columns if col in fact_df.columns]
        
        # Create final dataframe with proper types
        fact_final = pd.DataFrame()
        for col in final_columns:
            if col in all_surrogate_keys:
                # Date dimension keys are dates, not integers
                if col == date_dim_id_column:
                    fact_final[col] = fact_df[col]
                else:
                    fact_final[col] = fact_df[col].astype('Int64')
            else:
                fact_final[col] = fact_df[col]
        
        # Log summary
        context.log.info(f"Created {fact_name} with {len(fact_final)} records for partition {context.partition_key}")
        context.log.info(f"Populated {date_dim_id_column} directly from partition date")
        for lookup in dimension_lookups:
            valid_count = fact_final[lookup['surrogate_key']].notna().sum()
            context.log.info(f"  - {valid_count} with valid {lookup['surrogate_key']}")
        
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
            'dim_date_id': partition_date,
            'year': year,
            'month': month,
            'day': day,
            'quarter': quarter,
            'day_of_week': day_of_week,
            'day_of_year': day_of_year,
            'week_of_year': week_of_year,
            'month_name': partition_date.strftime('%B'),
            'day_name': partition_date.strftime('%A'),
            'is_weekend': day_of_week >= 5,
            'is_month_start': day == 1,
            'is_month_end': (partition_date + datetime.timedelta(days=1)).day == 1,
            'is_quarter_start': month in [1, 4, 7, 10] and day == 1,
            'is_quarter_end': month in [3, 6, 9, 12] and (partition_date + datetime.timedelta(days=1)).day == 1,
            'is_year_start': month == 1 and day == 1,
            'is_year_end': month == 12 and day == 31,
        }
        
        df = pd.DataFrame([row])
        context.log.info(f"Generated date dimension row for {partition_date}")
        return df
    
    return _date_dimension_asset
