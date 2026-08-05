"""Order and seller handoff analysis for EC_POLICY_V1."""

from __future__ import annotations

from datetime import datetime

from src.contracts import CaseInput, OrderFacts, OrderSellerFinding
from src.evidence import item_evidence, order_evidence, seller_evidence


def _after(value: str | None, limit: str | None) -> bool:
    if not value or not limit:
        return False
    return datetime.fromisoformat(value) > datetime.fromisoformat(limit)


class OrderSellerAgent:
    @staticmethod
    def run(case: CaseInput, facts: OrderFacts) -> OrderSellerFinding:
        del case
        seller_ids = list(dict.fromkeys(item.seller_id for item in facts.items))
        item_ids = [f"{item.order_id}:{item.order_item_id}" for item in facts.items]
        handoff_late = {
            seller_id: any(
                item.seller_id == seller_id
                and _after(facts.delivered_carrier_ts, item.shipping_limit_ts)
                for item in facts.items
            )
            for seller_id in seller_ids
        }
        evidence = []
        if facts.found:
            evidence.append(order_evidence(facts.order_id))
        evidence.extend(item_evidence(item.order_id, item.order_item_id) for item in facts.items)
        evidence.extend(seller_evidence(seller_id) for seller_id in seller_ids)
        return OrderSellerFinding(
            order_status=facts.order_status,
            has_items=bool(facts.items),
            seller_ids=seller_ids,
            item_ids=item_ids,
            seller_handoff_late=handoff_late,
            evidence=evidence,
            notes="Seller handoff evaluated against each item shipping limit.",
        )