import csv
import tempfile
import unittest
from pathlib import Path

from role3_payment_agent import PaymentAgent


class PaymentAgentTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.payments = root / "payments.csv"
        self.items = root / "items.csv"
        self.orders = root / "orders.csv"

        self._write(
            self.payments,
            [
                "order_id",
                "payment_sequential",
                "payment_type",
                "payment_installments",
                "payment_value",
            ],
            [
                ["normal", 1, "credit_card", 2, "110.00"],
                ["split", 2, "voucher", 1, "20.00"],
                ["split", 1, "credit_card", 1, "90.05"],
                ["canceled", 1, "credit_card", 1, "55.00"],
                ["mismatch", 1, "credit_card", 1, "109.89"],
                ["boundary", 1, "credit_card", 1, "110.10"],
            ],
        )
        self._write(
            self.items,
            ["order_id", "order_item_id", "price", "freight_value"],
            [
                ["normal", 1, "100.00", "10.00"],
                ["split", 1, "100.00", "10.00"],
                ["canceled", 1, "50.00", "5.00"],
                ["mismatch", 1, "100.00", "10.00"],
                ["boundary", 1, "100.00", "10.00"],
            ],
        )
        self._write(
            self.orders,
            ["order_id", "order_status"],
            [
                ["normal", "delivered"],
                ["split", "delivered"],
                ["canceled", "canceled"],
                ["mismatch", "delivered"],
                ["no_rows", "created"],
                ["boundary", "delivered"],
            ],
        )
        self.agent = PaymentAgent(self.payments, self.items, self.orders)

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def _write(path, fields, rows):
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(fields)
            writer.writerows(rows)

    def test_single_payment_reconciles(self):
        result = self.agent.analyze("normal")
        self.assertTrue(result["is_reconciled"])
        self.assertFalse(result["is_split_payment"])
        self.assertFalse(result["payment_ids_truncated"])
        self.assertEqual(result["financial_resolution"]["payment_total_brl"], 110.0)

    def test_split_payment_within_tolerance(self):
        result = self.agent.analyze("split", "valid_split_payment")
        self.assertTrue(result["is_split_payment"])
        self.assertTrue(result["is_valid_split_payment"])
        self.assertTrue(result["is_reconciled"])
        self.assertEqual(result["payment_ids"], ["split:1", "split:2"])
        self.assertEqual(result["financial_resolution"]["recommended_refund_brl"], 0.0)

    def test_difference_above_tolerance_does_not_reconcile(self):
        result = self.agent.analyze("mismatch")
        self.assertFalse(result["is_reconciled"])
        self.assertEqual(result["reconciliation_difference_brl"], -0.11)
        self.assertEqual(result["anomalies"], ["PAYMENT_TOTAL_MISMATCH"])

    def test_exact_tolerance_is_reconciled(self):
        result = self.agent.analyze("boundary")
        self.assertTrue(result["is_reconciled"])
        self.assertEqual(result["reconciliation_difference_brl"], 0.1)

    def test_canceled_paid_order_is_inferred_and_fully_refunded(self):
        result = self.agent.analyze("canceled")
        self.assertEqual(result["financial_resolution"]["recommended_refund_brl"], 55.0)
        self.assertEqual(result["financial_issue_candidate"], "canceled_order_paid")

    def test_late_delivery_refunds_freight(self):
        result = self.agent.analyze("normal", "late_delivery_logistics")
        self.assertEqual(result["financial_resolution"]["recommended_refund_brl"], 10.0)

    def test_order_without_item_or_payment_rows_returns_zeroes(self):
        result = self.agent.analyze("no_rows")
        self.assertTrue(result["is_reconciled"])
        self.assertEqual(result["payment_ids"], [])
        self.assertEqual(
            result["financial_resolution"],
            {
                "currency": "BRL",
                "item_total_brl": 0.0,
                "freight_total_brl": 0.0,
                "expected_total_brl": 0.0,
                "payment_total_brl": 0.0,
                "recommended_refund_brl": 0.0,
            },
        )

    def test_unknown_order_and_issue_fail_loudly(self):
        with self.assertRaises(KeyError):
            self.agent.analyze("missing")
        with self.assertRaises(ValueError):
            self.agent.analyze("normal", "invented_issue")

    def test_case_handoff_contract_is_validated(self):
        case = {
            "case_id": "EC_TEST",
            "policy_version": "EC_POLICY_V1",
            "customer_request": {"claimed_order_id": "normal"},
        }
        result = self.agent.analyze_case(case, "unsupported_late_claim")
        self.assertEqual(result["case_id"], "EC_TEST")
        self.assertEqual(result["agent"], "payment_agent")
        self.assertEqual(result["handoff_status"], "completed")
        self.assertEqual(len(result["trace"]), 4)

        bad_case = dict(case, policy_version="UNKNOWN")
        with self.assertRaises(ValueError):
            self.agent.analyze_case(bad_case)


class RealInputIntegrationTest(unittest.TestCase):
    def test_all_50_repository_cases(self):
        root = Path(__file__).resolve().parents[2]
        input_paths = sorted((root / "input").glob("EC_*.json"))
        if not input_paths:
            self.skipTest("repository inputs are not present")

        agent = PaymentAgent()
        results = agent.analyze_input_directory(root / "input")
        self.assertEqual(len(results), 50)
        self.assertEqual({row["handoff_status"] for row in results}, {"completed"})
        self.assertEqual(sum(row["is_split_payment"] for row in results), 9)
        self.assertEqual(sum(row["is_reconciled"] for row in results), 42)
        self.assertEqual(
            {row["case_id"] for row in results},
            {f"EC_{number:03d}" for number in range(1, 51)},
        )


if __name__ == "__main__":
    unittest.main()
