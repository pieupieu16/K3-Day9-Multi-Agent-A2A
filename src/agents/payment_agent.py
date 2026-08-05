"""Payment reconciliation adapter for the frozen coordinator contract."""

from __future__ import annotations

from src.contracts import CaseInput, OrderFacts, PaymentFinding
from src.evidence import payment_evidence
from src.financial import RECONCILIATION_TOLERANCE, sum_money


class PaymentAgent:
    @staticmethod
    def run(case: CaseInput, facts: OrderFacts) -> PaymentFinding:
        del case
        item_total = sum_money(item.price for item in facts.items)
        freight_total = sum_money(item.freight_value for item in facts.items)
        payment_total = sum_money(payment.payment_value for payment in facts.payments)
        difference = abs(payment_total - (item_total + freight_total))
        payment_ids = [
            f"{payment.order_id}:{payment.payment_sequential}"
            for payment in facts.payments
        ]
        return PaymentFinding(
            n_payment_rows=len(facts.payments),
            payment_total=float(payment_total),
            item_total=float(item_total),
            freight_total=float(freight_total),
            reconciled_within_010=difference <= RECONCILIATION_TOLERANCE,
            is_split_payment=len(facts.payments) >= 2,
            payment_ids=payment_ids,
            evidence=[
                payment_evidence(payment.order_id, payment.payment_sequential)
                for payment in facts.payments
            ],
            notes=f"Payment difference is {difference} BRL.",
        )