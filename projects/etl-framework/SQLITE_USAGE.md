# SQLite IO Manager Usage

The SQLite IO Manager provides automatic table creation for testing and development without requiring a PostgreSQL database. **This is now the default warehouse backend for the framework.**

## Features

- **Default backend**: SQLite is the default warehouse type (no configuration needed)
- **Automatic table creation**: Tables are created based on DataFrame schema if they don't exist
- **Testing friendly**: No external database required - just a file
- **Same interface**: Works with the same framework operations as PostgreSQL
- **DRY architecture**: Shares common SQL logic with PostgreSQL IO Manager via `BaseSqlIOManager`

## Key Differences from PostgreSQL IO Manager

| Feature | PostgreSQL | SQLite |
|---------|-----------|--------|
| Default | No (production) | **Yes (testing/dev)** |
| Table Creation | Manual (via schema migration tools) | Automatic |
| Use Case | Production deployment | Testing & development |
| Schema Support | Full schema support | Main schema only |
| Performance | Optimized for concurrent access | Single-writer model |

## Usage

### Environment Configuration (Optional)

SQLite is the default. To customize the database path:

```bash
# Optional - defaults to .data/warehouse.db
export SQLITE_DB_PATH=.data/warehouse.db

# To use PostgreSQL instead:
export WAREHOUSE_TYPE=postgres
export POSTGRES_HOST=localhost
export POSTGRES_DB=warehouse
export POSTGRES_USER=etl_user
export POSTGRES_PASSWORD=your_password
```

### Example

```python
from dagster_etl_framework import create_resources

# In your Dagster definitions - SQLite is used by default
resources = create_resources(
    source_data_path="tests/data",
    dagster_storage_path=".dagster/storage"
)

# Database will be created at .data/warehouse.db
```

### Testing

SQLite works out of the box for tests:

```bash
# No environment setup needed - uses SQLite by default
# Optionally customize paths:
export SQLITE_DB_PATH=.data/test_warehouse.db
export SOURCE_DATA_PATH=tests/data

# Run your Dagster job
dagster dev

# Clean up test database
rm .data/test_warehouse.db
```

## Migration Note

**The CSV IO Manager has been removed** from the framework. If you previously used CSV for testing:
- Update your code to use `SqliteIOManager` instead of `CsvIOManager`
- Remove YAML config overrides for `warehouse_io_manager`
- SQLite provides the same benefits with better testing capabilities (SQL queries, transactions, etc.)

## Architecture

Both `PostgresIOManager` and `SqliteIOManager` extend `BaseSqlIOManager`, which provides:

- Common operation execution (INSERT/UPDATE based on framework metadata)
- Shared load logic (table vs dim mode)
- Consistent interface for both databases

Database-specific implementations:
- Connection management (`_get_connection`)
- Table creation behavior (`_create_table_if_not_exists`)
- Bulk insert optimization (`_bulk_insert_impl`)
- SQL dialect details (`_get_quote_char`, `_get_placeholder`, `_format_table_name`)
