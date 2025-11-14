-- ============================================================================
-- VIEW: dim_product
-- Product dimension with full history (user-facing)
-- ============================================================================
CREATE OR REPLACE VIEW dim_product AS
SELECT
    dim_product_sk,
    effective_from,
    effective_to,
    is_current,
    sku,
    currency_code,
    launch_date,
    discontinued_at,
    category,
    brand,
    name,
    unit_price,
    grp_id
    
FROM t_dim_product;

-- User-facing view documentation
COMMENT ON VIEW dim_product IS 'Product dimension with complete SCD Type 2 history. Contains all versions of each product over time with tracking of what changed and when.';

-- Business key documentation
COMMENT ON COLUMN dim_product.dim_product_sk IS 'Surrogate key - unique identifier for each version of a product record. Use this for fact table joins.';
COMMENT ON COLUMN dim_product.sku IS 'Business key - Stock Keeping Unit (SKU) from source system. Use to find all versions of a product.';

-- Temporal metadata documentation  
COMMENT ON COLUMN dim_product.effective_from IS 'Date when this version became effective (when the product data looked like this)';
COMMENT ON COLUMN dim_product.effective_to IS 'Date when this version was superseded by a newer version (2999-12-31 for current version)';
COMMENT ON COLUMN dim_product.is_current IS 'Flag indicating current version (TRUE=current, FALSE=historical). Only one current version exists per product.';

-- Type 1 attributes (always current across all versions)
COMMENT ON COLUMN dim_product.currency_code IS 'Product currency code - Type 1 attribute (always shows current value across all historical versions)';
COMMENT ON COLUMN dim_product.launch_date IS 'Product launch date - Type 1 attribute (always shows current value across all historical versions)';
COMMENT ON COLUMN dim_product.discontinued_at IS 'Product discontinuation date - Type 1 attribute (always shows current value across all historical versions)';
COMMENT ON COLUMN dim_product.category IS 'Product category - Type 1 attribute (always shows current value across all historical versions)';
COMMENT ON COLUMN dim_product.brand IS 'Product brand - Type 1 attribute (always shows current value across all historical versions)';

-- Type 2 attributes (tracked historically)
COMMENT ON COLUMN dim_product.name IS 'Product name - Type 2 attribute (value preserved as it was at the time)';
COMMENT ON COLUMN dim_product.unit_price IS 'Product unit price - Type 2 attribute (value preserved as it was at the time)';
COMMENT ON COLUMN dim_product.grp_id IS 'Product group identifier - Type 2 attribute (value preserved as it was at the time)';

-- Helper views for common queries
CREATE OR REPLACE VIEW dim_product_current AS
SELECT
    dim_product_sk,
    sku,
    currency_code,
    launch_date,
    discontinued_at,
    category,
    brand,
    name,
    unit_price,
    grp_id,
    effective_from
FROM t_dim_product
WHERE is_current = TRUE
ORDER BY sku;

COMMENT ON VIEW dim_product_current IS 'Current (active) product records only. Most commonly used view for operational reporting and dashboards. Contains only the latest version of each product.';