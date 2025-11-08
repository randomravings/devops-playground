-- ============================================================================
-- VIEW: fact_orders
-- Fact with current dimension attributes (user-facing, denormalized)
-- ============================================================================
CREATE OR REPLACE VIEW fact_orders AS
SELECT
    f.order_id,
    f.line_number,
    f.order_number,
    f.order_date,
    f.order_timestamp,
    f.status,
    f.channel,
    f.payment_method,

    -- Customer attributes (current)
    c.dim_customer_sk,
    c.first_name,
    c.last_name,
    c.email,
    c.segment,
    c.city,
    c.state_province,
    c.country,

    -- Product attributes (current)
    p.dim_product_sk,
    p.name AS product_name,
    p.category,
    p.brand,

    -- Line metrics
    f.sku,
    f.quantity,
    f.unit_price,
    f.discount,
    f.line_total,

    -- Order metrics
    f.shipping_cost,
    f.tax_amount,
    f.total_amount,

    f.extract_date
FROM t_fact_orders AS f
LEFT JOIN dim_customers AS c ON f.customer_id = c.customer_id
LEFT JOIN dim_products AS p ON f.sku = p.sku;
