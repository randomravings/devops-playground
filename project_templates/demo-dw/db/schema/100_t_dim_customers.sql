-- ============================================================================
-- TABLE: t_dim_customers (SCD Type 2)
-- ============================================================================
CREATE TABLE IF NOT EXISTS t_dim_customers (
    -- Surrogate key
    dim_customer_sk SERIAL PRIMARY KEY,

    -- Natural key
    customer_id VARCHAR(50) NOT NULL,

    -- Type 1 attributes (always current)
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(50),

    -- Type 2 attributes (tracked historically)
    segment VARCHAR(50),
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state_province VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(10),

    -- SCD Type 2 metadata
    version INTEGER NOT NULL DEFAULT 1,
    effective_from DATE NOT NULL,
    effective_to DATE,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,

    -- Audit columns
    extract_date DATE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for SCD Type 2 queries
CREATE INDEX IF NOT EXISTS idx_t_dim_customers_natural_key
ON t_dim_customers (customer_id);
CREATE INDEX IF NOT EXISTS idx_t_dim_customers_current
ON t_dim_customers (customer_id, is_current)
WHERE is_current = TRUE;
CREATE INDEX IF NOT EXISTS idx_t_dim_customers_effective
ON t_dim_customers (effective_from, effective_to);
CREATE INDEX IF NOT EXISTS idx_t_dim_customers_extract_date
ON t_dim_customers (extract_date);
