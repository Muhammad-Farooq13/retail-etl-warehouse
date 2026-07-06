# API Reference

Interactive Swagger/OpenAPI docs auto-generated at **`/docs`** (ReDoc at
**`/redoc`**) whenever the service is running.

Base URL (local): `http://localhost:8001`

## `GET /health`
```bash
curl http://localhost:8001/health
```
```json
{"status": "ok", "warehouse": "reachable"}
```

## `GET /sales/daily?store_id=ST-0001&limit=7`
Daily sales for a store, most recent first.
```json
[
  {"date_key": "2026-06-30", "store_id": "ST-0001", "region": "North",
   "n_transactions": 42, "total_quantity": 118, "gross_revenue": 3120.5,
   "net_revenue": 2890.1, "gross_profit": 1210.4}
]
```

## `GET /sales/monthly-by-category?limit=12`
Monthly revenue/profit rollup by product category.

## `GET /customers/{customer_id}`
Lifetime summary for one customer. `404` if not found.

## `GET /customers/top/by-revenue?limit=10`
Top customers ranked by lifetime net revenue.

## Error responses

| Status | Meaning |
|---|---|
| `404` | Customer not found |
| `503` | Warehouse database unreachable — run `make pipeline` first |
