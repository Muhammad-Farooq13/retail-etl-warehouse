"""Synthetic raw retail source data generator.

DATA PROVENANCE NOTE: built offline, no internet access to pull a live POS
export, so this generates a realistic multi-table retail dataset
(transactions, stores, products) with intentionally injected data-quality
issues (nulls, duplicates, negative quantities, malformed dates, orphaned
foreign keys) at a controlled rate. This lets the ETL pipeline's data
quality/validation layer be exercised and demonstrated honestly, exactly as
it would be against a real messy source system. Swap `extract_transactions`,
`extract_stores`, `extract_products` for real `pd.read_csv(...)` /
`pd.read_sql(...)` calls against your real source to use this pipeline in
production.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.utils.config import load_config, resolve_path
from src.utils.logger import get_logger

logger = get_logger(__name__)


def generate_stores(n_stores: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    regions = ["North", "South", "East", "West", "Central"]
    formats = ["flagship", "standard", "express"]
    return pd.DataFrame({
        "store_id": [f"ST-{i:04d}" for i in range(1, n_stores + 1)],
        "region": rng.choice(regions, n_stores),
        "store_format": rng.choice(formats, n_stores, p=[0.15, 0.6, 0.25]),
        "opened_year": rng.integers(2005, 2025, n_stores),
    })


def generate_products(n_products: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 1)
    categories = ["Grocery", "Electronics", "Apparel", "Home & Garden", "Health & Beauty", "Toys"]
    return pd.DataFrame({
        "product_id": [f"PRD-{i:05d}" for i in range(1, n_products + 1)],
        "category": rng.choice(categories, n_products),
        "unit_cost": np.clip(rng.gamma(2, 8, n_products), 1, 300).round(2),
        "unit_price": None,  # filled below with a markup
    })


def _add_markup(products: pd.DataFrame, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 2)
    markup = rng.uniform(1.2, 2.4, len(products))
    products = products.copy()
    products["unit_price"] = (products["unit_cost"] * markup).round(2)
    return products


def generate_transactions(
    n_transactions: int,
    store_ids: list[str],
    product_ids: list[str],
    bad_row_rate: float,
    seed: int,
) -> pd.DataFrame:
    """Generate raw transaction line items, with injected messiness.

    Injected issues (at bad_row_rate, split across types): null customer_id,
    duplicate transaction_id, negative/zero quantity, malformed date strings,
    and product_id foreign keys that don't exist in the products table
    ("orphaned" rows) — all realistic POS-export defects.
    """
    rng = np.random.default_rng(seed + 3)

    dates = pd.date_range("2025-01-01", "2026-06-30", freq="D")
    txn_dates = rng.choice(dates, n_transactions)

    df = pd.DataFrame({
        "transaction_id": [f"TXN-{i:08d}" for i in range(n_transactions)],
        "transaction_date": pd.to_datetime(txn_dates).strftime("%Y-%m-%d"),
        "store_id": rng.choice(store_ids, n_transactions),
        "product_id": rng.choice(product_ids, n_transactions),
        "customer_id": [f"CUST-{i:06d}" for i in rng.integers(0, 8000, n_transactions)],
        "quantity": rng.integers(1, 6, n_transactions),
        "discount_pct": np.clip(rng.exponential(4, n_transactions), 0, 40).round(1),
    })

    n_bad = int(n_transactions * bad_row_rate)
    if n_bad > 0:
        bad_idx = rng.choice(df.index, size=n_bad, replace=False)
        chunks = np.array_split(bad_idx, 5)

        # 1. null customer_id
        df.loc[chunks[0], "customer_id"] = None
        # 2. duplicate transaction_id (copy an existing id onto a different row)
        if len(chunks[1]) > 0:
            donor_ids = df.loc[rng.choice(df.index, len(chunks[1])), "transaction_id"].values
            df.loc[chunks[1], "transaction_id"] = donor_ids
        # 3. negative/zero quantity
        df.loc[chunks[2], "quantity"] = rng.integers(-3, 1, len(chunks[2]))
        # 4. malformed date strings
        df.loc[chunks[3], "transaction_date"] = "not-a-date"
        # 5. orphaned product_id (references a product that doesn't exist)
        df.loc[chunks[4], "product_id"] = [f"PRD-99{i:03d}" for i in range(len(chunks[4]))]

    logger.info(
        "Generated %d raw transactions (%.1f%% intentionally messy for QA testing)",
        len(df), 100 * bad_row_rate,
    )
    return df


def main() -> None:
    cfg = load_config()
    seed = cfg.project.random_seed

    stores = generate_stores(cfg.data.n_stores, seed)
    products = _add_markup(generate_products(cfg.data.n_products, seed), seed)
    transactions = generate_transactions(
        cfg.data.n_transactions,
        stores["store_id"].tolist(),
        products["product_id"].tolist(),
        cfg.data.bad_row_injection_rate,
        seed,
    )

    for name, df, path_key in [
        ("stores", stores, "raw_stores_path"),
        ("products", products, "raw_products_path"),
        ("transactions", transactions, "raw_transactions_path"),
    ]:
        out_path = resolve_path(cfg.data[path_key])
        out_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_path, index=False)
        logger.info("Saved raw %s to %s (%d rows)", name, out_path, len(df))


if __name__ == "__main__":
    main()
