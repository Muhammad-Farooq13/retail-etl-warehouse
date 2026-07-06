# Deployment Guide

## 1. Local (no Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

make pipeline    # extract -> validate -> load -> transform -> mart models
make test        # run the full test suite
make serve       # analytics API at http://localhost:8001/docs
```

## 2. Docker Compose

```bash
docker compose --profile etl run --rm etl   # one-off pipeline run
docker compose up -d api                    # serve the analytics API
curl http://localhost:8001/health
```

## 3. Kubernetes

```bash
docker build -f docker/Dockerfile -t retail-etl-warehouse:latest .
kubectl apply -f deployment/kubernetes/deployment.yaml
kubectl apply -f deployment/kubernetes/service.yaml
kubectl get cronjob retail-etl-daily
kubectl get pods -l app=retail-analytics-api
```

The `CronJob` runs the ETL nightly and writes into a shared PVC; the API
`Deployment` mounts the same warehouse volume read-only, so a fresh
warehouse build doesn't require redeploying the API.

## 4. Cloud options

- **AWS**: Glue or a scheduled ECS/Fargate task for the ETL, RDS/Redshift
  in place of SQLite for the warehouse at scale, ECS/EKS for the API.
- **Azure**: Azure Data Factory or a scheduled Container App job for ETL,
  Azure SQL/Synapse for the warehouse.
- **GCP**: Cloud Composer (managed Airflow) for orchestration, BigQuery for
  the warehouse, Cloud Run for the API.

Because the transformation logic lives in plain SQL (`sql/marts/*.sql`) and
the schema is standard ANSI SQL, migrating off SQLite mainly means swapping
the `sqlite3` connection in `src/load/warehouse.py` for the target
database's driver — the mart SQL itself needs little to no rewriting.

## CI/CD

`.github/workflows/ci.yml` on every push/PR to `main`:
1. Lint (`ruff`) + format check (`black`).
2. Full `pytest` suite with coverage.
3. Full pipeline smoke test (`python -m src.pipeline`) — catches schema or
   SQL regressions that unit tests alone might miss.
4. Docker image build (build-only, no push).
