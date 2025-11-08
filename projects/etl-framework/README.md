# ETL Framework - CLI Reference

Dagster-based ETL framework for data pipeline management with SCD Type 2 support.

## CLI Verbs

### INSTALL

**Purpose**: Install and setup the ETL framework environment.

**Usage**: `etl INSTALL`

**Actions**:

- Creates `.venv` in the etl-framework directory
- Installs framework dependencies and package in development mode
- Checks Python version compatibility
- Sets up the etl-framework for use

### SETUP

**Purpose**: Setup project environment and dependencies.

**Usage**: `etl SETUP /path/to/project [-w warehouse]`

**Actions**:

- Creates `.venv` in both framework and project directories
- Installs framework and project dependencies
- Copies warehouse template to `.env` in project
- Validates `source_model.yaml` exists
- **Does not launch UI** (use UI verb separately)

**Options**: `-w postgres` (default: csv)

### RUN

**Purpose**: Execute ETL pipeline for specific date partition.

**Usage**: `etl RUN /path/to/project -d YYYY-MM-DD`

**Actions**:

- Activates project virtual environment
- Loads project `.env` configuration
- Executes Dagster pipeline for specified date
- Materializes all assets in dependency order
- Reports completion status

### TEST

**Purpose**: Run project tests with pytest.

**Usage**: `etl TEST /path/to/project`

**Actions**:

- Activates project virtual environment
- Runs pytest with test configuration
- Uses isolated test data and config
- Reports test results and coverage

### VALIDATE

**Purpose**: Validate source model against database schema.

**Usage**:

- `etl VALIDATE /path/to/project` (auto-detects HCL)
- `etl VALIDATE /path/to/project /path/to/schema.hcl`

**Actions**:

- Parses HCL schema file from dbci-tools
- Loads ETL source model definitions
- Compares dimensions/facts against database tables
- Reports missing columns and schema mismatches
- Auto-detects `../demo-dw/target/schema.hcl` if not specified

### UI

**Purpose**: Launch Dagster web UI for project.

**Usage**: `etl UI /path/to/project [-p port]`

**Actions**:

- Activates project virtual environment
- Launches Dagster UI on specified port (default: 3001)
- Provides web interface for pipeline monitoring
- Runs until Ctrl+C to stop

**Options**: `-p 3001` (default port)

## Dependencies

- **Python 3.12+**: Runtime environment
- **Dagster**: Pipeline orchestration
- **pandas**: Data processing
- **psycopg**: PostgreSQL connectivity (optional)

## Project Structure

```text
project/
├── source_model.yaml    # ETL model definition (required)
├── .venv/              # Project virtual environment (created by SETUP)
├── .env                # Warehouse configuration (created by SETUP)
├── assets.py           # Dagster assets
├── pyproject.toml      # Project dependencies
└── tests/              # Test files
    ├── config_test.yaml
    └── data/           # Test data
```
