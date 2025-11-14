-- ============================================================================
-- TABLE: t_dim_product (SCD Type 2)
-- ============================================================================
CREATE TABLE IF NOT EXISTS t_dim_product (
    -- Surrogate key
    dim_product_sk SERIAL PRIMARY KEY,

    -- SCD Type 1 & 2 metadata
    effective_from DATE NOT NULL,
    effective_to DATE NOT NULL,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,

    -- Audit columns
    extract_date DATE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Hash columns for change detection
    t1_hash VARCHAR(64),
    t2_hash VARCHAR(64),

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
    grp_id VARCHAR(50)  -- product_group_id alias
);

CREATE INDEX IF NOT EXISTS idx_t_dim_product_natural_key
ON t_dim_product (sku);
CREATE UNIQUE INDEX IF NOT EXISTS idx_t_dim_product_current
ON t_dim_product (sku)
WHERE is_current = TRUE;
CREATE INDEX IF NOT EXISTS idx_t_dim_product_effective
ON t_dim_product (effective_from, effective_to);
CREATE INDEX IF NOT EXISTS idx_t_dim_product_extract_date
ON t_dim_product (extract_date);
CREATE INDEX IF NOT EXISTS idx_t_dim_product_grp_id
ON t_dim_product (grp_id);

-- Unique partial index to enforce only one current record per business key
CREATE UNIQUE INDEX IF NOT EXISTS idx_t_dim_product_current_unique
ON t_dim_product (sku) WHERE is_current = TRUE;
