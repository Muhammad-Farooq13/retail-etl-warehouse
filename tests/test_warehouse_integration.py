"""Integration tests for src.load.warehouse using an in-memory SQLite DB."""
import sqlite3
import unittest

import pandas as pd

from src.load.warehouse import (
    build_dimensions_and_facts,
    init_schema,
    load_staging,
    run_mart_models,
)
from src.quality.validators import validate_transactions
from src.utils.config import load_config


class TestWarehouseIntegration(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.cfg = load_config()
        init_schema(self.conn, self.cfg)

        self.stores = pd.DataFrame({
            "store_id": ["ST-0001", "ST-0002"],
            "region": ["North", "South"],
            "store_format": ["standard", "express"],
            "opened_year": [2015, 2020],
        })
        self.products = pd.DataFrame({
            "product_id": ["PRD-00001", "PRD-00002"],
            "category": ["Grocery", "Electronics"],
            "unit_cost": [10.0, 100.0],
            "unit_price": [15.0, 150.0],
        })
        raw_txns = pd.DataFrame({
            "transaction_id": ["TXN-1", "TXN-2", "TXN-3"],
            "transaction_date": ["2026-01-01", "2026-01-02", "2026-01-02"],
            "store_id": ["ST-0001", "ST-0002", "ST-0001"],
            "product_id": ["PRD-00001", "PRD-00002", "PRD-00001"],
            "customer_id": ["CUST-1", None, "CUST-2"],
            "quantity": [2, 1, 3],
            "discount_pct": [10.0, 0.0, 5.0],
        })
        clean, quarantined, _ = validate_transactions(
            raw_txns, set(self.stores["store_id"]), set(self.products["product_id"])
        )
        load_staging(self.conn, self.stores, self.products, clean, quarantined)

    def tearDown(self):
        self.conn.close()

    def test_build_dimensions_and_facts(self):
        build_dimensions_and_facts(self.conn)
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM dim_store")
        self.assertEqual(cur.fetchone()[0], 2)
        cur.execute("SELECT COUNT(*) FROM fact_sales")
        self.assertEqual(cur.fetchone()[0], 3)

    def test_fact_sales_revenue_calculation_correct(self):
        build_dimensions_and_facts(self.conn)
        row = pd.read_sql(
            "SELECT * FROM fact_sales WHERE transaction_id = 'TXN-1'", self.conn
        ).iloc[0]
        # quantity=2, unit_price=15.0, discount=10% -> net_revenue = 2*15*0.9 = 27.0
        self.assertAlmostEqual(row["gross_revenue"], 30.0)
        self.assertAlmostEqual(row["net_revenue"], 27.0)
        self.assertAlmostEqual(row["cost_of_goods"], 20.0)

    def test_mart_models_produce_rows(self):
        build_dimensions_and_facts(self.conn)
        run_mart_models(self.conn)
        cur = self.conn.cursor()
        for table in ["mart_daily_sales_by_store", "mart_monthly_sales_by_category", "mart_customer_summary"]:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            self.assertGreater(cur.fetchone()[0], 0, f"{table} should have rows")

    def test_customer_summary_excludes_guest_checkouts(self):
        build_dimensions_and_facts(self.conn)
        run_mart_models(self.conn)
        customers = pd.read_sql("SELECT customer_id FROM mart_customer_summary", self.conn)
        self.assertNotIn(None, customers["customer_id"].values)


if __name__ == "__main__":
    unittest.main()
