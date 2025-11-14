-- ============================================================================
-- VIEW: dim_customer
-- Customer dimension with full history (user-facing)
-- Hides internal hash columns and audit details for business users
-- ============================================================================
CREATE OR REPLACE VIEW dim_customer AS
SELECT
    -- Surrogate and business keys
    dim_customer_sk,
    customer_id,
    
    -- SCD Type 2 metadata
    effective_from,
    effective_to,
    is_current,
    
    -- Type 1 attributes (always current across all versions)
    email,
    first_name,
    last_name,
    phone,
    
    -- Type 2 attributes (tracked historically)
    segment,
    address_line1,
    address_line2,
    city,
    state_province,
    postal_code,
    country
    
FROM t_dim_customer
ORDER BY customer_id, effective_from;

-- Comments explaining the view purpose
COMMENT ON VIEW dim_customer IS 'User-facing view of customer dimension with SCD Type 2 history. Shows all versions of each customer over time.';

-- Helper views for common queries
CREATE OR REPLACE VIEW dim_customer_current AS
SELECT
    dim_customer_sk,
    customer_id,
    email,
    first_name,
    last_name,
    phone,
    segment,
    address_line1,
    address_line2,
    city,
    state_province,
    postal_code,
    country,
    effective_from
FROM t_dim_customer
WHERE is_current = TRUE
ORDER BY customer_id;

COMMENT ON VIEW dim_customer_current IS 'Current (active) versions of all customers. Most common view for operational reporting.';
