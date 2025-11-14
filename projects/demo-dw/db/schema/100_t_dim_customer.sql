-- ============================================================================
-- TABLE: t_dim_customer (SCD Type 2)
-- Customer dimension with full history tracking
-- ============================================================================
CREATE TABLE IF NOT EXISTS t_dim_customer (
    -- Surrogate key (manually managed for consistent SCD Type 2 logic)
    dim_customer_sk INTEGER PRIMARY KEY,

    -- Business key (from source system)
    customer_id VARCHAR(50) NOT NULL,

    -- SCD Type 2 temporal metadata
    effective_from DATE NOT NULL,
    effective_to DATE NOT NULL,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,

    -- Hash columns for change detection (VARCHAR to prevent overflow)
    t1_hash VARCHAR(64),
    t2_hash VARCHAR(64),

    -- Type 1 attributes (updated in place for all versions)
    email VARCHAR(255),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(50),

    -- Type 2 attributes (tracked historically via versioning)
    segment VARCHAR(50),
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state_province VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(10),

    -- Audit columns (extract_date NEVER changes after insertion)
    extract_date DATE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Performance indexes for SCD Type 2 operations
CREATE INDEX IF NOT EXISTS idx_t_dim_customer_business_key
    ON t_dim_customer (customer_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_t_dim_customer_current
    ON t_dim_customer (customer_id)
    WHERE is_current = TRUE;

CREATE INDEX IF NOT EXISTS idx_t_dim_customer_effective_dates
    ON t_dim_customer (effective_from, effective_to);

CREATE INDEX IF NOT EXISTS idx_t_dim_customer_extract_date
    ON t_dim_customer (extract_date);

-- Unique partial index to enforce only one current record per business key
CREATE UNIQUE INDEX IF NOT EXISTS idx_t_dim_customer_current_unique
    ON t_dim_customer (customer_id) WHERE is_current = TRUE;

-- Comments explaining SCD Type 2 behavior
COMMENT ON TABLE t_dim_customer IS 'Customer dimension with SCD Type 2 history tracking. Each customer may have multiple versions over time.';

COMMENT ON COLUMN t_dim_customer.dim_customer_sk IS 'Surrogate key - unique identifier for each version of a customer record';
COMMENT ON COLUMN t_dim_customer.customer_id IS 'Business key - natural identifier from source system';
COMMENT ON COLUMN t_dim_customer.effective_from IS 'Date when this version became effective';
COMMENT ON COLUMN t_dim_customer.effective_to IS 'Date when this version was superseded (2999-12-31 for current)';
COMMENT ON COLUMN t_dim_customer.is_current IS 'Flag indicating current version (1=current, 0=historical)';
COMMENT ON COLUMN t_dim_customer.t1_hash IS 'Hash of Type 1 fields for change detection';
COMMENT ON COLUMN t_dim_customer.t2_hash IS 'Hash of Type 2 fields for change detection';
COMMENT ON COLUMN t_dim_customer.extract_date IS 'Date when record was first extracted (NEVER updated)';
COMMENT ON COLUMN t_dim_customer.created_at IS 'Timestamp when this version was created';
COMMENT ON COLUMN t_dim_customer.updated_at IS 'Timestamp when this version was last modified';

-- Type 1 field comments (updated in place for all versions)
COMMENT ON COLUMN t_dim_customer.email IS 'Type 1: Customer email - updated in place for all versions';
COMMENT ON COLUMN t_dim_customer.first_name IS 'Type 1: Customer first name - updated in place for all versions';
COMMENT ON COLUMN t_dim_customer.last_name IS 'Type 1: Customer last name - updated in place for all versions';
COMMENT ON COLUMN t_dim_customer.phone IS 'Type 1: Customer phone - updated in place for all versions';

-- Type 2 field comments (tracked historically via versioning)
COMMENT ON COLUMN t_dim_customer.segment IS 'Type 2: Customer segment - tracked historically';
COMMENT ON COLUMN t_dim_customer.address_line1 IS 'Type 2: Address line 1 - tracked historically';
COMMENT ON COLUMN t_dim_customer.address_line2 IS 'Type 2: Address line 2 - tracked historically';
COMMENT ON COLUMN t_dim_customer.city IS 'Type 2: City - tracked historically';
COMMENT ON COLUMN t_dim_customer.state_province IS 'Type 2: State/Province - tracked historically';
COMMENT ON COLUMN t_dim_customer.postal_code IS 'Type 2: Postal code - tracked historically';
COMMENT ON COLUMN t_dim_customer.country IS 'Type 2: Country - tracked historically';
