"""Deterministic monetary calculations for the payment and verifier agents.

All additions happen with :class:`~decimal.Decimal`.  Values are quantized only
after the complete sum so binary floating-point error cannot change a cent.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Iterable


CENT = Decimal("0.01")
ZERO = Decimal("0")
FULL_REFUND_ISSUES = {"canceled_order_paid", "unavailable_order_paid"}
FREIGHT_REFUND_ISSUES = {"late_delivery_seller", "late_delivery_logistics"}


def _value(source: Any, name: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(name, default)
    return getattr(source, name, default)


def _decimal(value: Any) -> Decimal:
    """Convert a source value to a finite, non-negative Decimal.

    Missing values are treated as zero so an incomplete row can never leak
    ``None``/``NaN`` into an output.  Negative and non-finite source money is
    rejected because silently refunding it would conceal corrupt source data.
    """
    if value in (None, ""):
        return ZERO
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid monetary value: {value!r}") from exc
    if not result.is_finite() or result < ZERO:
        raise ValueError(f"Monetary value must be finite and non-negative: {value!r}")
    return result


def _money(value: Decimal) -> float:
    return float(value.quantize(CENT, rounding=ROUND_HALF_UP))


def _sum_field(rows: Iterable[Any], field: str) -> float:
    total = sum((_decimal(_value(row, field, 0)) for row in rows), ZERO)
    return _money(total)


def item_total(items: Iterable[Any]) -> float:
    """Return the sum of item prices, rounded once to two decimal places."""
    return _sum_field(items, "price")


def freight_total(items: Iterable[Any]) -> float:
    """Return the sum of item freight values, rounded once to two decimals."""
    return _sum_field(items, "freight_value")


def payment_total(payments: Iterable[Any]) -> float:
    """Return the sum of payment rows (not installments)."""
    return _sum_field(payments, "payment_value")


def calculate_totals(items: Iterable[Any], payments: Iterable[Any]) -> tuple[float, float, float]:
    """Return ``(item_total, freight_total, payment_total)`` in BRL."""
    item_rows = list(items or [])
    payment_rows = list(payments or [])
    return (
        item_total(item_rows),
        freight_total(item_rows),
        payment_total(payment_rows),
    )


def is_reconciled(payment: float, items: float, freight: float) -> bool:
    """Whether payment differs from item plus freight by at most BRL 0.10."""
    difference = abs(_decimal(payment) - (_decimal(items) + _decimal(freight)))
    return difference <= Decimal("0.10")


def compute_refund(primary_issue: str, finding: Any) -> float:
    """Compute the authoritative EC_POLICY_V1 refund from a payment finding."""
    if primary_issue in FULL_REFUND_ISSUES:
        amount = _decimal(_value(finding, "payment_total", 0))
    elif primary_issue in FREIGHT_REFUND_ISSUES:
        amount = _decimal(_value(finding, "freight_total", 0))
    else:
        amount = ZERO
    return _money(amount)
