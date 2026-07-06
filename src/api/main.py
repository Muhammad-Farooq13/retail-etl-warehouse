"""FastAPI analytics API serving read queries against the retail warehouse.

Run locally:
    uvicorn src.api.main:app --host 0.0.0.0 --port 8001 --reload
"""
from __future__ import annotations

import sqlite3
from typing import List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query

from src.load.warehouse import get_connection
from src.utils.config import load_config
from src.utils.logger import get_logger

logger = get_logger(__name__)
cfg = load_config()

app = FastAPI(
    title=cfg.api.title,
    version=cfg.api.version,
    description="Read-only analytics API over the retail data warehouse marts.",
)


def _query(sql: str, params: tuple = ()) -> List[dict]:
    conn = get_connection(cfg)
    try:
        df = pd.read_sql(sql, conn, params=params)
    finally:
        conn.close()
    return df.to_dict(orient="records")


@app.get("/health", tags=["monitoring"])
def health() -> dict:
    try:
        conn = get_connection(cfg)
        conn.execute("SELECT 1")
        conn.close()
        return {"status": "ok", "warehouse": "reachable"}
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail=f"Warehouse unreachable: {exc}") from exc


@app.get("/sales/daily", tags=["analytics"])
def daily_sales(
    store_id: Optional[str] = Query(None, description="Filter to a single store_id"),
    limit: int = Query(30, ge=1, le=1000),
) -> List[dict]:
    """Daily sales by store (most recent first)."""
    if store_id:
        sql = """
            SELECT * FROM mart_daily_sales_by_store
            WHERE store_id = ? ORDER BY date_key DESC LIMIT ?
        """
        return _query(sql, (store_id, limit))
    sql = "SELECT * FROM mart_daily_sales_by_store ORDER BY date_key DESC LIMIT ?"
    return _query(sql, (limit,))


@app.get("/sales/monthly-by-category", tags=["analytics"])
def monthly_sales_by_category(limit: int = Query(100, ge=1, le=1000)) -> List[dict]:
    """Monthly gross/net revenue and profit by product category."""
    sql = "SELECT * FROM mart_monthly_sales_by_category ORDER BY year_month DESC LIMIT ?"
    return _query(sql, (limit,))


@app.get("/customers/{customer_id}", tags=["analytics"])
def customer_summary(customer_id: str) -> dict:
    """Lifetime summary for a single customer."""
    result = _query(
        "SELECT * FROM mart_customer_summary WHERE customer_id = ?", (customer_id,)
    )
    if not result:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return result[0]


@app.get("/customers/top/by-revenue", tags=["analytics"])
def top_customers(limit: int = Query(10, ge=1, le=100)) -> List[dict]:
    """Top customers ranked by lifetime revenue."""
    sql = "SELECT * FROM mart_customer_summary ORDER BY lifetime_revenue DESC LIMIT ?"
    return _query(sql, (limit,))


@app.get("/", tags=["monitoring"])
def root() -> dict:
    return {"service": cfg.api.title, "version": cfg.api.version, "docs": "/docs"}
