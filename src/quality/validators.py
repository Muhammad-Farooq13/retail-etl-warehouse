"""Data quality validation and quarantine logic.

Runs a battery of checks against raw extracted data and separates each
table into `(clean_rows, quarantined_rows, report)`. Rows are quarantined
(not silently dropped) so they remain auditable — a real data engineering
team needs to be able to answer "which specific rows did we exclude and
why?" during an incident review.
"""
from __future__ import annotations

from typing import Dict, Tuple

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)


def _mark_violation(df: pd.DataFrame, mask: pd.Series, reason: str, reasons_col: str = "_dq_reasons") -> None:
    """Append a violation reason to the reasons column for rows matching mask."""
    if reasons_col not in df.columns:
        df[reasons_col] = ""
    existing = df.loc[mask, reasons_col]
    df.loc[mask, reasons_col] = existing.where(existing == "", existing + "; ") + reason


def validate_transactions(
    df: pd.DataFrame, valid_store_ids: set, valid_product_ids: set
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
    """Validate raw transactions and split into clean vs. quarantined rows.

    Checks:
        - transaction_id uniqueness
        - transaction_date parses as a valid date
        - quantity > 0
        - store_id exists in the stores dimension
        - product_id exists in the products dimension
        - discount_pct within [0, 100]

    customer_id nulls are NOT quarantined (guest checkouts are legitimate in
    retail); they are instead flagged downstream as "guest" in the mart.
    """
    df = df.copy()
    df["_dq_reasons"] = ""

    duplicated_mask = df.duplicated(subset=["transaction_id"], keep="first")
    _mark_violation(df, duplicated_mask, "duplicate_transaction_id")

    parsed_dates = pd.to_datetime(df["transaction_date"], errors="coerce")
    bad_date_mask = parsed_dates.isna()
    _mark_violation(df, bad_date_mask, "invalid_transaction_date")

    bad_qty_mask = df["quantity"] <= 0
    _mark_violation(df, bad_qty_mask, "non_positive_quantity")

    bad_store_mask = ~df["store_id"].isin(valid_store_ids)
    _mark_violation(df, bad_store_mask, "unknown_store_id")

    bad_product_mask = ~df["product_id"].isin(valid_product_ids)
    _mark_violation(df, bad_product_mask, "unknown_product_id")

    bad_discount_mask = (df["discount_pct"] < 0) | (df["discount_pct"] > 100)
    _mark_violation(df, bad_discount_mask, "discount_out_of_range")

    is_dirty = df["_dq_reasons"] != ""
    clean = df.loc[~is_dirty].drop(columns=["_dq_reasons"]).copy()
    clean["transaction_date"] = pd.to_datetime(clean["transaction_date"])
    quarantined = df.loc[is_dirty].copy()

    total = len(df)
    report = {
        "table": "transactions",
        "total_rows": total,
        "clean_rows": len(clean),
        "quarantined_rows": len(quarantined),
        "quarantine_rate": round(len(quarantined) / total, 4) if total else 0.0,
        "null_customer_id_count": int(df["customer_id"].isna().sum()),
        "violation_counts": {
            "duplicate_transaction_id": int(duplicated_mask.sum()),
            "invalid_transaction_date": int(bad_date_mask.sum()),
            "non_positive_quantity": int(bad_qty_mask.sum()),
            "unknown_store_id": int(bad_store_mask.sum()),
            "unknown_product_id": int(bad_product_mask.sum()),
            "discount_out_of_range": int(bad_discount_mask.sum()),
        },
    }
    logger.info(
        "Transaction validation: %d/%d rows clean (%.2f%% quarantined)",
        report["clean_rows"], total, 100 * report["quarantine_rate"],
    )
    return clean, quarantined, report
