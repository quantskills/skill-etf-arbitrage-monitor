from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import etf_arb_report  # noqa: E402
import premium  # noqa: E402


class MissingCriticalDataSource:
    backend = "fixture"

    def etf_cr(self, symbol, start, end):
        return []

    def fund_daily(self, symbol, start, end):
        return [{"symbol": symbol, "date": "20260724", "close": 4.0,
                 "discount_rate": -0.005, "amount": None}]

    def etf_constituents(self, symbol, start, end):
        return []

    def stock_daily(self, symbols, start, end):
        return []


class ETFRegressionTests(unittest.TestCase):
    def test_ratio_discount_rate_converts_to_bps(self):
        got = premium.premium_from_interface(
            [{"date": "20260724", "close": 4.0, "discount_rate": -0.003}]
        )
        self.assertEqual(got["premium_bps"], 30.0)
        self.assertEqual(got["discount_rate_unit"], "ratio")

    def test_constituents_use_selected_date_and_deduplicate(self):
        rows = [
            {"date": "20260723", "stock_symbol": "A", "quantity": 100},
            {"date": "20260724", "stock_symbol": "A", "quantity": 100},
            {"date": "20260724", "stock_symbol": "A", "quantity": 100},
        ]
        selected = premium.constituents_for_date(rows, "20260724")
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["date"], "20260724")

    def test_missing_cr_or_amount_is_not_actionable(self):
        report = etf_arb_report.build_report(
            ["510300.SH"], 30, 20, 1000,
            data_source=MissingCriticalDataSource(),
        )
        item = report["items"][0]
        self.assertFalse(item["actionable"])
        self.assertFalse(item["feasible"])
        self.assertEqual(report["status"], "failed")

    def test_output_contract_fields_present(self):
        report = etf_arb_report.build_report(
            ["510300.SH"], 30, 20, 1000,
            data_source=MissingCriticalDataSource(),
        )
        item = report["items"][0]
        required = {"iopv", "price", "direction", "feasible", "data_date", "sources"}
        self.assertLessEqual(required, item.keys())
        self.assertIn("degraded", report)

    def test_nan_discount_rate_is_missing_not_a_false_discount_signal(self):
        got = premium.premium_from_interface(
            [{"date": "20260728", "close": 4.0, "discount_rate": float("nan")}]
        )
        self.assertIsNone(got)


if __name__ == "__main__":
    unittest.main()
