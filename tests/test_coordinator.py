from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from src.contracts import CaseInput
from src.coordinator import Coordinator


SCENARIOS = {
    "fixture_canceled_paid": ("canceled_order_paid", 100.0),
    "fixture_unavailable_paid": ("unavailable_order_paid", 60.0),
    "fixture_late_seller": ("late_delivery_seller", 15.0),
    "fixture_late_logistics": ("late_delivery_logistics", 15.0),
    "fixture_split_payment": ("valid_split_payment", 0.0),
    "fixture_delivered_ontime": ("unsupported_late_claim", 0.0),
}


def _case(order_id: str) -> CaseInput:
    return CaseInput(
        case_id="EC_TEST",
        opened_at="2018-10-18T00:00:00-03:00",
        language="vi",
        message="Test case",
        claimed_order_id=order_id,
        policy_version="EC_POLICY_V1",
    )


class CoordinatorFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = patch.dict(os.environ, {"FIXTURE_MODE": "1"})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.coordinator = Coordinator()

    def test_all_policy_branches(self) -> None:
        for order_id, (expected_issue, expected_refund) in SCENARIOS.items():
            with self.subTest(order_id=order_id):
                output = self.coordinator.process_case(_case(order_id))
                self.assertEqual(expected_issue, output.assessment["primary_issue"])
                self.assertEqual(1.0, output.assessment["confidence"])
                self.assertEqual(
                    expected_refund,
                    output.financial_resolution["recommended_refund_brl"],
                )
                self.assertTrue(any(
                    evidence.startswith("policy:")
                    for evidence in output.evidence_ids
                ))
                evidence_order = {
                    "order": 0, "item": 1, "payment": 2, "seller": 3, "policy": 4,
                }
                evidence_ranks = [
                    evidence_order[evidence.split(":", 1)[0]]
                    for evidence in output.evidence_ids
                ]
                self.assertEqual(sorted(evidence_ranks), evidence_ranks)
                payment_sequences = [
                    int(payment_id.rsplit(":", 1)[1])
                    for payment_id in output.affected_entities["payment_ids"]
                ]
                self.assertEqual(sorted(payment_sequences), payment_sequences)

    def test_no_items_has_empty_item_and_seller_entities(self) -> None:
        output = self.coordinator.process_case(_case("fixture_no_items"))
        self.assertEqual([], output.affected_entities["item_ids"])
        self.assertEqual([], output.affected_entities["seller_ids"])
        self.assertEqual(0.0, output.financial_resolution["item_total_brl"])
        self.assertEqual(0.0, output.financial_resolution["freight_total_brl"])

    def test_missing_order_does_not_emit_unverified_entities(self) -> None:
        output = self.coordinator.process_case(_case("fixture_missing_order"))
        self.assertEqual([], output.affected_entities["order_ids"])
        self.assertEqual([], output.affected_entities["item_ids"])
        self.assertEqual([], output.affected_entities["seller_ids"])
        self.assertEqual([], output.affected_entities["payment_ids"])
        self.assertEqual(["policy:DELIVERY_WITHIN_ESTIMATE"], output.evidence_ids)


if __name__ == "__main__":
    unittest.main()