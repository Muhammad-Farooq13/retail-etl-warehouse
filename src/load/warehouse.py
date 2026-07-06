"""Load layer: builds the SQLite data warehouse (star schema) from clean,
validated staging data, then runs the dbt-style SQL mart models on top.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from src.utils.config import load_config, resolve_path
from src.utils.logger import get_logger

logger = get_logger(__name__)

SQL_DIR = Path(__file__).resolve().parents[2] / "sql"


def _run_script(conn: sqlite3.Connection, path: Path) -> None:
    with open(path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())


def get_connection(cfg=None) -> sqlite3.Connection:
    cfg = cfg or load_config()
    db_path = resolve_path(cfg.warehouse.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def init_schema(conn: sqlite3.Connection, cfg=None) -> None:
    """Create staging and mart tables if they don't already exist."""
    cfg = cfg or load_config()
    _run_script(conn, resolve_path(cfg.warehouse.staging_schema_sql))
    _run_script(conn, resolve_path(cfg.warehouse.marts_schema_sql))
    logger.info("Warehouse schema initialized (staging + marts).")


def reset_warehouse(conn: sqlite3.Connection) -> None:
    """Truncate all tables so the pipeline can be re-run idempotently."""
    tables = [
        "stg_stores", "stg_products", "stg_transactions", "stg_quarantined_transactions",
        "dim_store", "dim_product", "dim_date", "fact_sales",
        "mart_daily_sales_by_store", "mart_monthly_sales_by_category", "mart_customer_summary",
    ]
    cur = conn.cursor()
    for table in tables:
        cur.execute(f"DELETE FROM {table}")
    conn.commit()
    logger.info("Warehouse tables truncated for idempotent reload.")


def load_staging(
    conn: sqlite3.Connection,
    stores: pd.DataFrame,
    products: pd.DataFrame,
    clean_transactions: pd.DataFrame,
    quarantined_transactions: pd.DataFrame,
) -> None:
    """Load clean source data into staging tables."""
    stores.to_sql("stg_stores", conn, if_exists="append", index=False)
    products.to_sql("stg_products", conn, if_exists="append", index=False)

    txns = clean_transactions.copy()
    txns["transaction_date"] = txns["transaction_date"].dt.strftime("%Y-%m-%d")
    txns.to_sql("stg_transactions", conn, if_exists="append", index=False)

    if not quarantined_transactions.empty:
        q = quarantined_transactions.rename(columns={"_dq_reasons": "dq_reasons"})
        expected_cols = [
            "transaction_id", "transaction_date", "store_id", "product_id",
            "customer_id", "quantity", "discount_pct", "dq_reasons",
        ]
        q = q[[c for c in expected_cols if c in q.columns]]
        q.to_sql("stg_quarantined_transactions", conn, if_exists="append", index=False)

    conn.commit()
    logger.info(
        "Staging load complete: %d stores, %d products, %d clean txns, %d quarantined txns.",
        len(stores), len(products), len(clean_transactions), len(quarantined_transactions),
    )


def build_dimensions_and_facts(conn: sqlite3.Connection) -> None:
    """Transform staging tables into the star-schema dims + fact table."""
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO dim_store
        SELECT store_id, region, store_format, opened_year,
               (CAST(strftime('%Y', 'now') AS INTEGER) - opened_year) AS store_age_years
        FROM stg_stores
    """)

    cur.execute("""
        INSERT INTO dim_product
        SELECT product_id, category, unit_cost, unit_price,
               ROUND((unit_price - unit_cost) / unit_price * 100, 2) AS margin_pct
        FROM stg_products
    """)

    dates = pd.read_sql(
        "SELECT DISTINCT transaction_date AS date_key FROM stg_transactions", conn
    )
    dt = pd.to_datetime(dates["date_key"])
    dates["year"] = dt.dt.year
    dates["month"] = dt.dt.month
    dates["day_of_week"] = dt.dt.day_name()
    dates["is_weekend"] = dt.dt.dayofweek.isin([5, 6]).astype(int)
    dates.to_sql("dim_date", conn, if_exists="append", index=False)

    cur.execute("""
        INSERT INTO fact_sales
        SELECT
            t.transaction_id,
            t.transaction_date AS date_key,
            t.store_id,
            t.product_id,
            t.customer_id,
            t.quantity,
            t.discount_pct,
            ROUND(t.quantity * p.unit_price, 2) AS gross_revenue,
            ROUND(t.quantity * p.unit_price * (1 - t.discount_pct / 100.0), 2) AS net_revenue,
            ROUND(t.quantity * p.unit_cost, 2) AS cost_of_goods,
            ROUND(
                t.quantity * p.unit_price * (1 - t.discount_pct / 100.0) - t.quantity * p.unit_cost, 2
            ) AS gross_profit
        FROM stg_transactions t
        JOIN dim_product p ON t.product_id = p.product_id
    """)

    conn.commit()
    logger.info("Built dim_store, dim_product, dim_date, and fact_sales.")


def run_mart_models(conn: sqlite3.Connection) -> None:
    """Execute each dbt-style SQL mart model in sql/marts/."""
    marts_dir = SQL_DIR / "marts"
    for sql_file in sorted(marts_dir.glob("*.sql")):
        _run_script(conn, sql_file)
        logger.info("Ran mart model: %s", sql_file.name)
    conn.commit()
