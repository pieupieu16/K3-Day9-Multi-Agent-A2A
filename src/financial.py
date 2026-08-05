"""Deterministic BRL calculations shared by Payment and Verifier agents."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable


MONEY_QUANTUM = Decimal("0.01")
RECONCILIATION_TOLERANCE = Decimal("0.10")
FULL_REFUND_ISSUES = {"canceled_order_paid", "unavailable_order_paid"}
FREIGHT_REFUND_ISSUES = {"late_delivery_seller", "late_delivery_logistics"}


def money(value: Any) -> Decimal:
    return Decimal(str(value or 0)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def sum_money(values: Iterable[Any]) -> Decimal:
    return money(sum((Decimal(str(value or 0)) for value in values), Decimal("0")))


def compute_refund(primary_issue: str, payment: Any) -> float:
    if isinstance(payment, dict):
        payment_total = payment.get("payment_total", 0)
        freight_total = payment.get("freight_total", 0)
    else:
        payment_total = getattr(payment, "payment_total", 0)
        freight_total = getattr(payment, "freight_total", 0)
    if primary_issue in FULL_REFUND_ISSUES:
        return float(money(payment_total))
    if primary_issue in FREIGHT_REFUND_ISSUES:
        return float(money(freight_total))
    return 0.0