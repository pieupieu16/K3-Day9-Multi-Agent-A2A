"""Deterministic EC_POLICY_V1 decision logic.

The coordinator may pass contract dataclasses or JSON-like mock dictionaries while
the rest of the pipeline is being integrated.
"""

from dataclasses import dataclass
from importlib import import_module
from typing import Any


@dataclass
class _FallbackPolicyDecision:
    primary_issue: str
    case_status: str
    confidence: float
    ranked_causes: list[dict[str, Any]]
    responsible_parties: list[dict[str, str]]
    recommended_refund_brl: float
    resolution_actions: list[str]
    evidence: list[str]


def _value(source: Any, name: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(name, default)
    return getattr(source, name, default)


def _decision(**values: Any) -> Any:
    try:
        policy_decision = getattr(import_module("src.contracts"), "PolicyDecision")
    except ImportError:
        return _FallbackPolicyDecision(**values)
    return policy_decision(**values)


def decide_policy(
    order_seller: Any,
    delivery: Any,
    payment: Any,
) -> Any:
    """Apply EC_POLICY_V1 in its mandated priority order."""
    order_status = _value(order_seller, "order_status")
    payment_total = round(float(_value(payment, "payment_total", 0.0) or 0.0), 2)
    freight_total = round(float(_value(payment, "freight_total", 0.0) or 0.0), 2)
    delivered_late = bool(_value(delivery, "delivered_after_estimate", False))
    seller_late = bool(_value(delivery, "any_seller_handoff_late", False))
    late_sellers = list(_value(delivery, "late_seller_ids", []) or [])
    is_split = bool(_value(payment, "is_split_payment", False))
    reconciled = bool(_value(payment, "reconciled_within_010", False))

    if order_status == "canceled" and payment_total > 0:
        return _result(
            "canceled_order_paid", "ORDER_CANCELED_AFTER_PAYMENT", 0.95,
            [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}],
            payment_total, "issue_full_refund",
        )
    if order_status == "unavailable" and payment_total > 0:
        return _result(
            "unavailable_order_paid", "ORDER_UNAVAILABLE_AFTER_PAYMENT", 0.95,
            [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}],
            payment_total, "issue_full_refund",
        )
    if delivered_late and seller_late:
        seller_id = late_sellers[0] if late_sellers else "UNKNOWN_SELLER"
        return _result(
            "late_delivery_seller", "SELLER_HANDOFF_AFTER_LIMIT", 0.90,
            [{"party_type": "seller", "party_id": seller_id}],
            freight_total, "refund_freight",
        )
    if delivered_late:
        return _result(
            "late_delivery_logistics", "CARRIER_DELIVERED_AFTER_ESTIMATE", 0.90,
            [{"party_type": "logistics_provider", "party_id": "LOGISTICS_PROVIDER"}],
            freight_total, "refund_freight",
        )
    if is_split and reconciled:
        return _result(
            "valid_split_payment", "MULTIPLE_PAYMENTS_RECONCILED", 0.88,
            [], 0.0, "explain_valid_split_payment",
        )
    return _result(
        "unsupported_late_claim", "DELIVERY_WITHIN_ESTIMATE", 0.85,
        [], 0.0, "reject_late_refund",
    )


def _result(
    primary_issue: str,
    cause_code: str,
    confidence: float,
    responsible_parties: list[dict[str, str]],
    refund: float,
    action: str,
) -> Any:
    return _decision(
        primary_issue=primary_issue,
        case_status="action_required" if refund > 0 else "no_action",
        confidence=confidence,
        ranked_causes=[{"cause_code": cause_code, "rank": 1}],
        responsible_parties=responsible_parties,
        recommended_refund_brl=round(refund, 2),
        resolution_actions=[action],
        evidence=[f"policy:{cause_code}"],
    )


run = decide_policy