"""End-to-end ETL pipeline orchestrator.

Run: python -m src.pipeline
"""
from __future__ import annotations

import json
from typing import Any, Dict

from src.extract.readers import extract_products, extract_stores, extract_transactions
from src.load.warehouse import (
    build_dimensions_and_facts,
    get_connection,
    init_schema,
    load_staging,
    reset_warehouse,
    run_mart_models,
)
from src.quality.validators import validate_transactions
from src.utils.config import load_config, resolve_path
from src.utils.logger import get_logger

logger = get_logger(__name__)


def run_pipeline() -> Dict[str, Any]:
    """Run the full extract -> validate -> load -> transform -> mart pipeline."""
    cfg = load_config()

    logger.info("=== STEP 1/5: EXTRACT ===")
    stores = extract_stores(cfg)
    products = extract_products(cfg)
    transactions = extract_transactions(cfg)

    logger.info("=== STEP 2/5: VALIDATE (data quality) ===")
    clean_txns, quarantined_txns, dq_report = validate_transactions(
        transactions, set(stores["store_id"]), set(products["product_id"])
    )

    report_path = resolve_path(cfg.quality.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(dq_report, f, indent=2)

    if (
        cfg.quality.fail_pipeline_on_violation
        and dq_report["quarantine_rate"] > cfg.quality.max_duplicate_rate
    ):
        raise RuntimeError(
            f"Data quality gate failed: quarantine rate {dq_report['quarantine_rate']:.2%} "
            f"exceeds threshold. See {report_path}"
        )

    logger.info("=== STEP 3/5: LOAD (staging) ===")
    conn = get_connection(cfg)
    init_schema(conn, cfg)
    reset_warehouse(conn)  # idempotent re-run
    load_staging(conn, stores, products, clean_txns, quarantined_txns)

    logger.info("=== STEP 4/5: TRANSFORM (star schema) ===")
    build_dimensions_and_facts(conn)

    logger.info("=== STEP 5/5: MART MODELS ===")
    run_mart_models(conn)
    conn.close()

    summary = {
        "dq_report": dq_report,
        "warehouse_path": str(resolve_path(cfg.warehouse.db_path)),
    }
    logger.info("Pipeline completed successfully. Summary: %s", json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    run_pipeline()
