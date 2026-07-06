"""Unit tests for src.quality.validators."""
import unittest

import pandas as pd

from src.quality.validators import validate_transactions


class TestValidateTransactions(unittest.TestCase):
    def setUp(self):
        self.valid_stores = {"ST-0001", "ST-0002"}
        self.valid_products = {"PRD-00001", "PRD-00002"}
        self.df = pd.DataFrame({
            "transaction_id": ["TXN-1", "TXN-2", "TXN-2", "TXN-3", "TXN-4", "TXN-5"],
            "transaction_date": ["2026-01-01", "2026-01-02", "2026-01-02", "not-a-date", "2026-01-04", "2026-01-05"],
            "store_id": ["ST-0001", "ST-0001", "ST-0001", "ST-0002", "ST-9999", "ST-0002"],
            "product_id": ["PRD-00001", "PRD-00002", "PRD-00002", "PRD-00001", "PRD-00001", "PRD-99999"],
            "customer_id": ["CUST-1", None, None, "CUST-3", "CUST-4", "CUST-5"],
            "quantity": [2, 1, 1, -1, 3, 0],
            "discount_pct": [10.0, 5.0, 5.0, 0.0, 200.0, 5.0],
        })

    def test_duplicate_transaction_id_quarantined(self):
        clean, quarantined, report = validate_transactions(self.df, self.valid_stores, self.valid_products)
        self.assertGreaterEqual(report["violation_counts"]["duplicate_transaction_id"], 1)

    def test_invalid_date_quarantined(self):
        _, quarantined, _ = validate_transactions(self.df, self.valid_stores, self.valid_products)
        self.assertIn("TXN-3", quarantined["transaction_id"].values)

    def test_unknown_store_quarantined(self):
        _, quarantined, _ = validate_transactions(self.df, self.valid_stores, self.valid_products)
        self.assertIn("TXN-4", quarantined["transaction_id"].values)

    def test_null_customer_id_not_quarantined(self):
        """Guest checkouts (null customer_id) should NOT be quarantined."""
        clean, quarantined, _ = validate_transactions(self.df, self.valid_stores, self.valid_products)
        # TXN-2 has a null customer_id but is otherwise fine except duplication;
        # verify null customer_id alone is never the sole quarantine reason.
        self.assertNotIn("null_customer_id", "".join(quarantined.get("_dq_reasons", pd.Series(dtype=str))))

    def test_clean_and_quarantined_partition_all_rows(self):
        clean, quarantined, report = validate_transactions(self.df, self.valid_stores, self.valid_products)
        self.assertEqual(len(clean) + len(quarantined), len(self.df))
        self.assertEqual(report["total_rows"], len(self.df))

    def test_report_structure(self):
        _, _, report = validate_transactions(self.df, self.valid_stores, self.valid_products)
        self.assertIn("violation_counts", report)
        self.assertIn("quarantine_rate", report)


if __name__ == "__main__":
    unittest.main()
