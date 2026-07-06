-- Model: mart_customer_summary
-- Grain: one row per registered customer (guest checkouts excluded, customer_id IS NOT NULL).
INSERT INTO mart_customer_summary
SELECT
    f.customer_id,
    MIN(f.date_key)                          AS first_purchase,
    MAX(f.date_key)                          AS last_purchase,
    COUNT(*)                                 AS n_transactions,
    ROUND(SUM(f.net_revenue), 2)             AS lifetime_revenue,
    ROUND(SUM(f.net_revenue) / COUNT(*), 2)  AS avg_order_value
FROM fact_sales f
WHERE f.customer_id IS NOT NULL
GROUP BY f.customer_id;
