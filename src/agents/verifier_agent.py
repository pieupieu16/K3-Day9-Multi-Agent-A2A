"""Final quality gate and CaseOutput serializer for EC_POLICY_V1."""

from __future__ import annotations

import re
from typing import Any


EVIDENCE_PATTERNS = (
    re.compile(r"^order:[^:]+$"),
    re.compile(r"^item:[^:]+:[1-9][0-9]*$"),
    re.compile(r"^payment:[^:]+:[1-9][0-9]*$"),
    re.compile(r"^seller:[^:]+$"),
    re.compile(r"^policy:(SELLER_HANDOFF_AFTER_LIMIT|CARRIER_DELIVERED_AFTER_ESTIMATE|ORDER_CANCELED_AFTER_PAYMENT|ORDER_UNAVAILABLE_AFTER_PAYMENT|MULTIPLE_PAYMENTS_RECONCILED|DELIVERY_WITHIN_ESTIMATE)$"),
)


def _value(source: Any, name: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(name, default)
    return getattr(source, name, default)


def _money(value: Any) -> float:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return 0.0


def _is_valid_evidence(evidence_id: str, facts: Any) -> bool:
    try:
        from src.evidence import evidence_exists
    except ImportError:
        return any(pattern.fullmatch(evidence_id) for pattern in EVIDENCE_PATTERNS)
    return evidence_exists(evidence_id, facts)


def _refund(primary_issue: str, payment: Any) -> float:
    try:
        from src.financial import compute_refund
    except ImportError:
        if primary_issue in {"canceled_order_paid", "unavailable_order_paid"}:
            return _money(_value(payment, "payment_total", 0.0))
        if primary_issue.startswith("late_delivery_"):
            return _money(_value(payment, "freight_total", 0.0))
        return 0.0
    return _money(compute_refund(primary_issue, payment))


def verify_and_serialize(
    case: Any,
    facts: Any,
    order_seller: Any,
    payment: Any,
    delivery_or_decision: Any,
    decision: Any | None = None,
) -> dict[str, Any]:
    """Return a bounded, schema-complete output dictionary ready for JSON encoding."""
    if decision is None:
        decision = delivery_or_decision
        delivery = None
    else:
        delivery = delivery_or_decision
    order_id = _value(facts, "order_id", _value(case, "claimed_order_id", "")) or ""
    items = list(_value(facts, "items", []) or [])
    item_ids = list(_value(order_seller, "item_ids", []) or [])[:5]
    seller_ids = list(_value(order_seller, "seller_ids", []) or [])[:5]
    payment_ids = list(_value(payment, "payment_ids", []) or [])[:5]
    primary_issue = _value(decision, "primary_issue", "unsupported_late_claim")
    evidence = list(_value(order_seller, "evidence", []) or [])
    evidence += list(_value(delivery, "evidence", []) or [])
    evidence += list(_value(payment, "evidence", []) or [])
    evidence += list(_value(decision, "evidence", []) or [])
    evidence = [entry for entry in dict.fromkeys(evidence) if _is_valid_evidence(entry, facts)][:10]

    if order_id and f"order:{order_id}" not in evidence:
        evidence.insert(0, f"order:{order_id}")
    evidence = [entry for entry in evidence if _is_valid_evidence(entry, facts)][:10]
    item_total = _money(_value(payment, "item_total", sum(float(_value(item, "price", 0.0) or 0.0) for item in items)))
    freight_total = _money(_value(payment, "freight_total", sum(float(_value(item, "freight_value", 0.0) or 0.0) for item in items)))
    payment_total = _money(_value(payment, "payment_total", 0.0))
    confidence = min(1.0, max(0.0, float(_value(decision, "confidence", 0.0) or 0.0)))
    refund = _refund(primary_issue, payment)

    return {
        "case_id": _value(case, "case_id", ""),
        "assessment": {
            "primary_issue": primary_issue,
            "case_status": "action_required" if refund > 0 else "no_action",
            "confidence": confidence,
        },
        "affected_entities": {
            "order_ids": [order_id] if order_id else [],
            "item_ids": item_ids,
            "seller_ids": seller_ids,
            "payment_ids": payment_ids,
        },
        "root_cause_analysis": {
            "ranked_causes": list(_value(decision, "ranked_causes", []) or [])[:3],
            "responsible_parties": list(_value(decision, "responsible_parties", []) or [])[:3],
        },
        "evidence_ids": evidence,
        "financial_resolution": {
            "currency": "BRL",
            "item_total_brl": item_total,
            "freight_total_brl": freight_total,
            "payment_total_brl": payment_total,
            "recommended_refund_brl": refund,
        },
        "resolution_actions": list(_value(decision, "resolution_actions", []) or [])[:5],
    }


run = verify_and_serialize