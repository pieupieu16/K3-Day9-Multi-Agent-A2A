from __future__ import annotations

import csv
from pathlib import Path

import pytest

from src.agents.payment_agent import PaymentAgent
from src.contracts import CaseInput, ItemFact, OrderFacts, PaymentFact, PaymentFinding
from src.financial import calculate_totals, compute_refund, is_reconciled


ROOT = Path(__file__).resolve().parents[1]
REAL_ORDER_TOTALS = {
    "00010242fe8c5a6d1ba2dd792cb16214": (58.90, 13.29, 72.19),
    "00018f77f2f0320c557190d7a144bdd3": (239.90, 19.93, 259.83),
    "000229ec398224ef6ca0657da4fc703e": (199.00, 17.87, 216.87),
    "00024acbcdf0a6daa1e931b038114c75": (12.99, 12.79, 25.78),
    "00042b26cf59d7ce69dfabb4e55b4fd9": (199.90, 18.14, 218.04),
}


def _case(order_id: str = "order-1") -> CaseInput:
    return CaseInput("EC_TEST", "", "vi", "", order_id, "EC_POLICY_V1")


def _facts(
    item_values: list[tuple[float, float]],
    payment_values: list[float],
    order_id: str = "order-1",
) -> OrderFacts:
    return OrderFacts(
        found=True,
        order_id=order_id,
        items=[
            ItemFact(order_id, index, f"product-{index}", "seller-1", None, price, freight)
            for index, (price, freight) in enumerate(item_values, 1)
        ],
        payments=[
            PaymentFact(order_id, index, "credit_card", 1, value)
            for index, value in enumerate(payment_values, 1)
        ],
    )


@pytest.mark.parametrize(
    ("items", "payments", "expected"),
    [
        ([(10.10, 1.20)], [11.30], (10.10, 1.20, 11.30)),
        ([(20.00, 2.50), (30.00, 3.50)], [56.00], (50.00, 6.00, 56.00)),
        ([(0.10, 0.10), (0.20, 0.20)], [0.60], (0.30, 0.30, 0.60)),
        ([(99.999, 5.555)], [105.554], (100.00, 5.56, 105.55)),
        ([(25.00, 0.00)], [10.00, 15.00], (25.00, 0.00, 25.00)),
    ],
)
def test_decimal_rounding_examples(items, payments, expected):
    facts = _facts(items, payments)
    assert calculate_totals(facts.items, facts.payments) == expected


def test_five_real_olist_orders_match_hand_checked_totals():
    wanted = set(REAL_ORDER_TOTALS)
    item_rows = {order_id: [] for order_id in wanted}
    payment_rows = {order_id: [] for order_id in wanted}

    with (ROOT / "data" / "olist_order_items_dataset.csv").open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            order_id = row["order_id"]
            if order_id in wanted:
                item_rows[order_id].append((float(row["price"]), float(row["freight_value"])))

    with (ROOT / "data" / "olist_order_payments_dataset.csv").open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            order_id = row["order_id"]
            if order_id in wanted:
                payment_rows[order_id].append(float(row["payment_value"]))

    for order_id, expected in REAL_ORDER_TOTALS.items():
        facts = _facts(item_rows[order_id], payment_rows[order_id], order_id)
        assert calculate_totals(facts.items, facts.payments) == expected


def test_payment_agent_uses_deterministic_values_and_valid_ids(monkeypatch):
    facts = _facts([(80.0, 15.0)], [50.0, 45.0])
    monkeypatch.setattr(
        "src.agents.payment_agent.call_llm",
        lambda *args, **kwargs: {"payment_total": -999, "notes": "Payment rows reconcile."},
    )

    finding = PaymentAgent.run(_case(), facts)

    assert finding.payment_total == 95.0
    assert finding.is_split_payment is True
    assert finding.reconciled_within_010 is True
    assert finding.payment_ids == ["order-1:1", "order-1:2"]
    assert finding.evidence == ["payment:order-1:1", "payment:order-1:2"]
    assert finding.notes == "Payment rows reconcile."


def test_no_item_rows_produce_zero_item_and_freight_totals():
    finding = PaymentAgent.run(_case(), _facts([], [12.5]))
    assert finding.item_total == 0.0
    assert finding.freight_total == 0.0


def test_reconciliation_boundary_is_inclusive():
    assert is_reconciled(100.10, 90.0, 10.0) is True
    assert is_reconciled(100.11, 90.0, 10.0) is False


def test_compute_refund_follows_policy_and_rounds():
    finding = PaymentFinding(1, 100.005, 90.0, 10.005, True, False, [], [])
    assert compute_refund("canceled_order_paid", finding) == 100.01
    assert compute_refund("unavailable_order_paid", finding) == 100.01
    assert compute_refund("late_delivery_seller", finding) == 10.01
    assert compute_refund("late_delivery_logistics", finding) == 10.01
    assert compute_refund("valid_split_payment", finding) == 0.0


@pytest.mark.parametrize("bad_value", [-1, float("nan"), float("inf")])
def test_invalid_source_money_is_rejected(bad_value):
    facts = _facts([(bad_value, 0.0)], [0.0])
    with pytest.raises(ValueError):
        calculate_totals(facts.items, facts.payments)
