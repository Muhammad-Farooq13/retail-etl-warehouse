# Architecture

## Pipeline overview

```mermaid
flowchart LR
    A[Extract<br/>stores.csv, products.csv, transactions.csv] --> B[Validate<br/>src/quality/validators.py]
    B -->|clean rows| C[Load: Staging Tables<br/>stg_stores, stg_products, stg_transactions]
    B -->|quarantined rows| Q[stg_quarantined_transactions<br/>auditable, not dropped]
    C --> D[Transform<br/>dim_store, dim_product, dim_date, fact_sales]
    D --> E[Mart Models<br/>sql/marts/*.sql]
    E --> F[(SQLite Warehouse<br/>data/warehouse/retail.db)]
    F --> G[Analytics API<br/>src/api/main.py]
    F --> H[BI tools / notebooks]
```

## Star schema

```mermaid
erDiagram
    dim_store ||--o{ fact_sales : "sold at"
    dim_product ||--o{ fact_sales : "product of"
    dim_date ||--o{ fact_sales : "occurred on"

    dim_store {
        text store_id PK
        text region
        text store_format
        int opened_year
        int store_age_years
    }
    dim_product {
        text product_id PK
        text category
        real unit_cost
        real unit_price
        real margin_pct
    }
    dim_date {
        text date_key PK
        int year
        int month
        text day_of_week
        int is_weekend
    }
    fact_sales {
        text transaction_id PK
        text date_key FK
        text store_id FK
        text product_id FK
        text customer_id
        int quantity
        real discount_pct
        real gross_revenue
        real net_revenue
        real gross_profit
    }
```

## Data quality gate

```mermaid
flowchart TD
    A[Raw transactions] --> B{Validate}
    B -->|duplicate transaction_id| Q[Quarantine]
    B -->|invalid date| Q
    B -->|quantity <= 0| Q
    B -->|unknown store_id / product_id FK| Q
    B -->|discount out of range| Q
    B -->|passes all checks| C[Clean staging table]
    Q --> R[stg_quarantined_transactions<br/>+ dq_reasons column]
    R --> S[artifacts/reports/data_quality_report.json]
```

Rows are **quarantined, not silently dropped** — every excluded row remains
queryable with its specific violation reason(s), which is what a real
incident review ("why is store ST-0007's revenue lower than expected this
week?") actually requires.

## Why this stack

| Layer | Choice | Why |
|---|---|---|
| Warehouse | SQLite | Zero setup, fully portable, and the schema/SQL is standard enough to port directly to Postgres/Snowflake/BigQuery by changing only the connection layer. |
| Transformations | Plain SQL files under `sql/marts/`, dbt-style | Same modeling pattern as dbt (one `.sql` file = one model), without requiring a dbt install in this offline sandbox — trivially portable to a real dbt project later. |
| Validation | Custom Python validators with quarantine tables | Explicit, auditable, and testable — no hidden framework magic between "bad row" and "why it was excluded." |
| Serving | FastAPI read-only analytics API | Lets BI tools/dashboards query marts over HTTP instead of needing direct DB file access. |
| Orchestration | Airflow DAG (optional, `pipelines/`) | Standard way to schedule, retry, and alert on a daily ETL job in production. |
| Packaging | Multi-stage Docker + Kubernetes CronJob + Deployment | CronJob runs the nightly ETL; Deployment serves the API — decoupled so API uptime doesn't depend on ETL run time. |
