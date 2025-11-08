# DBCI Tools - CLI Reference

Database Continuous Integration (DBCI) command-line tool for PostgreSQL schema management.

## CLI Verbs

### INSTALL

**Purpose**: Install and setup the DBCI tools environment.

**Usage**: `dbci INSTALL`

**Actions**:

- Creates `.venv` virtual environment in the dbci-tools directory
- Installs Python dependencies from requirements.txt
- Installs dbci-tools package in development mode
- Checks for external dependencies (Atlas CLI)
- Sets up the dbci-tools framework for use

### BUILD

**Purpose**: Generate HCL schema from source SQL files using Atlas.

**Usage**: `dbci BUILD /path/to/project`

**Actions**:

- Inspects SQL files in `db/schema/`
- Generates `target/schema.hcl` using Atlas schema inspection
- Uses `ATLAS_DEV_URL` environment variable or defaults to PostgreSQL 15 Docker

### LINT

**Purpose**: Run SQL linting on source schema files using SQLFluff.

**Usage**: `dbci LINT /path/to/project`

**Actions**:

- Lints all `.sql` files in `db/schema/`
- Uses project-local `.sqlfluff` configuration
- Reports style violations and formatting issues
- Enforces PostgreSQL dialect rules

### DIFF

**Purpose**: Compare current schema with main branch using Atlas.

**Usage**: `dbci DIFF /path/to/project`

**Actions**:

- Extracts `db/schema/` from `origin/main` branch
- Generates `target/main.hcl` for inspection
- Compares main branch vs current working directory schemas
- Produces migration SQL in `target/atlas.migration.sql`
- Creates schema change analysis in `target/atlas.migration.schema-changes.json`

### GUARD

**Purpose**: Run schema validation checks on migration changes.

**Usage**: `dbci GUARD /path/to/project`

**Actions**:

- Validates migration changes from `target/atlas.migration.schema-changes.json`
- Enforces database safety rules
- Prevents destructive schema changes
- **Must run after DIFF** to analyze migration output

### ALL

**Purpose**: Execute all operations in the proper sequence.

**Usage**: `dbci ALL /path/to/project`

**Actions**:

- Runs LINT → BUILD → DIFF → GUARD in sequence
- Stops on first failure
- Provides complete schema validation workflow

## Dependencies

- **Atlas CLI**: Schema inspection and migration generation
- **SQLFluff**: SQL linting and formatting
- **Git**: Branch comparison for DIFF operation

## Project Structure

```text
project/
├── db/schema/           # Source SQL files (required)
├── .sqlfluff           # SQLFluff configuration (created by INSTALL)
└── target/             # Generated outputs (created automatically)
    ├── schema.hcl      # Current schema (BUILD)
    ├── main.hcl        # Main branch schema (DIFF)
    ├── atlas.migration.sql              # Migration script (DIFF)
    └── atlas.migration.schema-changes.json  # Change analysis (DIFF)
```
