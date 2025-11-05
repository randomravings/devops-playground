"""IO Managers for Dagster ETL Framework."""

from pathlib import Path
from typing import Optional, Dict, List
import datetime
import pandas as pd

try:
    import psycopg
    HAS_PSYCOPG = True
except ImportError:
    HAS_PSYCOPG = False

import dagster as dg
from dagster import ConfigurableIOManager, InputContext, OutputContext


class CsvIOManager(ConfigurableIOManager):
    """IO manager that stores DataFrames as CSV files.
    
    Warehouse files are NOT partitioned - they are single accumulated files
    that get overwritten/appended with each partition run.
    """
    base_path: str = ".data/warehouse"
    
    def _path_for(self, context: dg.OutputContext | dg.InputContext) -> Path:
        name = context.asset_key.to_user_string().replace("/", "__")
        # Warehouse files do NOT have partition suffixes - single accumulated files
        return Path(self.base_path) / f"{name}.csv"

    def handle_output(self, context: dg.OutputContext, obj):
        p = self._path_for(context)
        p.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to DataFrame if needed
        df_new = obj if isinstance(obj, pd.DataFrame) else pd.DataFrame(obj)
        
        # Check if this is a fact table (partitioned append) or dimension (partitioned replace)
        asset_key = context.asset_key.path if hasattr(context, 'asset_key') else []
        asset_name = asset_key[-1] if asset_key else ""
        is_fact = asset_name.startswith("fact_")
        
        # Check if partitioned
        is_partitioned = hasattr(context, 'partition_key') and context.partition_key is not None
        
        # For partitioned assets:
        # - Facts: APPEND (each partition adds new rows)
        # - Dimensions (including dim_date): REPLACE per partition (upsert behavior)
        if is_partitioned and is_fact:
            # For partitioned facts: APPEND only (each partition is unique data)
            if p.exists():
                context.log.info(f"Appending partition {context.partition_key} to fact: {p}")
                df_new.to_csv(p, mode='a', header=False, index=False)
                context.log.info(f"Appended {len(df_new)} rows from partition {context.partition_key}")
            else:
                context.log.info(f"Creating new CSV: {p}")
                df_new.to_csv(p, index=False)
                context.log.info(f"Wrote {len(df_new)} rows to {p}")
        else:
            # For dimensions:
            # - dim_date (partitioned, natural key): APPEND (one row per partition)
            # - SCD Type 2 dimensions (partitioned inputs, snapshot output): REPLACE
            is_date_dim = asset_name == "dim_date"
            
            if p.exists() and is_partitioned and is_date_dim:
                # Date dimension: append new rows for this partition
                context.log.info(f"Appending partition {context.partition_key} to dimension: {p}")
                df_new.to_csv(p, mode='a', header=False, index=False)
                context.log.info(f"Appended {len(df_new)} rows from partition {context.partition_key}")
            else:
                # SCD Type 2 dimensions or non-partitioned: replace entire snapshot
                context.log.info(f"Replacing snapshot: {p}")
                df_new.to_csv(p, index=False)
                context.log.info(f"Wrote {len(df_new)} rows to {p}")

    def load_input(self, context: dg.InputContext):
        p = self._path_for(context)
        return pd.read_csv(p)


class SourceCsvIOManager(ConfigurableIOManager):
    """Read-only IO manager for loading source CSV files with schema control and validation.
    
    This IO manager is designed specifically for reading external source CSV files
    with explicit schema control (dtypes, datetime parsing, field projection) and
    extract_date validation. It does not support writing - sources are external data.
    
    Usage:
        The load_date and source metadata are passed via InputContext.metadata:
        - metadata["load_date"]: datetime.date or str (YYYY-MM-DD)
        - metadata["source"]: Source object from source_model
    """
    
    base_path: str = "data/input"
    
    def handle_output(self, context: OutputContext, obj):
        """Not supported - source files are read-only external data."""
        raise NotImplementedError(
            "SourceCsvIOManager is read-only. Source data should not be written via this IO manager."
        )
    
    def load_input(self, context: InputContext) -> pd.DataFrame:
        """Load a CSV file with schema control, validation, and extract_date checking.
        
        This method encapsulates the full source CSV loading logic:
        - Resolves file path based on load_date and source external name
        - Loads CSV with explicit schema from Source object
        - Validates extract_date matches load_date
        - Drops extract_date column (not needed downstream)
        - Stores source name in DataFrame attrs
        - Logs DataFrame structure
        
        The load_date and source are retrieved from context.metadata:
        - metadata["load_date"]: datetime.date or str (YYYY-MM-DD)
        - metadata["source"]: Source object from source_model
        
        Returns:
            DataFrame with specified schema, validated and ready for processing
        """
        # Extract metadata from context
        metadata = context.definition_metadata or {}
        load_date_raw = metadata.get("load_date")
        source = metadata.get("source")
        
        if not load_date_raw:
            raise ValueError("SourceCsvIOManager requires 'load_date' in InputContext.metadata")
        if not source:
            raise ValueError("SourceCsvIOManager requires 'source' in InputContext.metadata")
        
        # Convert load_date to datetime.date if it's a string
        if isinstance(load_date_raw, str):
            load_date = datetime.datetime.strptime(load_date_raw, '%Y-%m-%d').date()
        else:
            load_date = load_date_raw
        
        # Format date as YYYYMMDD for folder name
        load_date_str = load_date.strftime('%Y%m%d')
        
        # Build path: base_path / YYYYMMDD / source_ext_name.csv
        csv_path = Path(self.base_path) / load_date_str / source.ext_name
        
        if not csv_path.exists():
            raise FileNotFoundError(f"Source CSV file not found: {csv_path}")
        
        context.log.info(f"Loading source CSV: {csv_path} for source: {source.name}")
        
        # Derive parameters from Source object
        usecols = [field.name for field in source.fields.values()]
        datetimes = [field.name for field in source.fields.values() if field.dtype == 'datetime64[ns]']
        dtypes = {field.name: field.dtype for field in source.fields.values() 
                  if field.dtype and field.dtype != 'datetime64[ns]'}
        
        # Build read_csv kwargs
        kwargs = {}
        if usecols:
            kwargs['usecols'] = usecols
        if dtypes:
            kwargs['dtype'] = dtypes
        if datetimes:
            kwargs['parse_dates'] = datetimes
        
        df = pd.read_csv(csv_path, **kwargs)
        context.log.info(f"Loaded {len(df)} rows with columns: {list(df.columns)}")
        
        # Validate extract_date if present
        if 'extract_date' in df.columns:
            unique_dates = df['extract_date'].unique()
            if len(unique_dates) != 1:
                raise ValueError(
                    f"CSV {source.name} contains multiple extract dates: {unique_dates}. "
                    f"Expected exactly one extract_date."
                )
            # Convert datetime to date for comparison
            extract_date = pd.to_datetime(unique_dates[0]).date()
            if extract_date != load_date:
                raise ValueError(
                    f"CSV {source.name} extract_date {extract_date} does not match "
                    f"expected load_date {load_date}"
                )
            context.log.info(
                f"Validated extract_date={load_date} for {source.name}"
            )
            # Drop extract_date from dataframe (not needed in dimension processing)
            df.drop('extract_date', axis=1, inplace=True)
        
        # Store entire source model in attrs for later reference
        df.attrs['source'] = source
        
        # Log DataFrame structure for debugging
        self._log_frame_info(context, df)
        
        return df
    
    def _log_frame_info(self, context: InputContext, df: pd.DataFrame):
        """Log DataFrame structure with index and column information."""
        # Mark index fields with asterisk
        key_fields = [f"{name}*: {str(df.index.get_level_values(name).dtype)}" 
                      for name in df.index.names]
        # Regular column fields
        col_fields = [f"{col}: {str(dtype)}" for col, dtype in df.dtypes.items()]
        # Combine and format
        fields_list = "\n  ".join(key_fields + col_fields)
        context.log.debug(f"\nDataFrame fields:\n  {fields_list}")


class PostgresIOManager(ConfigurableIOManager):
    """IO manager that stores DataFrames in PostgreSQL tables."""
    host: str
    db: str
    user: str
    password: str
    schema: str = "public"

    def _table_for(self, context: OutputContext | InputContext) -> str:
        # map asset key to table name however you like
        return context.asset_key.path[-1]

    def handle_output(self, context: OutputContext, obj):
        if not HAS_PSYCOPG:
            raise ImportError("psycopg is required for PostgresIOManager. Install with: pip install psycopg[binary]")
        
        table = self._table_for(context)
        with psycopg.connect(host=self.host, dbname=self.db, user=self.user, password=self.password) as conn:
            with conn.cursor() as cur:
                # naive: recreate table + copy
                df = obj if isinstance(obj, pd.DataFrame) else pd.DataFrame(obj)
                cols = ", ".join([f'"{c}" text' for c in df.columns])
                cur.execute(f'DROP TABLE IF EXISTS "{self.schema}"."{table}"')
                cur.execute(f'CREATE TABLE "{self.schema}"."{table}" ({cols})')
                # fast path: use copy
                with cur.copy(f'COPY "{self.schema}"."{table}" FROM STDIN WITH (FORMAT CSV, HEADER TRUE)') as cp:
                    cp.write(df.to_csv(index=False))
            conn.commit()
        context.log.info(f"Wrote PG: {self.schema}.{table}")

    def load_input(self, context: InputContext):
        if not HAS_PSYCOPG:
            raise ImportError("psycopg is required for PostgresIOManager. Install with: pip install psycopg[binary]")
        
        table = self._table_for(context)
        with psycopg.connect(host=self.host, dbname=self.db, user=self.user, password=self.password) as conn:
            return pd.read_sql_query(f'SELECT * FROM "{self.schema}"."{table}"', conn)
