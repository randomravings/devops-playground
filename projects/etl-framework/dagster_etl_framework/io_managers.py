"""IO Managers for Dagster ETL Framework."""

from pathlib import Path
from typing import Optional, Dict, List
from abc import ABC, abstractmethod
import datetime
import pandas as pd
import io

try:
    import psycopg
    HAS_PSYCOPG = True
except ImportError:
    HAS_PSYCOPG = False

try:
    import sqlite3
    HAS_SQLITE3 = True
except ImportError:
    HAS_SQLITE3 = False

import dagster as dg
from dagster import ConfigurableIOManager, InputContext, OutputContext


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


class BaseSqlIOManager(ConfigurableIOManager, ABC):
    """Base class for SQL-based IO managers with shared logic.
    
    This is a pure data persistence layer. The framework (in framework.py) is responsible
    for computing what needs to be inserted, updated, or deleted. This IO manager simply
    executes those operations based on row-level metadata in the DataFrame.
    
    DataFrame metadata (in df.attrs):
    - "operations": Dict[index, str] - Maps row index to operation: "INSERT" or "UPDATE"
    - "primary_key": List[str] - Column names that form the primary key for UPDATEs
    
    If no "operations" metadata is present, defaults to INSERT all rows (append mode).
    
    InputContext metadata:
    - "load_mode": "table" | "dim" - Controls which columns to load (default: "table")
    """
    
    schema: str = "public"
    
    def _sanitize_value(self, val, col_name: str = None):
        """Sanitize pandas types for database compatibility.
        
        Converts pandas-specific types to standard Python types:
        - pandas NA types (pd.NA, pd.NaT) → None (NULL)
        - pandas Timestamp → Python datetime
        
        Args:
            val: Value to sanitize
            col_name: Optional column name for type-specific conversions (overridden in subclasses)
        """
        if pd.isna(val):
            return None
        elif isinstance(val, pd.Timestamp):
            return val.to_pydatetime()
        else:
            return val
    
    def _table_for(self, context: OutputContext | InputContext) -> str:
        """Get table name with 't_' prefix from asset key."""
        asset_name = context.asset_key.path[-1]
        return f"t_{asset_name}"
    
    @abstractmethod
    def _get_connection(self):
        """Get database connection. Must be implemented by subclass."""
        pass
    
    @abstractmethod
    def _create_table_if_not_exists(self, conn, context: OutputContext, df: pd.DataFrame, table: str):
        """Create table if it doesn't exist. Must be implemented by subclass."""
        pass
    
    @abstractmethod
    def _bulk_insert_impl(self, conn, cursor, context: OutputContext, df: pd.DataFrame, table: str):
        """Database-specific bulk insert implementation."""
        pass
    
    @abstractmethod
    def _get_quote_char(self) -> str:
        """Get the quote character for identifiers (e.g., '"' for PostgreSQL, '`' for SQLite)."""
        pass
    
    @abstractmethod
    def _get_placeholder(self) -> str:
        """Get the placeholder character for parameterized queries (e.g., '%s' for PostgreSQL, '?' for SQLite)."""
        pass
    
    @abstractmethod
    def _format_table_name(self, table: str) -> str:
        """Format table name with schema prefix if needed."""
        pass
    
    def handle_output(self, context: OutputContext, obj):
        df = obj if isinstance(obj, pd.DataFrame) else pd.DataFrame(obj)
        table = self._table_for(context)
        
        # Check for operation metadata from framework
        operations = df.attrs.get("operations", {})
        primary_key = df.attrs.get("primary_key", [])
        
        # Handle empty dataframe (no operations needed)
        if len(df) == 0:
            context.log.info(f"Empty dataframe - no operations needed for {table}")
            return
        
        with self._get_connection() as conn:
            # Create table if needed (subclass-specific behavior)
            self._create_table_if_not_exists(conn, context, df, table)
            
            cursor = conn.cursor()
            try:
                # Check if this is a date dimension load
                load_mode = df.attrs.get("load_mode", None)
                
                if not operations:
                    # No operations specified - default to INSERT all rows (fact table mode)
                    self._bulk_insert(conn, cursor, context, df, table)
                else:
                    # Framework has computed operations - execute them (SCD Type 2 or other)
                    self._execute_operations(conn, cursor, context, df, table, operations, primary_key)
                
                # Special post-processing for date dimension
                if load_mode == "date_dim" and table.endswith("_date"):
                    self._update_date_dimension_current_flags(conn, cursor, context, table)
                
                conn.commit()
            finally:
                cursor.close()
    
    def _update_date_dimension_current_flags(self, conn, cursor, context: OutputContext, table: str):
        """Update date dimension to have only the latest date as current.
        
        This implements SCD Type 2 pattern for date dimensions where only the most recent
        date should have is_current = TRUE, all others should be FALSE.
        """
        quote = self._get_quote_char()
        table_name = self._format_table_name(table)
        
        # First, set all dates to is_current = FALSE
        cursor.execute(f'UPDATE {table_name} SET is_current = FALSE')
        
        # Then, set only the latest date to is_current = TRUE
        cursor.execute(f'''
            UPDATE {table_name} 
            SET is_current = TRUE 
            WHERE dim_date_sk = (SELECT MAX(dim_date_sk) FROM {table_name})
        ''')
        
        context.log.info(f"Updated date dimension current flags in {table_name}")
    
    def _bulk_insert(self, conn, cursor, context: OutputContext, df: pd.DataFrame, table: str):
        """Bulk insert all rows - fast path for facts and initial loads."""
        self._bulk_insert_impl(conn, cursor, context, df, table)
        context.log.info(f"Bulk inserted {len(df)} rows into {self.schema}.{table}")
    
    def _execute_operations(self, conn, cursor, context: OutputContext, df: pd.DataFrame, 
                           table: str, operations: dict, primary_key: list):
        """Execute row-by-row INSERT or UPDATE operations as computed by the framework."""
        if not primary_key:
            raise ValueError("primary_key must be specified in df.attrs for UPDATE operations")
        
        inserts = 0
        updates = 0
        quote = self._get_quote_char()
        placeholder = self._get_placeholder()
        table_name = self._format_table_name(table)
        
        # Debug: Log operations summary
        insert_count = sum(1 for op in operations.values() if op == "INSERT")
        update_count = sum(1 for op in operations.values() if op == "UPDATE")
        context.log.info(f"Executing operations: {insert_count} INSERTs, {update_count} UPDATEs")
        
        for idx, row in df.iterrows():
            operation = operations.get(idx, "INSERT")
            
            # Debug: Log row index and operation
            sk_col = primary_key[0] if primary_key else None
            sk_value = row[sk_col] if sk_col and sk_col in row.index else "unknown"
            context.log.info(f"Row {idx}: {operation} with {sk_col}={sk_value}")
            
            if operation == "INSERT":
                cols = ", ".join([f'{quote}{c}{quote}' for c in df.columns])
                placeholders = ", ".join([placeholder] * len(df.columns))
                values = [self._sanitize_value(row[c], c) for c in df.columns]
                
                # Debug: Log the SK value being inserted
                sk_col = primary_key[0] if primary_key else None
                sk_value = row[sk_col] if sk_col and sk_col in row.index else "unknown"
                context.log.debug(f"INSERT operation: {sk_col}={sk_value}")
                
                cursor.execute(
                    f'INSERT INTO {table_name} ({cols}) VALUES ({placeholders})',
                    values
                )
                inserts += 1
                
            elif operation == "UPDATE":
                # Build SET clause for all non-key columns
                update_cols = [c for c in df.columns if c not in primary_key]
                set_clause = ", ".join([f'{quote}{c}{quote} = {placeholder}' for c in update_cols])
                
                # Build WHERE clause for primary key
                where_clause = " AND ".join([f'{quote}{k}{quote} = {placeholder}' for k in primary_key])
                
                # Values: update columns first, then key columns (sanitize all)
                values = [self._sanitize_value(row[c], c) for c in update_cols] + [self._sanitize_value(row[k], k) for k in primary_key]
                
                cursor.execute(
                    f'UPDATE {table_name} SET {set_clause} WHERE {where_clause}',
                    values
                )
                updates += 1
            else:
                raise ValueError(f"Unknown operation: {operation}")
        
        context.log.info(f"Executed operations on {table_name}: inserts={inserts}, updates={updates}")
    
    def load_input(self, context: InputContext):
        table = self._table_for(context)
        metadata = context.definition_metadata or {}
        load_mode = metadata.get("load_mode", "table")
        quote = self._get_quote_char()
        table_name = self._format_table_name(table)
        
        with self._get_connection() as conn:
            if load_mode == "dim":
                # Extract dimension name from asset key (e.g., "dim_customers" -> "dim_customers")
                # Table name already has t_ prefix (e.g., "t_dim_customers")
                asset_name = context.asset_key.path[-1]
                
                # Load dimension-specific columns for SCD processing
                # SK column is named after the asset (e.g., "dim_customers_sk")
                sk_col = f"{asset_name}_sk"
                columns = [
                    sk_col,
                    "effective_from",
                    "effective_to",
                    "t1_hash",
                    "t2_hash"
                ]
                # Add business key columns from metadata if provided
                business_keys = metadata.get("business_keys", [])
                for key in business_keys:
                    if key not in columns:
                        columns.append(key)
                
                col_list = ", ".join([f'{quote}{c}{quote}' for c in columns])
                query = f'SELECT {col_list} FROM {table_name}'
                context.log.info(f"Loading dimension with mode=dim: {columns}")
            else:
                # Load all columns (table mode)
                query = f'SELECT * FROM {table_name}'
                context.log.info(f"Loading table with mode=table: SELECT *")
            
            return pd.read_sql_query(query, conn)


class PostgresIOManager(BaseSqlIOManager):
    """IO manager for persisting DataFrames to PostgreSQL.
    
    Does NOT support automatic table creation - tables must be created via schema migration tools.
    """
    host: str
    db: str
    user: str
    password: str
    schema: str = "public"

    def _get_connection(self):
        if not HAS_PSYCOPG:
            raise ImportError("psycopg is required for PostgresIOManager. Install with: pip install psycopg[binary]")
        return psycopg.connect(host=self.host, dbname=self.db, user=self.user, password=self.password)
    
    def _get_quote_char(self) -> str:
        return '"'
    
    def _get_placeholder(self) -> str:
        return '%s'
    
    def _format_table_name(self, table: str) -> str:
        """Format table name with schema prefix for PostgreSQL."""
        return f'"{self.schema}"."{table}"'
    
    def _create_table_if_not_exists(self, conn, context: OutputContext, df: pd.DataFrame, table: str):
        """PostgreSQL does not support automatic table creation."""
        pass  # Tables must exist - managed by schema migration tools
    
    def _sanitize_value(self, val, col_name: str = None):
        """PostgreSQL-specific value sanitization.
        
        Converts framework types to PostgreSQL-compatible types:
        - pandas NA types (pd.NA, pd.NaT) → None (NULL)
        - pandas Timestamp → Python datetime
        - is_current integers (0/1) → PostgreSQL boolean (False/True)
        """
        # Handle pandas NA first
        if pd.isna(val):
            return None
        elif isinstance(val, pd.Timestamp):
            return val.to_pydatetime()
        # Convert is_current from int to boolean for PostgreSQL
        elif col_name == 'is_current' and isinstance(val, (int, bool)):
            return bool(val)
        else:
            return val
    
    def _bulk_insert_impl(self, conn, cursor, context: OutputContext, df: pd.DataFrame, table: str):
        """PostgreSQL-specific bulk insert using COPY."""
        # Sanitize pandas types for PostgreSQL with column-aware conversion
        data_rows = []
        for row in df.itertuples(index=False, name=None):
            clean_row = []
            for i, val in enumerate(row):
                col_name = df.columns[i]
                clean_val = self._sanitize_value(val, col_name)
                clean_row.append(clean_val)
            data_rows.append(clean_row)
        
        # Create a clean DataFrame with sanitized data
        df_clean = pd.DataFrame(data_rows, columns=df.columns)
        
        # Explicitly specify columns in COPY command to match DataFrame
        cols = ", ".join([f'"{c}"' for c in df_clean.columns])
        copy_cmd = f'COPY "{self.schema}"."{table}" ({cols}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE)'
        
        with cursor.copy(copy_cmd) as cp:
            cp.write(df_clean.to_csv(index=False))


class SqliteIOManager(BaseSqlIOManager):
    """IO manager for persisting DataFrames to SQLite.
    
    Supports automatic table creation for testing and development scenarios.
    Tables are created based on DataFrame schema if they don't exist.
    """
    db_path: str
    schema: str = "main"  # SQLite default schema
    
    def _get_connection(self):
        if not HAS_SQLITE3:
            raise ImportError("sqlite3 is required for SqliteIOManager")
        # Ensure parent directory exists
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(str(db_file))
    
    def _get_quote_char(self) -> str:
        return '"'  # SQLite uses double quotes for identifiers
    
    def _get_placeholder(self) -> str:
        return '?'
    
    def _format_table_name(self, table: str) -> str:
        """Format table name for SQLite (no schema prefix needed for main schema)."""
        return f'"{table}"'
    
    def _create_table_if_not_exists(self, conn, context: OutputContext, df: pd.DataFrame, table: str):
        """Create table if it doesn't exist based on DataFrame schema."""
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,)
        )
        
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            # Table doesn't exist - create it
            context.log.info(f"Creating table {table} in SQLite")
            
            # Build CREATE TABLE statement from DataFrame dtypes
            col_defs = []
            for col, dtype in df.dtypes.items():
                sql_type = self._pandas_dtype_to_sqlite(dtype)
                col_defs.append(f'"{col}" {sql_type}')
            
            # Add PRIMARY KEY constraint if specified in attrs
            primary_key = df.attrs.get('primary_key', [])
            if primary_key:
                pk_cols = ', '.join([f'"{col}"' for col in primary_key])
                col_defs.append(f'PRIMARY KEY ({pk_cols})')
            
            create_sql = f'CREATE TABLE "{table}" ({", ".join(col_defs)})'
            cursor.execute(create_sql)
            conn.commit()
            context.log.info(f"Created table {table} with {len(df.columns)} columns and PK={primary_key}")
            
            # Create index on business keys if specified in attrs
            business_keys = df.attrs.get('business_keys', [])
            if business_keys:
                idx_cols = ', '.join([f'"{col}"' for col in business_keys])
                idx_name = f'idx_{table}_business_keys'
                create_idx_sql = f'CREATE INDEX "{idx_name}" ON "{table}" ({idx_cols})'
                cursor.execute(create_idx_sql)
                conn.commit()
                context.log.info(f"Created index {idx_name} on {table} ({', '.join(business_keys)})")
        
        cursor.close()
    
    def _pandas_dtype_to_sqlite(self, dtype) -> str:
        """Map pandas dtype to SQLite type."""
        dtype_str = str(dtype)
        
        if 'int' in dtype_str.lower():
            return 'INTEGER'
        elif 'float' in dtype_str.lower():
            return 'REAL'
        elif 'bool' in dtype_str.lower():
            return 'INTEGER'  # SQLite uses 0/1 for boolean
        elif 'datetime' in dtype_str.lower():
            return 'TEXT'  # Store as ISO format string
        elif 'date' in dtype_str.lower():
            return 'TEXT'  # Store as ISO format string
        else:
            return 'TEXT'  # Default to TEXT for strings and other types
    
    def _bulk_insert_impl(self, conn, cursor, context: OutputContext, df: pd.DataFrame, table: str):
        """SQLite bulk insert using executemany."""
        # Prepare data - convert to list of tuples
        placeholders = ", ".join(["?"] * len(df.columns))
        cols = ", ".join([f'"{c}"' for c in df.columns])
        
        insert_sql = f'INSERT INTO "{table}" ({cols}) VALUES ({placeholders})'
        
        # Convert DataFrame to list of tuples, sanitizing pandas types for SQLite
        data = []
        for row in df.itertuples(index=False, name=None):
            clean_row = [self._sanitize_value(val) for val in row]
            data.append(tuple(clean_row))
        
        cursor.executemany(insert_sql, data)
