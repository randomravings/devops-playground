-- ============================================================================
-- VIEW: fact_order
-- Fact with current dimension attributes (user-facing, denormalized)
-- ============================================================================
CREATE OR REPLACE VIEW fact_order AS
SELECT
    f.order_id,
    f.line_number,
    f.order_number,
    f.order_date,
    f.order_timestamp,
    f.status,
    f.channel,
    f.payment_method,
    f.quantity,
    f.unit_price,
    f.discount,
    f.line_total,
    f.shipping_cost,
    f.tax_amount,
    f.total_amount,

    -- Line foreign keys to dimensions
    f.dim_date_sk,
    d.is_current,
    d.year,
    d.quarter,
    d.month,
    d.day,
    d.day_of_week,
    d.day_of_year,
    d.week_of_year,
    d.day_name,
    d.month_name,
    d.is_weekend,
    d.is_month_start,
    d.is_month_end,
    d.is_quarter_start,
    d.is_quarter_end,
    d.is_year_start,
    d.is_year_end,

    -- Customer attributes (current)
    f.dim_customer_sk,
    c.customer_id,
    c.first_name,
    c.last_name,
    c.email,
    c.segment,
    c.city,
    c.state_province,
    c.country,

    -- Product attributes (current)
    f.dim_product_sk,
    p.sku,
    p.name AS product_name,
    p.category,
    p.brand
    
FROM t_fact_order AS f
JOIN dim_date AS d ON f.dim_date_sk = d.dim_date_sk
JOIN dim_customer AS c ON f.dim_customer_sk = c.dim_customer_sk
JOIN dim_product AS p ON f.dim_product_sk = p.dim_product_sk;

-- User-facing fact view documentation
COMMENT ON VIEW fact_order IS 'Order fact table with denormalized dimension attributes. Each row represents one line item from an order. Includes current customer and product attributes for easy analysis without additional joins.';

-- Primary identifiers
COMMENT ON COLUMN fact_order.order_id IS 'Unique order identifier from source system';
COMMENT ON COLUMN fact_order.line_number IS 'Line item number within the order (1, 2, 3...)';
COMMENT ON COLUMN fact_order.order_number IS 'Human-readable order number displayed to customers';

-- Order context
COMMENT ON COLUMN fact_order.order_date IS 'Date when the order was placed (use for time-based analysis)';
COMMENT ON COLUMN fact_order.order_timestamp IS 'Exact timestamp when the order was placed';
COMMENT ON COLUMN fact_order.status IS 'Order status (Pending, Shipped, Delivered, Cancelled, etc.)';
COMMENT ON COLUMN fact_order.channel IS 'Sales channel (Online, Store, Phone, etc.)';
COMMENT ON COLUMN fact_order.payment_method IS 'Payment method used (Credit Card, PayPal, etc.)';

-- Dimension keys (for advanced users who need to join to dimension tables)
COMMENT ON COLUMN fact_order.dim_date_sk IS 'Foreign key to date dimension (same as order_date)';
COMMENT ON COLUMN fact_order.dim_customer_sk IS 'Foreign key to customer dimension at time of order';
COMMENT ON COLUMN fact_order.dim_product_sk IS 'Foreign key to product dimension at time of order';

-- Date dimension attributes (denormalized for convenience)
COMMENT ON COLUMN fact_order.year IS 'Year of order date';
COMMENT ON COLUMN fact_order.quarter IS 'Quarter of order date (1-4)';
COMMENT ON COLUMN fact_order.month IS 'Month of order date (1-12)';
COMMENT ON COLUMN fact_order.day IS 'Day of month for order date';
COMMENT ON COLUMN fact_order.day_of_week IS 'Day of week (0=Monday, 6=Sunday)';
COMMENT ON COLUMN fact_order.day_name IS 'Day name (Monday, Tuesday, etc.)';
COMMENT ON COLUMN fact_order.month_name IS 'Month name (January, February, etc.)';
COMMENT ON COLUMN fact_order.is_weekend IS 'TRUE if order placed on weekend';

-- Customer attributes (current values - denormalized for convenience)
COMMENT ON COLUMN fact_order.customer_id IS 'Customer business identifier';
COMMENT ON COLUMN fact_order.first_name IS 'Customer first name (current value)';
COMMENT ON COLUMN fact_order.last_name IS 'Customer last name (current value)';
COMMENT ON COLUMN fact_order.email IS 'Customer email (current value)';
COMMENT ON COLUMN fact_order.segment IS 'Customer segment at time of order';
COMMENT ON COLUMN fact_order.city IS 'Customer city at time of order';
COMMENT ON COLUMN fact_order.state_province IS 'Customer state/province at time of order';
COMMENT ON COLUMN fact_order.country IS 'Customer country at time of order';

-- Product attributes (values at time of order - denormalized for convenience)
COMMENT ON COLUMN fact_order.sku IS 'Product SKU (Stock Keeping Unit)';
COMMENT ON COLUMN fact_order.product_name IS 'Product name at time of order';
COMMENT ON COLUMN fact_order.category IS 'Product category at time of order';
COMMENT ON COLUMN fact_order.brand IS 'Product brand at time of order';

-- Line-level measurements
COMMENT ON COLUMN fact_order.quantity IS 'Quantity of this product ordered';
COMMENT ON COLUMN fact_order.unit_price IS 'Price per unit at time of order';
COMMENT ON COLUMN fact_order.discount IS 'Discount amount applied to this line';
COMMENT ON COLUMN fact_order.line_total IS 'Total for this line (quantity × unit_price - discount)';

-- Order-level measurements
COMMENT ON COLUMN fact_order.shipping_cost IS 'Shipping cost for entire order (repeated on each line)';
COMMENT ON COLUMN fact_order.tax_amount IS 'Tax amount for entire order (repeated on each line)';
COMMENT ON COLUMN fact_order.total_amount IS 'Total order amount (repeated on each line)';

CREATE OR REPLACE VIEW fact_order_current AS
SELECT
    f.order_id,
    f.line_number,
    f.order_number,
    f.order_date,
    f.order_timestamp,
    f.status,
    f.channel,
    f.payment_method,
    f.quantity,
    f.unit_price,
    f.discount,
    f.line_total,
    f.shipping_cost,
    f.tax_amount,
    f.total_amount,

    -- Line foreign keys to dimensions
    f.dim_date_sk,
    d.is_current,
    d.year,
    d.quarter,
    d.month,
    d.day,
    d.day_of_week,
    d.day_of_year,
    d.week_of_year,
    d.day_name,
    d.month_name,
    d.is_weekend,
    d.is_month_start,
    d.is_month_end,
    d.is_quarter_start,
    d.is_quarter_end,
    d.is_year_start,
    d.is_year_end,

    -- Customer attributes (current)
    f.dim_customer_sk,
    c.customer_id,
    c.first_name,
    c.last_name,
    c.email,
    c.segment,
    c.city,
    c.state_province,
    c.country,

    -- Product attributes (current)
    f.dim_product_sk,
    p.sku,
    p.name AS product_name,
    p.category,
    p.brand
    
FROM t_fact_order AS f
JOIN dim_date AS d ON f.dim_date_sk = d.dim_date_sk
JOIN dim_customer AS c ON f.dim_customer_sk = c.dim_customer_sk
JOIN dim_product AS p ON f.dim_product_sk = p.dim_product_sk
WHERE d.is_current = TRUE;