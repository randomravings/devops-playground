# PostgreSQL Schema - Demo ETL Warehouse

PostgreSQL DDL for SCD Type 2 dimensions and fact tables.

## Structure

```bash
schema/
├── README.md                   # This file
├── 000_t_dim_date.sql          # Date dimension table
├── 100_t_dim_customers.sql     # Customer dimension table (SCD Type 2)
├── 110_t_dim_products.sql      # Product dimension table (SCD Type 2)
├── 300_t_fact_orders.sql       # Order fact table
├── 500_dim_date.sql            # Date dimension view (user-facing)
├── 600_dim_customers.sql       # Customer dimension view (user-facing)
├── 610_dim_products.sql        # Product dimension view (user-facing)
└── 700_fact_orders.sql         # Order fact view (user-facing, enriched)
```

**Naming Convention:**

- **Tables** (ETL targets): Prefixed with `t_` (e.g., `t_dim_customers`, `t_fact_orders`)
- **Views** (User-facing): No prefix (e.g., `dim_customers`, `fact_orders`)

**Execution Order:**

- `000-499` - Tables (no inter-dependencies)
  - `000_*` - Date dimension table
  - `1xx_*` - Other dimension tables
  - `3xx_*` - Fact tables
- `500-999` - Views (depend on tables, mirror table numbering)
  - `5xx_*` - Views for 0xx tables (date dimension)
  - `6xx_*` - Views for 1xx tables (other dimensions)
  - `7xx_*` - Views for 3xx tables (facts)

## Usage

### Create All Tables

```bash
# Create database and user (if needed)
psql -U postgres << EOF
CREATE DATABASE warehouse;
CREATE USER etl_user WITH PASSWORD 'changeme';
GRANT ALL PRIVILEGES ON DATABASE warehouse TO etl_user;
EOF

# Apply schema in order (numeric prefixes ensure correct sequence)
psql -h localhost -U etl_user -d warehouse << EOF
\i schema/000_t_dim_date.sql
\i schema/100_t_dim_customers.sql
\i schema/110_t_dim_products.sql
\i schema/300_t_fact_orders.sql
\i schema/500_dim_date.sql
\i schema/600_dim_customers.sql
\i schema/610_dim_products.sql
\i schema/700_fact_orders.sql
EOF

# Or apply all files in order using glob expansion
cd schema && for f in *.sql; do psql -h localhost -U etl_user -d warehouse -f "$f"; done
```

### Create Individual Table

```bash
psql -h localhost -U etl_user -d warehouse -f schema/100_t_dim_customers.sql
```

### Drop All Tables

```bash
# Drop in reverse order (views first, then tables)
psql -h localhost -U etl_user -d warehouse << EOF
DROP VIEW IF EXISTS fact_orders;
DROP VIEW IF EXISTS dim_products;
DROP VIEW IF EXISTS dim_customers;
DROP VIEW IF EXISTS dim_date;
DROP TABLE IF EXISTS t_fact_orders;
DROP TABLE IF EXISTS t_dim_products;
DROP TABLE IF EXISTS t_dim_customers;
DROP TABLE IF EXISTS t_dim_date;
EOF
```

## Schema Features

### Tables (ETL Targets - `t_` prefix)

ETL processes write to these tables. Advanced users can query for historical analysis.

**Dimensions (SCD Type 2):**

- **Surrogate Keys**: `dim_*_sk` (SERIAL) for immutable references
- **Natural Keys**: Business keys like `customer_id`, `sku`
- **Version Tracking**: `version`, `effective_from`, `effective_to`, `is_current`
- **Audit Columns**: `extract_date`, `created_at`, `updated_at`

**Facts:**

- **Grain**: One row per order line item
- **Foreign Keys**: Optional constraints to dimension tables
- **Measures**: Quantities, amounts, costs

### Views (User-Facing - no prefix)

End users query these views. They hide complexity and provide current/enriched data.

**Dimension Views:**

- `dim_date`: All calendar attributes
- `dim_customers`: Full customer history with SCD Type 2 tracking
- `dim_products`: Full product history with SCD Type 2 tracking

**Fact Views:**

- `fact_orders`: Enriched with dimension attributes (joins to tables, not filtered)

### Indexes

- Natural key lookups: Fast business key queries on `t_dim_*` tables
- Current records: Optimized `WHERE is_current = TRUE` queries
- Effective date ranges: Historical point-in-time queries on `t_dim_*` tables
- Extract date tracking: ETL lineage and debugging

## Testing with Demo ETL

1. **Setup PostgreSQL**

   ```bash
   # Start PostgreSQL (Docker example)
   docker run -d \
     --name postgres-warehouse \
     -e POSTGRES_DB=warehouse \
     -e POSTGRES_USER=etl_user \
     -e POSTGRES_PASSWORD=changeme \
     -p 5432:5432 \
     postgres:15
   ```

2. **Create Schema**

   ```bash
   cd /Users/bergur/Local/john/demo-etl
   for f in schema/*.sql; do 
     psql -h localhost -U etl_user -d warehouse -f "$f"
   done
   ```

3. **Configure Demo ETL**

   ```bash
   cp .env.postgres.example .env
   # Edit .env to set:
   # WAREHOUSE_TYPE=postgres
   # POSTGRES_HOST=localhost
   # POSTGRES_DB=warehouse
   # POSTGRES_USER=etl_user
   # POSTGRES_PASSWORD=changeme
   ```

4. **Run ETL**

   ```bash
   ./setup.sh
   ./run.sh -d 2024-02-01
   ```

5. **Query Results**

   ```sql
   -- Query all customers (includes history)
   SELECT * FROM dim_customers;
   
   -- Query current customers only
   SELECT * FROM dim_customers WHERE is_current = TRUE;
   
   -- Query historical snapshot
   SELECT * FROM dim_customers 
   WHERE '2024-03-01' BETWEEN effective_from AND COALESCE(effective_to, '9999-12-31');
   
   -- Query version history for specific customer (table access)
   SELECT customer_id, version, effective_from, effective_to, is_current
   FROM t_dim_customers
   WHERE customer_id = 'CUST-001'
   ORDER BY version;
   
   -- Query enriched facts
   SELECT order_id, first_name, last_name, product_name, line_total
   FROM fact_orders
   ORDER BY order_date DESC;
   ```
