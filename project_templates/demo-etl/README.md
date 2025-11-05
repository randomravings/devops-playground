# Demo ETL (Dagster)

A parameterized Dagster ETL pipeline demonstrating SCD Type 2 transformations with date-based snapshot processing. Designed for local development and production deployment with PostgreSQL.

This project uses the **etl-framework** for all operations (similar to how demo-dw uses dbci-tools). All scripts and commands are provided by the framework.

## Features

- **Parameterized Execution**: Configure via environment variables, run tags, or Dagster UI
- **Date-Based Snapshots**: Process multiple extract dates in a single run
- **SCD Type 2**: Track historical changes with version, effective_to, is_current
- **Flexible File Loading**: Automatic pattern matching for various file naming conventions
- **Output Isolation**: Direct output to custom directories for testing/production separation
- **Production Ready**: Same code works with CSV, Parquet, or PostgreSQL

## Project Layout

```text
demo-etl/
├── demo_etl/              # ETL application code
│   ├── __init__.py
│   ├── assets.py          # Asset definitions (wiring layer)
│   ├── resources.py       # Resource configurations
│   └── source_model.yaml  # Data model definition
├── tests/                 # Test suite
│   ├── __init__.py
│   ├── test_assets.py     # Integration tests
│   └── data/              # Test fixtures
│       ├── 20240201/      # Initial snapshot
│       └── 20240310/      # Delta snapshot
├── dagster.yaml           # Dagster configuration
├── pyproject.toml         # Python package definition
└── workspace.yaml         # Dagster workspace definition

Note: All scripts (setup, run, test, teardown) are provided by ../etl-framework/
```

## Prerequisites

- Python 3.12
- etl-framework in sibling directory (`../etl-framework`)
- Optional: PostgreSQL 16+ for warehouse backend

## Getting Started

All commands are executed from the **etl-framework** directory, targeting this project instance.

### Recipe 1: Setup Environment

**CSV Warehouse (recommended for local development):**

```bash
cd ../etl-framework
./run.sh setup --project-dir ../demo-etl --framework-path . --warehouse csv
```

**PostgreSQL Warehouse:**

```bash
cd ../etl-framework
./run.sh setup --project-dir ../demo-etl --framework-path . --warehouse postgres
```

This will:

- Create virtual environment (`.venv/`)
- Install framework and project dependencies
- Create `.env` from template
- Launch Dagster UI at <http://localhost:3000>

### Recipe 2: Run Pipeline for Specific Date

```bash
cd ../etl-framework

# Run for specific date
./run.sh run --project-dir ../demo-etl -d 2024-02-01

# Run with custom input/output
./run.sh run --project-dir ../demo-etl -i tests/data -d 2024-02-01 -o .data/warehouse
```

### Recipe 3: Run Tests

```bash
cd ../etl-framework

# Run all tests
./run.sh test --project-dir ../demo-etl

# Run with verbose output
./run.sh test --project-dir ../demo-etl -v

# Run specific test file
./run.sh test --project-dir ../demo-etl tests/test_assets.py -v
```

### Recipe 4: Teardown Environment

```bash
cd ../etl-framework

# Interactive teardown (prompts for confirmation)
./run.sh teardown --project-dir ../demo-etl

# Force teardown without confirmation
./run.sh teardown --project-dir ../demo-etl --force

# Stop UI only, keep environment
./run.sh teardown --project-dir ../demo-etl --ui-only
```
cd demo-etl

# Interactive teardown (prompts for confirmation)
../etl-framework/run.sh teardown --project-dir .

# Force teardown without confirmation
../etl-framework/run.sh teardown --project-dir . --force

# Stop UI only, keep environment
../etl-framework/run.sh teardown --project-dir . --ui-only
```

## Configuration

The project uses environment variables for flexible configuration across different environments.

### Warehouse Backend Selection

Choose between CSV files or PostgreSQL for warehouse storage by setting `WAREHOUSE_TYPE`:

**CSV Mode (default)**:
```bash
# No configuration needed - CSV is the default
# Or explicitly set:
WAREHOUSE_TYPE=csv
WAREHOUSE_PATH=.data/warehouse
```

**PostgreSQL Mode**:
```bash
WAREHOUSE_TYPE=postgres
POSTGRES_HOST=localhost
POSTGRES_DB=warehouse
POSTGRES_USER=etl_user
POSTGRES_PASSWORD=your_password
POSTGRES_SCHEMA=public
```

### Environment Variables

- **SOURCE_DATA_PATH**: Path to source CSV files (default: `tests/data`)
- **DAGSTER_STORAGE_PATH**: Path for Dagster internal storage (default: `.dagster/storage`)
- **WAREHOUSE_TYPE**: Warehouse backend - `csv` or `postgres` (default: `csv`)
- **WAREHOUSE_PATH**: Path for CSV warehouse files (default: `.data/warehouse`)
- **POSTGRES_HOST**: PostgreSQL host (default: `localhost`)
- **POSTGRES_DB**: PostgreSQL database (default: `warehouse`)
- **POSTGRES_USER**: PostgreSQL user (default: `etl_user`)
- **POSTGRES_PASSWORD**: PostgreSQL password (default: `changeme`)
- **POSTGRES_SCHEMA**: PostgreSQL schema (default: `public`)

### Quick Setup

1. Copy the appropriate template:
   - For CSV: `cp .env.example .env`
   - For PostgreSQL: `cp .env.postgres.example .env`
2. Edit `.env` with your settings
3. Run: `source .env && ./setup.sh`

See `.env.example` and `.env.postgres.example` for details.

## Getting Started

### Setup and Launch Dagster UI

**Fastest path:**

```bash
./setup.sh  # Sets up .venv, installs deps, starts Dagster UI on port 3000
```

This script is **idempotent** - safe to run multiple times. It will:
- Create Python 3.12 virtual environment (if needed)
- Install dependencies (if needed)
- Launch Dagster UI at http://localhost:3000

**Options:**
```bash
./setup.sh           # Setup and launch UI
./setup.sh --no-ui   # Setup only, no UI launch
./setup.sh --help    # Show help
```

### Stop and Cleanup

**Stop Dagster UI:**
```bash
./teardown.sh --ui-only --force  # Stop Dagster, keep environment
```

**Full cleanup:**
```bash
./teardown.sh  # Interactive - prompts for confirmation
./teardown.sh --force  # Skip confirmation prompts
```

This will:
- Stop any running Dagster processes
- Remove virtual environment
- Clean up temporary files and caches
- Preserve warehouse/ directory (ETL outputs)

### Using Dagster UI

Once setup.sh launches the UI, navigate to <http://localhost:3000>:

1. Navigate to Assets
2. Select the assets you want to materialize
3. Click "Materialize" to run the pipeline
4. View logs and outputs in real-time

See [QUICKSTART.md](QUICKSTART.md) for detailed examples.

## Testing

The project includes comprehensive tests for SCD2 transformation logic:

```bash
./run.sh && source .venv/bin/activate

# Run all tests
pytest

# Run only SCD2 unit tests (no database required)
pytest tests/test_scd2_logic.py -v

# Run integration tests
pytest tests/test_assets.py -v
```

**Key insight:** SCD2 transformations are tested with pure pandas DataFrames—no database needed! The same transformation logic works regardless of whether data comes from CSV, Parquet, or PostgreSQL.

See [TESTING.md](TESTING.md) for:
- Complete testing strategy
- Production database patterns (SQLite, TestContainers, PostgreSQL)
- How to adapt for PostgreSQL target in production

## Assets Overview

The pipeline processes 6 source assets and produces 3 transformed assets:

**Source Assets** (loaded from CSV snapshots):
- `customers` - Customer dimension with temporal attributes
- `customer_addresses` - Customer address history  
- `products` - Product master with price changes
- `product_groups` - Product categorization
- `orders` - Order headers
- `order_items` - Order line items

**Transformed Assets** (saved as Parquet):
- `customers_scd` - Customer dimension with SCD Type 2 (version, effective_to, is_current)
- `products_scd` - Product dimension with SCD Type 2
- `customer_order_summary` - Aggregated customer order metrics with current attributes

All transformations are **idempotent** and **date-parameterized** for production use.
