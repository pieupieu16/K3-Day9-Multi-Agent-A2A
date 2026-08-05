"""Pure financial rules for Role 3 under EC_POLICY_V1.

This module intentionally contains no CSV or agent orchestration code.  Keeping
the money rules pure makes them straightforward to test and reuse by the
Payment Agent and the final verifier.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


MONEY_QUANTUM = Decimal("0.01")
RECONCILIATION_TOLERANCE = Decimal("0.10")

FULL_REFUND_ISSUES = frozenset({"canceled_order_paid", "unavailable_order_paid"})
FREIGHT_REFUND_ISSUES = frozenset(
    {"late_delivery_seller", "late_delivery_logistics"}
)
NO_REFUND_ISSUES = frozenset({"valid_split_payment", "unsupported_late_claim"})
KNOWN_ISSUES = FULL_REFUND_ISSUES | FREIGHT_REFUND_ISSUES | NO_REFUND_ISSUES


def money(value: object) -> Decimal:
    """Convert a CSV/number value to BRL rounded with commercial rounding."""

    return Decimal(str(value)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class FinancialTotals:
    item_total: Decimal
    freight_total: Decimal
    payment_total: Decimal

    @property
    def expected_total(self) -> Decimal:
        return money(self.item_total + self.freight_total)

    @property
    def difference(self) -> Decimal:
        return money(self.payment_total - self.expected_total)

    @property
    def is_reconciled(self) -> bool:
        return abs(self.difference) <= RECONCILIATION_TOLERANCE


def recommended_refund(
    primary_issue: Optional[str], totals: FinancialTotals
) -> Decimal:
    """Return the refund dictated by EC_POLICY_V1.

    ``None`` is allowed while the Coordinator has not selected an issue yet;
    in that situation no refund is guessed. Unknown non-null issues are likely
    an integration bug and therefore raise an explicit error.
    """

    if primary_issue is None:
        return money(0)
    if primary_issue not in KNOWN_ISSUES:
        raise ValueError(f"Unknown EC_POLICY_V1 primary issue: {primary_issue!r}")
    if primary_issue in FULL_REFUND_ISSUES:
        return totals.payment_total if totals.payment_total > 0 else money(0)
    if primary_issue in FREIGHT_REFUND_ISSUES:
        return totals.freight_total
    return money(0)
