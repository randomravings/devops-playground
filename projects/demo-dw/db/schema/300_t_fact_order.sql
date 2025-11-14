-- ============================================================================
-- TABLE: t_fact_order
-- ============================================================================
CREATE TABLE IF NOT EXISTS t_fact_order (

    -- Audit columns
    extract_date DATE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Composite primary key
    order_id VARCHAR(50) NOT NULL,
    line_number INTEGER NOT NULL,

    -- Foreign key surrogate keys to dimensions
    dim_date_sk DATE,
    dim_customer_sk INTEGER,
    dim_product_sk INTEGER,

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

    PRIMARY KEY (order_id, line_number)
);

ALTER TABLE t_fact_order 
    ADD CONSTRAINT fk_t_fact_order_customer 
    FOREIGN KEY (dim_customer_sk) REFERENCES t_dim_customer(dim_customer_sk);

ALTER TABLE t_fact_order 
    ADD CONSTRAINT fk_t_fact_order_product 
    FOREIGN KEY (dim_product_sk) REFERENCES t_dim_product(dim_product_sk);

ALTER TABLE t_fact_order 
    ADD CONSTRAINT fk_t_fact_order_order_date 
    FOREIGN KEY (order_date) REFERENCES t_dim_date(dim_date_sk);

CREATE INDEX IF NOT EXISTS idx_t_fact_order_dim_customer_sk
ON t_fact_order (dim_customer_sk);
CREATE INDEX IF NOT EXISTS idx_t_fact_order_dim_product_sk
ON t_fact_order (dim_product_sk);
CREATE INDEX IF NOT EXISTS idx_t_fact_order_customer
ON t_fact_order (customer_id);
CREATE INDEX IF NOT EXISTS idx_t_fact_order_product
ON t_fact_order (sku);
CREATE INDEX IF NOT EXISTS idx_t_fact_order_order_date
ON t_fact_order (order_date);
CREATE INDEX IF NOT EXISTS idx_t_fact_order_extract_date
ON t_fact_order (extract_date);
CREATE INDEX IF NOT EXISTS idx_t_fact_order_timestamp
ON t_fact_order (order_timestamp);
