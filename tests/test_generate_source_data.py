"""Unit tests for src.extract.generate_source_data."""
import unittest

from src.extract.generate_source_data import generate_stores, generate_products, generate_transactions, _add_markup


class TestGenerateSourceData(unittest.TestCase):
    def test_stores_shape_and_uniqueness(self):
        stores = generate_stores(25, seed=1)
        self.assertEqual(len(stores), 25)
        self.assertEqual(stores["store_id"].nunique(), 25)

    def test_products_have_positive_costs(self):
        products = _add_markup(generate_products(50, seed=1), seed=1)
        self.assertTrue((products["unit_cost"] > 0).all())
        self.assertTrue((products["unit_price"] > products["unit_cost"]).all())

    def test_transactions_inject_expected_bad_row_rate(self):
        stores = generate_stores(10, seed=2)
        products = _add_markup(generate_products(20, seed=2), seed=2)
        txns = generate_transactions(
            n_transactions=2000,
            store_ids=stores["store_id"].tolist(),
            product_ids=products["product_id"].tolist(),
            bad_row_rate=0.05,
            seed=2,
        )
        self.assertEqual(len(txns), 2000)
        n_bad_dates = (txns["transaction_date"] == "not-a-date").sum()
        self.assertGreater(n_bad_dates, 0)

    def test_transactions_reproducible(self):
        stores = generate_stores(10, seed=3)
        products = _add_markup(generate_products(20, seed=3), seed=3)
        t1 = generate_transactions(500, stores["store_id"].tolist(), products["product_id"].tolist(), 0.03, seed=3)
        t2 = generate_transactions(500, stores["store_id"].tolist(), products["product_id"].tolist(), 0.03, seed=3)
        self.assertTrue(t1.equals(t2))


if __name__ == "__main__":
    unittest.main()
