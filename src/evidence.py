"""Evidence ID construction and verification against an ``OrderFacts`` record."""

from __future__ import annotations

from typing import Any

ROOT_CAUSES = {
    "SELLER_HANDOFF_AFTER_LIMIT",
    "CARRIER_DELIVERED_AFTER_ESTIMATE",
    "ORDER_CANCELED_AFTER_PAYMENT",
    "ORDER_UNAVAILABLE_AFTER_PAYMENT",
    "MULTIPLE_PAYMENTS_RECONCILED",
    "DELIVERY_WITHIN_ESTIMATE",
}


def order_evidence(order_id: str) -> str:
    return f"order:{order_id}"


def item_evidence(order_id: str, order_item_id: int) -> str:
    return f"item:{order_id}:{int(order_item_id)}"


def payment_evidence(order_id: str, payment_sequential: int) -> str:
    return f"payment:{order_id}:{int(payment_sequential)}"


def seller_evidence(seller_id: str) -> str:
    return f"seller:{seller_id}"


def policy_evidence(root_cause: str) -> str:
    return f"policy:{root_cause}"


def _value(source: Any, name: str, default: Any = None) -> Any:
    return source.get(name, default) if isinstance(source, dict) else getattr(source, name, default)


def evidence_exists(evidence_id: str, facts: Any) -> bool:
    """Return true only for a correctly formatted evidence ID supported by facts."""
    if not isinstance(evidence_id, str) or not evidence_id:
        return False
    parts = evidence_id.split(":")
    order_id = str(_value(facts, "order_id", "") or "")

    if parts[0] == "order" and len(parts) == 2:
        return bool(_value(facts, "found", False)) and parts[1] == order_id
    if parts[0] == "item" and len(parts) == 3 and parts[1] == order_id:
        return any(str(_value(item, "order_item_id")) == parts[2] for item in _value(facts, "items", []))
    if parts[0] == "payment" and len(parts) == 3 and parts[1] == order_id:
        return any(str(_value(payment, "payment_sequential")) == parts[2] for payment in _value(facts, "payments", []))
    if parts[0] == "seller" and len(parts) == 2:
        return any(str(_value(item, "seller_id", "")) == parts[1] for item in _value(facts, "items", []))
    if parts[0] == "policy" and len(parts) == 2:
        return parts[1] in ROOT_CAUSES
    return False


# Explicit aliases used by callers that prefer the "make_*" naming convention.
make_order_evidence = order_evidence
make_item_evidence = item_evidence
make_payment_evidence = payment_evidence
make_seller_evidence = seller_evidence
make_policy_evidence = policy_evidence
