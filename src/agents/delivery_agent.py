"""Delivery specialist using verified timestamps and optional LLM commentary."""

from __future__ import annotations

import json

from src.contracts import CaseInput, DeliveryFinding, OrderFacts, OrderSellerFinding
from src.evidence import order_evidence
from src.llm_client import MODEL_NAME, call_llm


SYSTEM_PROMPT = """You are DeliveryAgent using a model below 10B parameters.
Review only the supplied delivery timestamps and seller handoff summary. Return
JSON with a concise `notes` explanation. Do not alter deterministic booleans or
invent shipment events."""


def _llm_notes(
    facts: OrderFacts, delivered_after_estimate: bool, late_seller_ids: list[str]
) -> str:
    payload = {
        "agent": "delivery",
        "delivered_carrier_ts": facts.delivered_carrier_ts,
        "delivered_customer_ts": facts.delivered_customer_ts,
        "estimated_delivery_ts": facts.estimated_delivery_ts,
        "delivered_after_estimate": delivered_after_estimate,
        "late_seller_ids": late_seller_ids,
    }
    try:
        response = call_llm(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            system_prompt=SYSTEM_PROMPT,
            json_mode=True,
        )
        note = response.get("notes") if isinstance(response, dict) else None
        if isinstance(note, str) and note.strip():
            return note.strip()
    except Exception:
        pass
    return f"Deterministic delivery inspection; explanation model={MODEL_NAME}"


def analyze_delivery(
    case: CaseInput, facts: OrderFacts, order_seller: OrderSellerFinding
) -> DeliveryFinding:
    """Classify lateness from CSV timestamps without timezone conversion."""
    del case
    delivered = facts.delivered_customer_ts is not None
    delivered_after_estimate = bool(
        delivered
        and facts.estimated_delivery_ts
        and facts.delivered_customer_ts > facts.estimated_delivery_ts
    )
    late_seller_ids = [
        seller_id for seller_id, is_late in order_seller.seller_handoff_late.items()
        if is_late
    ][:5]
    evidence = [order_evidence(facts.order_id)] if facts.found and facts.order_id else []
    return DeliveryFinding(
        delivered=delivered,
        delivered_after_estimate=delivered_after_estimate,
        carrier_handoff_ts=facts.delivered_carrier_ts,
        estimated_ts=facts.estimated_delivery_ts,
        delivered_ts=facts.delivered_customer_ts,
        any_seller_handoff_late=bool(late_seller_ids),
        late_seller_ids=late_seller_ids,
        evidence=evidence,
        notes=_llm_notes(facts, delivered_after_estimate, late_seller_ids),
    )


class DeliveryAgent:
    """Coordinator-compatible facade."""

    @staticmethod
    def run(
        case: CaseInput, facts: OrderFacts, order_seller: OrderSellerFinding
    ) -> DeliveryFinding:
        return analyze_delivery(case, facts, order_seller)


run = analyze_delivery