"""Run EC_POLICY_V1 policy and verifier checks using integration-safe mock data."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agents.policy_agent import decide_policy
from src.agents.verifier_agent import verify_and_serialize


SCENARIOS = [
    ("canceled_order_paid", {"order_status": "canceled"}, {}, {"payment_total": 120.0}, 120.0),
    ("unavailable_order_paid", {"order_status": "unavailable"}, {}, {"payment_total": 120.0}, 120.0),
    ("late_delivery_seller", {}, {"delivered_after_estimate": True, "any_seller_handoff_late": True, "late_seller_ids": ["seller-1"]}, {"freight_total": 15.0}, 15.0),
    ("late_delivery_logistics", {}, {"delivered_after_estimate": True, "any_seller_handoff_late": False}, {"freight_total": 15.0}, 15.0),
    ("valid_split_payment", {}, {}, {"is_split_payment": True, "reconciled_within_010": True}, 0.0),
    ("unsupported_late_claim", {}, {}, {"reconciled_within_010": True}, 0.0),
]


def main() -> int:
    for index, (expected, order_seller, delivery, payment, expected_refund) in enumerate(SCENARIOS, 1):
        order_id = f"mock-order-{index}"
        order_seller.update({"item_ids": [f"{order_id}:1"], "seller_ids": ["seller-1"], "evidence": [f"order:{order_id}"]})
        delivery.setdefault("evidence", [])
        payment.update({"item_total": 100.0, "freight_total": payment.get("freight_total", 20.0), "payment_total": payment.get("payment_total", 120.0), "payment_ids": [f"{order_id}:1"], "evidence": [f"payment:{order_id}:1"]})
        decision = decide_policy(order_seller, delivery, payment)
        output = verify_and_serialize(
            {"case_id": f"EC_{index:03d}", "claimed_order_id": order_id},
            {"order_id": order_id, "items": []}, order_seller, payment, delivery, decision,
        )
        assert output["assessment"]["primary_issue"] == expected
        assert output["financial_resolution"]["recommended_refund_brl"] == expected_refund
    print("Mock policy/verifier smoke passed: 6/6 scenarios")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())