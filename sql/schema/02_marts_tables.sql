-- Mart layer: star schema (dimension + fact tables) ready for BI/analytics.

CREATE TABLE IF NOT EXISTS dim_store (
    store_id      TEXT PRIMARY KEY,
    region        TEXT NOT NULL,
    store_format  TEXT NOT NULL,
    opened_year   INTEGER NOT NULL,
    store_age_years INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_product (
    product_id  TEXT PRIMARY KEY,
    category    TEXT NOT NULL,
    unit_cost   REAL NOT NULL,
    unit_price  REAL NOT NULL,
    margin_pct  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_key     TEXT PRIMARY KEY,   -- YYYY-MM-DD
    year         INTEGER NOT NULL,
    month        INTEGER NOT NULL,
    day_of_week  TEXT NOT NULL,
    is_weekend   INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_sales (
    transaction_id  TEXT PRIMARY KEY,
    date_key        TEXT NOT NULL,
    store_id        TEXT NOT NULL,
    product_id      TEXT NOT NULL,
    customer_id     TEXT,             -- NULL = guest checkout
    quantity        INTEGER NOT NULL,
    discount_pct    REAL NOT NULL,
    gross_revenue   REAL NOT NULL,
    net_revenue     REAL NOT NULL,
    cost_of_goods   REAL NOT NULL,
    gross_profit    REAL NOT NULL,
    FOREIGN KEY (date_key) REFERENCES dim_date(date_key),
    FOREIGN KEY (store_id) REFERENCES dim_store(store_id),
    FOREIGN KEY (product_id) REFERENCES dim_product(product_id)
);

-- Aggregated marts (analogous to dbt "marts" models built on top of fact_sales)

CREATE TABLE IF NOT EXISTS mart_daily_sales_by_store (
    date_key       TEXT NOT NULL,
    store_id       TEXT NOT NULL,
    region         TEXT NOT NULL,
    n_transactions INTEGER NOT NULL,
    total_quantity INTEGER NOT NULL,
    gross_revenue  REAL NOT NULL,
    net_revenue    REAL NOT NULL,
    gross_profit   REAL NOT NULL,
    PRIMARY KEY (date_key, store_id)
);

CREATE TABLE IF NOT EXISTS mart_monthly_sales_by_category (
    year_month     TEXT NOT NULL,
    category       TEXT NOT NULL,
    n_transactions INTEGER NOT NULL,
    total_quantity INTEGER NOT NULL,
    gross_revenue  REAL NOT NULL,
    net_revenue    REAL NOT NULL,
    gross_profit   REAL NOT NULL,
    avg_margin_pct REAL NOT NULL,
    PRIMARY KEY (year_month, category)
);

CREATE TABLE IF NOT EXISTS mart_customer_summary (
    customer_id       TEXT PRIMARY KEY,
    first_purchase    TEXT NOT NULL,
    last_purchase     TEXT NOT NULL,
    n_transactions    INTEGER NOT NULL,
    lifetime_revenue  REAL NOT NULL,
    avg_order_value   REAL NOT NULL
);
