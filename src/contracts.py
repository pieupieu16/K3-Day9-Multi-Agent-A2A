"""
src/contracts.py — Contract đóng băng cho hệ thống Multi-Agent Dispute Resolution.
Dân lập trình các module (Data Layer, Agents, Coordinator) tuân theo các dataclass này.
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any


@dataclass
class CaseInput:
    case_id: str
    opened_at: str
    language: str
    message: str
    claimed_order_id: str
    policy_version: str

    @classmethod
    def from_dict(cls, data: dict) -> "CaseInput":
        req = data.get("customer_request", {})
        return cls(
            case_id=data.get("case_id", ""),
            opened_at=data.get("opened_at", ""),
            language=req.get("language", "vi"),
            message=req.get("message", ""),
            claimed_order_id=req.get("claimed_order_id", ""),
            policy_version=data.get("policy_version", "EC_POLICY_V1"),
        )


@dataclass
class ItemFact:
    order_id: str
    order_item_id: int
    product_id: str
    seller_id: str
    shipping_limit_ts: Optional[str]
    price: float
    freight_value: float


@dataclass
class PaymentFact:
    order_id: str
    payment_sequential: int
    payment_type: str
    installments: int
    payment_value: float


@dataclass
class OrderFacts:
    """Trả về từ Data Layer (Dương) - Nguồn sự thật duy nhất về Order"""

    found: bool
    order_id: str
    customer_id: Optional[str] = None
    order_status: Optional[str] = None
    purchase_ts: Optional[str] = None
    approved_ts: Optional[str] = None
    delivered_carrier_ts: Optional[str] = None
    delivered_customer_ts: Optional[str] = None
    estimated_delivery_ts: Optional[str] = None
    items: List[ItemFact] = field(default_factory=list)
    payments: List[PaymentFact] = field(default_factory=list)


@dataclass
class OrderSellerFinding:
    """Kết quả từ Order & Seller Agent (Phương)"""

    order_status: Optional[str]
    has_items: bool
    seller_ids: List[str]
    item_ids: List[str]  # dạng "order_id:order_item_id"
    seller_handoff_late: Dict[str, bool]  # seller_id -> trễ hạn?
    evidence: List[str]
    notes: str = ""


@dataclass
class DeliveryFinding:
    """Kết quả từ Delivery Agent (Phương)"""

    delivered: bool
    delivered_after_estimate: bool
    carrier_handoff_ts: Optional[str]
    estimated_ts: Optional[str]
    delivered_ts: Optional[str]
    any_seller_handoff_late: bool
    late_seller_ids: List[str]
    evidence: List[str]
    notes: str = ""


@dataclass
class PaymentFinding:
    """Kết quả từ Payment Agent (Long)"""

    n_payment_rows: int
    payment_total: float
    item_total: float
    freight_total: float
    reconciled_within_010: bool
    is_split_payment: bool
    payment_ids: List[str]  # dạng "order_id:payment_sequential"
    evidence: List[str]
    notes: str = ""


@dataclass
class PolicyDecision:
    """Kết quả từ Policy Agent (Tùng)"""

    primary_issue: str
    case_status: str
    confidence: float
    ranked_causes: List[dict]
    responsible_parties: List[dict]
    recommended_refund_brl: float
    resolution_actions: List[str]
    evidence: List[str]


@dataclass
class CaseOutput:
    """Cấu trúc JSON Output cuối cùng nộp bài (đúng schema mục 6 README)"""

    case_id: str
    assessment: dict
    affected_entities: dict
    root_cause_analysis: dict
    evidence_ids: List[str]
    financial_resolution: dict
    resolution_actions: List[str]

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "assessment": self.assessment,
            "affected_entities": self.affected_entities,
            "root_cause_analysis": self.root_cause_analysis,
            "evidence_ids": self.evidence_ids,
            "financial_resolution": self.financial_resolution,
            "resolution_actions": self.resolution_actions,
        }
