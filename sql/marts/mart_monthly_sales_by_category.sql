-- Model: mart_monthly_sales_by_category
-- Grain: one row per (year_month, category).
INSERT INTO mart_monthly_sales_by_category
SELECT
    substr(f.date_key, 1, 7)       AS year_month,
    p.category,
    COUNT(*)                       AS n_transactions,
    SUM(f.quantity)                AS total_quantity,
    ROUND(SUM(f.gross_revenue), 2) AS gross_revenue,
    ROUND(SUM(f.net_revenue), 2)   AS net_revenue,
    ROUND(SUM(f.gross_profit), 2)  AS gross_profit,
    ROUND(AVG(p.margin_pct), 2)    AS avg_margin_pct
FROM fact_sales f
JOIN dim_product p ON f.product_id = p.product_id
GROUP BY substr(f.date_key, 1, 7), p.category;
