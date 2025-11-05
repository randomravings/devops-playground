-- ============================================================================
-- TABLE: t_dim_products (SCD Type 2)
-- ============================================================================
CREATE TABLE IF NOT EXISTS t_dim_products (
    -- Surrogate key
    dim_product_sk SERIAL PRIMARY KEY,

    -- Natural key
    sku VARCHAR(50) NOT NULL,

    -- Type 1 attributes (always current)
    currency_code VARCHAR(10),
    launch_date DATE,
    discontinued_at DATE,
    category VARCHAR(100),
    brand VARCHAR(100),

    -- Type 2 attributes (tracked historically)
    name VARCHAR(255),
    unit_price NUMERIC(10, 2),
    grp_id VARCHAR(50),  -- product_group_id alias

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
CREATE INDEX IF NOT EXISTS idx_t_dim_products_natural_key
ON t_dim_products (sku);
CREATE INDEX IF NOT EXISTS idx_t_dim_products_current
ON t_dim_products (sku, is_current)
WHERE is_current = TRUE;
CREATE INDEX IF NOT EXISTS idx_t_dim_products_effective
ON t_dim_products (effective_from, effective_to);
CREATE INDEX IF NOT EXISTS idx_t_dim_products_extract_date
ON t_dim_products (extract_date);
CREATE INDEX IF NOT EXISTS idx_t_dim_products_grp_id
ON t_dim_products (grp_id);
