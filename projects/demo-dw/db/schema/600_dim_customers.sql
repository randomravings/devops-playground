-- ============================================================================
-- VIEW: dim_customers
-- Customer dimension with full history (user-facing)
-- ============================================================================
CREATE OR REPLACE VIEW dim_customers AS
SELECT
    dim_customer_sk,
    customer_id,
    first_name,
    last_name,
    email,
    phone,
    segment,
    address_line1,
    address_line2,
    city,
    state_province,
    postal_code,
    country,
    version,
    effective_from,
    effective_to,
    is_current,
    extract_date
FROM t_dim_customers;
