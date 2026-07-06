"""Airflow DAG: daily retail ETL pipeline orchestration.

Requires an Airflow environment (`pip install apache-airflow`) to actually
run; not executed as part of this repo's test suite (see README
transparency section). Shows how the single-process `run_pipeline()` call
scales into a scheduled, monitored, alerting-capable production DAG.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "data-engineering-team",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def _extract_and_validate(**context) -> None:
    import json
    from src.extract.readers import extract_products, extract_stores, extract_transactions
    from src.quality.validators import validate_transactions
    from src.utils.config import load_config, resolve_path

    cfg = load_config()
    stores = extract_stores(cfg)
    products = extract_products(cfg)
    transactions = extract_transactions(cfg)
    clean, quarantined, report = validate_transactions(
        transactions, set(stores["store_id"]), set(products["product_id"])
    )

    if report["quarantine_rate"] > 0.10:
        raise ValueError(
            f"Data quality gate failed: {report['quarantine_rate']:.2%} of rows quarantined "
            "(threshold 10%). Investigate upstream source system before proceeding."
        )

    # Push small artifacts via XCom; large DataFrames would go to a shared
    # object store (S3/GCS) in a real deployment rather than XCom.
    context["ti"].xcom_push(key="dq_report", value=json.dumps(report))


def _load_and_transform(**context) -> None:
    from src.pipeline import run_pipeline
    run_pipeline()


def _run_data_quality_smoke_check(**context) -> None:
    """Post-load sanity check: marts should be non-empty and fact table should reconcile."""
    from src.load.warehouse import get_connection
    from src.utils.config import load_config

    conn = get_connection(load_config())
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM fact_sales")
    fact_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM mart_daily_sales_by_store")
    mart_count = cur.fetchone()[0]
    conn.close()

    if fact_count == 0 or mart_count == 0:
        raise ValueError("Post-load smoke check failed: fact/mart tables are empty.")


with DAG(
    dag_id="retail_etl_daily",
    default_args=default_args,
    description="Daily ETL: extract -> validate -> load -> transform -> mart models",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["etl", "retail", "warehouse"],
) as dag:

    extract_validate = PythonOperator(
        task_id="extract_and_validate",
        python_callable=_extract_and_validate,
    )

    load_transform = PythonOperator(
        task_id="load_and_transform",
        python_callable=_load_and_transform,
    )

    smoke_check = PythonOperator(
        task_id="post_load_smoke_check",
        python_callable=_run_data_quality_smoke_check,
    )

    extract_validate >> load_transform >> smoke_check
