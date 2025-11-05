-- ============================================================================
-- TABLE: t_fact_orders
-- ============================================================================
CREATE TABLE IF NOT EXISTS t_fact_orders (
    -- Composite primary key
    order_id VARCHAR(50) NOT NULL,
    line_number INTEGER NOT NULL,

    -- Order header attributes
    order_number VARCHAR(50),
    customer_id VARCHAR(50),
    order_date DATE,
    order_timestamp TIMESTAMP,
    status VARCHAR(50),
    channel VARCHAR(50),
    payment_method VARCHAR(50),
    shipping_cost NUMERIC(10, 2),
    tax_amount NUMERIC(10, 2),
    total_amount NUMERIC(10, 2),

    -- Order line attributes
    sku VARCHAR(50),
    quantity INTEGER,
    unit_price NUMERIC(10, 2),
    discount NUMERIC(10, 2),
    line_total NUMERIC(10, 2),
    line_timestamp TIMESTAMP,

    -- Audit columns
    extract_date DATE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (order_id, line_number)
);

-- Foreign key constraints (optional - enforce referential integrity)
-- Uncomment if you want strict FK enforcement
-- ALTER TABLE t_fact_orders 
--     ADD CONSTRAINT fk_t_fact_orders_customer 
--     FOREIGN KEY (customer_id) REFERENCES t_dim_customers(customer_id);
-- 
-- ALTER TABLE t_fact_orders 
--     ADD CONSTRAINT fk_t_fact_orders_product 
--     FOREIGN KEY (sku) REFERENCES t_dim_products(sku);
-- 
-- ALTER TABLE t_fact_orders 
--     ADD CONSTRAINT fk_t_fact_orders_order_date 
--     FOREIGN KEY (order_date) REFERENCES t_dim_date(dim_date_id);

-- Indexes for fact table queries
CREATE INDEX IF NOT EXISTS idx_t_fact_orders_customer
ON t_fact_orders (customer_id);
CREATE INDEX IF NOT EXISTS idx_t_fact_orders_product
ON t_fact_orders (sku);
CREATE INDEX IF NOT EXISTS idx_t_fact_orders_order_date
ON t_fact_orders (order_date);
CREATE INDEX IF NOT EXISTS idx_t_fact_orders_extract_date
ON t_fact_orders (extract_date);
CREATE INDEX IF NOT EXISTS idx_t_fact_orders_timestamp
ON t_fact_orders (order_timestamp);
