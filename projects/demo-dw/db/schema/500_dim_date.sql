-- ============================================================================
-- VIEW: dim_date
-- Date dimension with all calendar attributes (user-facing)
-- ============================================================================
CREATE OR REPLACE VIEW dim_date AS
SELECT
    dim_date_sk,
    is_current,
    year,
    quarter,
    month,
    day,
    day_of_week,
    day_of_year,
    week_of_year,
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

-- User-facing view documentation
COMMENT ON VIEW dim_date IS 'Date dimension with comprehensive calendar attributes. Provides all calendar calculations and flags needed for time-based analysis.';

-- Key columns
COMMENT ON COLUMN dim_date.dim_date_sk IS 'Date surrogate key - use this for fact table joins. Also serves as the actual date value.';
COMMENT ON COLUMN dim_date.is_current IS 'Flag indicating if this date record is current. Used for SCD Type 2 consistency.';

-- Basic date components
COMMENT ON COLUMN dim_date.year IS 'Four-digit year (e.g., 2024)';
COMMENT ON COLUMN dim_date.quarter IS 'Quarter number (1-4)';
COMMENT ON COLUMN dim_date.month IS 'Month number (1-12)';
COMMENT ON COLUMN dim_date.day IS 'Day of month (1-31)';

-- Advanced date attributes
COMMENT ON COLUMN dim_date.day_of_week IS 'Day of week number (0=Monday, 6=Sunday)';
COMMENT ON COLUMN dim_date.day_of_year IS 'Day number within the year (1-366)';
COMMENT ON COLUMN dim_date.week_of_year IS 'ISO week number within the year (1-53)';
COMMENT ON COLUMN dim_date.day_name IS 'Full day name (Monday, Tuesday, etc.)';
COMMENT ON COLUMN dim_date.month_name IS 'Full month name (January, February, etc.)';

-- Business flags for common filters
COMMENT ON COLUMN dim_date.is_weekend IS 'TRUE if Saturday or Sunday, FALSE for weekdays';
COMMENT ON COLUMN dim_date.is_month_start IS 'TRUE if first day of the month';
COMMENT ON COLUMN dim_date.is_month_end IS 'TRUE if last day of the month';
COMMENT ON COLUMN dim_date.is_quarter_start IS 'TRUE if first day of the quarter';
COMMENT ON COLUMN dim_date.is_quarter_end IS 'TRUE if last day of the quarter';
COMMENT ON COLUMN dim_date.is_year_start IS 'TRUE if first day of the year (January 1st)';
COMMENT ON COLUMN dim_date.is_year_end IS 'TRUE if last day of the year (December 31st)';
