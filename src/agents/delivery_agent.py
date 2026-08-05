"""Delivery timing analysis for EC_POLICY_V1."""

from __future__ import annotations

from datetime import datetime

from src.contracts import CaseInput, DeliveryFinding, OrderFacts, OrderSellerFinding
from src.evidence import order_evidence


def _after(value: str | None, limit: str | None) -> bool:
    if not value or not limit:
        return False
    return datetime.fromisoformat(value) > datetime.fromisoformat(limit)


class DeliveryAgent:
    @staticmethod
    def run(
        case: CaseInput,
        facts: OrderFacts,
        order_seller: OrderSellerFinding,
    ) -> DeliveryFinding:
        del case
        late_sellers = [
            seller_id
            for seller_id, is_late in order_seller.seller_handoff_late.items()
            if is_late
        ]
        return DeliveryFinding(
            delivered=facts.delivered_customer_ts is not None,
            delivered_after_estimate=_after(
                facts.delivered_customer_ts, facts.estimated_delivery_ts
            ),
            carrier_handoff_ts=facts.delivered_carrier_ts,
            estimated_ts=facts.estimated_delivery_ts,
            delivered_ts=facts.delivered_customer_ts,
            any_seller_handoff_late=bool(late_sellers),
            late_seller_ids=late_sellers,
            evidence=[order_evidence(facts.order_id)] if facts.found else [],
            notes="Customer delivery compared directly with the estimated date.",
        )