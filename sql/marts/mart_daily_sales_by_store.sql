-- Model: mart_daily_sales_by_store
-- Grain: one row per (date, store). Analogous to a dbt mart model.
INSERT INTO mart_daily_sales_by_store
SELECT
    f.date_key,
    f.store_id,
    s.region,
    COUNT(*)                    AS n_transactions,
    SUM(f.quantity)             AS total_quantity,
    ROUND(SUM(f.gross_revenue), 2) AS gross_revenue,
    ROUND(SUM(f.net_revenue), 2)   AS net_revenue,
    ROUND(SUM(f.gross_profit), 2)  AS gross_profit
FROM fact_sales f
JOIN dim_store s ON f.store_id = s.store_id
GROUP BY f.date_key, f.store_id, s.region;
