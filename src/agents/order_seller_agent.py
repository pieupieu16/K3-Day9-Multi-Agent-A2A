"""Order and seller specialist using verified facts and optional LLM commentary."""

from __future__ import annotations

import json

from src.contracts import CaseInput, OrderFacts, OrderSellerFinding
from src.evidence import item_evidence, order_evidence, seller_evidence
from src.llm_client import MODEL_NAME, call_llm


SYSTEM_PROMPT = """You are OrderSellerAgent using a model below 10B parameters.
Review only the supplied order, item and seller facts. Return JSON with a concise
`notes` explanation. Do not create IDs, change deterministic booleans, or infer
payment or delivery-customer facts."""


def _llm_notes(facts: OrderFacts, seller_handoff_late: dict[str, bool]) -> str:
    payload = {
        "agent": "order_seller",
        "order_id": facts.order_id,
        "order_status": facts.order_status,
        "delivered_carrier_ts": facts.delivered_carrier_ts,
        "items": [
            {
                "order_item_id": item.order_item_id,
                "seller_id": item.seller_id,
                "shipping_limit_ts": item.shipping_limit_ts,
            }
            for item in facts.items
        ],
        "seller_handoff_late": seller_handoff_late,
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
    return f"Deterministic order/seller inspection; explanation model={MODEL_NAME}"


def analyze_order_seller(case: CaseInput, facts: OrderFacts) -> OrderSellerFinding:
    """Derive seller handoff responsibility directly from frozen order facts."""
    del case
    seller_ids = list(dict.fromkeys(item.seller_id for item in facts.items if item.seller_id))[:5]
    item_ids = [f"{item.order_id}:{item.order_item_id}" for item in facts.items][:5]
    seller_handoff_late: dict[str, bool] = {}
    for seller_id in seller_ids:
        seller_items = [item for item in facts.items if item.seller_id == seller_id]
        seller_handoff_late[seller_id] = any(
            bool(
                facts.delivered_carrier_ts
                and item.shipping_limit_ts
                and facts.delivered_carrier_ts > item.shipping_limit_ts
            )
            for item in seller_items
        )

    evidence = [order_evidence(facts.order_id)] if facts.found and facts.order_id else []
    evidence.extend(item_evidence(item.order_id, item.order_item_id) for item in facts.items[:5])
    evidence.extend(seller_evidence(seller_id) for seller_id in seller_ids)
    return OrderSellerFinding(
        order_status=facts.order_status,
        has_items=bool(facts.items),
        seller_ids=seller_ids,
        item_ids=item_ids,
        seller_handoff_late=seller_handoff_late,
        evidence=evidence[:10],
        notes=_llm_notes(facts, seller_handoff_late),
    )


class OrderSellerAgent:
    """Coordinator-compatible facade."""

    @staticmethod
    def run(case: CaseInput, facts: OrderFacts) -> OrderSellerFinding:
        return analyze_order_seller(case, facts)


run = analyze_order_seller