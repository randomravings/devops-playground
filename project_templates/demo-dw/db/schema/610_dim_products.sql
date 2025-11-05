-- ============================================================================
-- VIEW: dim_products
-- Product dimension with full history (user-facing)
-- ============================================================================
CREATE OR REPLACE VIEW dim_products AS
SELECT
    dim_product_sk,
    sku,
    name,
    unit_price,
    currency_code,
    launch_date,
    discontinued_at,
    grp_id,
    category,
    brand,
    version,
    effective_from,
    effective_to,
    is_current,
    extract_date
FROM t_dim_products;
