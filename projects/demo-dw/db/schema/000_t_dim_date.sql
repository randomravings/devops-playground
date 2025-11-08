-- ============================================================================
-- TABLE: t_dim_date
-- ============================================================================
CREATE TABLE IF NOT EXISTS t_dim_date (
    dim_date_id DATE PRIMARY KEY,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    day_name VARCHAR(10) NOT NULL,
    month_name VARCHAR(10) NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    is_month_start BOOLEAN NOT NULL,
    is_month_end BOOLEAN NOT NULL,
    is_quarter_start BOOLEAN NOT NULL,
    is_quarter_end BOOLEAN NOT NULL,
    is_year_start BOOLEAN NOT NULL,
    is_year_end BOOLEAN NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_t_dim_date_year_month
ON t_dim_date (year, month);
CREATE INDEX IF NOT EXISTS idx_t_dim_date_quarter
ON t_dim_date (year, quarter);
