-- ============================================================================
-- VIEW: dim_date
-- Date dimension with all calendar attributes (user-facing)
-- ============================================================================
CREATE OR REPLACE VIEW dim_date AS
SELECT
    dim_date_id,
    year,
    quarter,
    month,
    day,
    day_of_week,
    day_name,
    month_name,
    is_weekend,
    is_month_start,
    is_month_end,
    is_quarter_start,
    is_quarter_end,
    is_year_start,
    is_year_end
FROM t_dim_date;
