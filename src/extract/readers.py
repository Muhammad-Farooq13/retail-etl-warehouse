"""Extraction layer: reads raw source data into pandas DataFrames.

In a real deployment, these functions would connect to the actual source
systems (POS database, e-commerce API, ERP export bucket, etc.) instead of
reading local CSVs. Keeping extraction isolated in its own module means
swapping the source system later only requires changing this file.
"""
from __future__ import annotations

import pandas as pd

from src.extract.generate_source_data import main as generate_raw_data
from src.utils.config import load_config, resolve_path
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _ensure_raw_data_exists(cfg) -> None:
    """Generate all raw source files together if any are missing.

    The three source tables are generated in one shot (they're related:
    transactions reference store_id/product_id), so we check all three
    paths and regenerate together if any is absent, rather than generating
    piecemeal per-table.
    """
    paths = [
        resolve_path(cfg.data.raw_stores_path),
        resolve_path(cfg.data.raw_products_path),
        resolve_path(cfg.data.raw_transactions_path),
    ]
    if not all(p.exists() for p in paths):
        logger.info("One or more raw source files missing; generating synthetic source data.")
        generate_raw_data()


def extract_transactions(cfg=None) -> pd.DataFrame:
    cfg = cfg or load_config()
    _ensure_raw_data_exists(cfg)
    path = resolve_path(cfg.data.raw_transactions_path)
    df = pd.read_csv(path, dtype={"customer_id": "string"})
    logger.info("Extracted %d raw transaction rows from %s", len(df), path)
    return df


def extract_stores(cfg=None) -> pd.DataFrame:
    cfg = cfg or load_config()
    _ensure_raw_data_exists(cfg)
    path = resolve_path(cfg.data.raw_stores_path)
    df = pd.read_csv(path)
    logger.info("Extracted %d store rows from %s", len(df), path)
    return df


def extract_products(cfg=None) -> pd.DataFrame:
    cfg = cfg or load_config()
    _ensure_raw_data_exists(cfg)
    path = resolve_path(cfg.data.raw_products_path)
    df = pd.read_csv(path)
    logger.info("Extracted %d product rows from %s", len(df), path)
    return df
