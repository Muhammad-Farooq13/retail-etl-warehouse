-- Staging tables: near-raw structure, lightly typed, one row per source record.
-- These are the load target for clean (post-quality-check) data before any
-- business transformation happens.

CREATE TABLE IF NOT EXISTS stg_stores (
    store_id      TEXT PRIMARY KEY,
    region        TEXT NOT NULL,
    store_format  TEXT NOT NULL,
    opened_year   INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS stg_products (
    product_id  TEXT PRIMARY KEY,
    category    TEXT NOT NULL,
    unit_cost   REAL NOT NULL,
    unit_price  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS stg_transactions (
    transaction_id    TEXT PRIMARY KEY,
    transaction_date  TEXT NOT NULL,
    store_id          TEXT NOT NULL,
    product_id        TEXT NOT NULL,
    customer_id       TEXT,
    quantity          INTEGER NOT NULL,
    discount_pct      REAL NOT NULL,
    FOREIGN KEY (store_id) REFERENCES stg_stores(store_id),
    FOREIGN KEY (product_id) REFERENCES stg_products(product_id)
);

CREATE TABLE IF NOT EXISTS stg_quarantined_transactions (
    transaction_id    TEXT,
    transaction_date  TEXT,
    store_id          TEXT,
    product_id        TEXT,
    customer_id       TEXT,
    quantity          INTEGER,
    discount_pct      REAL,
    dq_reasons        TEXT NOT NULL
);
