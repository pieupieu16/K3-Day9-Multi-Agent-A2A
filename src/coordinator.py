"""
src/coordinator.py — Coordinator Agent (Thành viên 1 - Team Lead / Coordinator Architect)
Điều phối luồng công việc giữa 5 Agents (Order/Seller, Delivery, Payment, Policy, Verifier).
Sử dụng Handoff Pattern và hỗ trợ Stub Fallback thông minh để không bao giờ bị block.
"""
import time
import logging
from typing import Dict, Any, Tuple
from src.contracts import (
    CaseInput,
    OrderFacts,
    ItemFact,
    PaymentFact,
    OrderSellerFinding,
    DeliveryFinding,
    PaymentFinding,
    PolicyDecision,
    CaseOutput,
)
from src.tracing import trace_event

logger = logging.getLogger(__name__)

# Dynamically import domain modules if available, otherwise fall back to internal stubs
try:
    from src.data_layer import load_order
except ImportError:
    load_order = None

try:
    from src.agents.order_seller_agent import OrderSellerAgent
except ImportError:
    OrderSellerAgent = None

try:
    from src.agents.delivery_agent import DeliveryAgent
except ImportError:
    DeliveryAgent = None

try:
    from src.agents.payment_agent import PaymentAgent
except ImportError:
    PaymentAgent = None

try:
    from src.agents.policy_agent import PolicyAgent
except ImportError:
    PolicyAgent = None

try:
    from src.agents.verifier_agent import VerifierAgent
except ImportError:
    VerifierAgent = None


class Coordinator:
    """
    Coordinator Agent điều phối toàn bộ quy trình xử lý case khiếu nại.
    """

    def __init__(self):
        pass

    def _stub_load_order(self, order_id: str) -> OrderFacts:
        """Data layer stub fallback khi Dương chưa push code thật."""
        if not order_id:
            return OrderFacts(found=False, order_id="")
        return OrderFacts(
            found=True,
            order_id=order_id,
            customer_id=f"cust_{order_id[:8]}",
            order_status="delivered",
            purchase_ts="2018-01-01T10:00:00",
            approved_ts="2018-01-01T10:15:00",
            delivered_carrier_ts="2018-01-02T14:00:00",
            delivered_customer_ts="2018-01-08T16:00:00",
            estimated_delivery_ts="2018-01-12T00:00:00",
            items=[
                ItemFact(
                    order_id=order_id,
                    order_item_id=1,
                    product_id="prod_01",
                    seller_id="seller_01",
                    shipping_limit_ts="2018-01-05T00:00:00",
                    price=80.0,
                    freight_value=15.0,
                )
            ],
            payments=[
                PaymentFact(
                    order_id=order_id,
                    payment_sequential=1,
                    payment_type="credit_card",
                    installments=1,
                    payment_value=95.0,
                )
            ],
        )

    def _run_order_seller_step(
        self, case: CaseInput, facts: OrderFacts
    ) -> Tuple[OrderSellerFinding, float]:
        t0 = time.time()
        if OrderSellerAgent and hasattr(OrderSellerAgent, "run"):
            finding = OrderSellerAgent.run(case, facts)
        else:
            # Stub Order & Seller Agent (Phương)
            seller_ids = list(dict.fromkeys([item.seller_id for item in facts.items]))
            item_ids = [f"{item.order_id}:{item.order_item_id}" for item in facts.items]
            evidence = [f"order:{facts.order_id}"] + [f"seller:{s}" for s in seller_ids]
            finding = OrderSellerFinding(
                order_status=facts.order_status,
                has_items=len(facts.items) > 0,
                seller_ids=seller_ids,
                item_ids=item_ids,
                seller_handoff_late={s: False for s in seller_ids},
                evidence=evidence,
                notes="Stub OrderSeller Agent evaluation",
            )
        elapsed = (time.time() - t0) * 1000
        return finding, elapsed

    def _run_payment_step(
        self, case: CaseInput, facts: OrderFacts
    ) -> Tuple[PaymentFinding, float]:
        t0 = time.time()
        if PaymentAgent and hasattr(PaymentAgent, "run"):
            finding = PaymentAgent.run(case, facts)
        else:
            # Stub Payment Agent (Long)
            item_total = round(sum(i.price for i in facts.items), 2)
            freight_total = round(sum(i.freight_value for i in facts.items), 2)
            payment_total = round(sum(p.payment_value for p in facts.payments), 2)
            p_ids = [f"{facts.order_id}:{p.payment_sequential}" for p in facts.payments]
            evidence = [f"payment:{p_id}" for p_id in p_ids]
            
            reconciled = abs(payment_total - (item_total + freight_total)) <= 0.10
            is_split = len(facts.payments) >= 2
            
            finding = PaymentFinding(
                n_payment_rows=len(facts.payments),
                payment_total=payment_total,
                item_total=item_total,
                freight_total=freight_total,
                reconciled_within_010=reconciled,
                is_split_payment=is_split,
                payment_ids=p_ids,
                evidence=evidence,
                notes="Stub Payment Agent evaluation",
            )
        elapsed = (time.time() - t0) * 1000
        return finding, elapsed

    def _run_delivery_step(
        self, case: CaseInput, facts: OrderFacts, order_seller_finding: OrderSellerFinding
    ) -> Tuple[DeliveryFinding, float]:
        t0 = time.time()
        if DeliveryAgent and hasattr(DeliveryAgent, "run"):
            finding = DeliveryAgent.run(case, facts, order_seller_finding)
        else:
            # Stub Delivery Agent (Phương)
            delivered = facts.delivered_customer_ts is not None
            delivered_after_est = False
            if delivered and facts.estimated_delivery_ts:
                delivered_after_est = facts.delivered_customer_ts > facts.estimated_delivery_ts
            
            any_late = any(order_seller_finding.seller_handoff_late.values())
            late_sellers = [s for s, is_late in order_seller_finding.seller_handoff_late.items() if is_late]
            
            evidence = [f"order:{facts.order_id}"]
            finding = DeliveryFinding(
                delivered=delivered,
                delivered_after_estimate=delivered_after_est,
                carrier_handoff_ts=facts.delivered_carrier_ts,
                estimated_ts=facts.estimated_delivery_ts,
                delivered_ts=facts.delivered_customer_ts,
                any_seller_handoff_late=any_late,
                late_seller_ids=late_sellers,
                evidence=evidence,
                notes="Stub Delivery Agent evaluation",
            )
        elapsed = (time.time() - t0) * 1000
        return finding, elapsed

    def _run_policy_step(
        self,
        case: CaseInput,
        order_seller_finding: OrderSellerFinding,
        delivery_finding: DeliveryFinding,
        payment_finding: PaymentFinding,
    ) -> Tuple[PolicyDecision, float]:
        t0 = time.time()
        if PolicyAgent and hasattr(PolicyAgent, "run"):
            decision = PolicyAgent.run(
                case, order_seller_finding, delivery_finding, payment_finding
            )
        else:
            # Stub / Deterministic Baseline Policy Agent (Tùng - 1 to 6 rules in PHAN_CONG §4)
            status = order_seller_finding.order_status
            pay_total = payment_finding.payment_total
            freight_total = payment_finding.freight_total

            if status == "canceled" and pay_total > 0:
                issue = "canceled_order_paid"
                c_status = "action_required"
                resp = [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}]
                refund = pay_total
                action = ["issue_full_refund"]
                cause = "ORDER_CANCELED_AFTER_PAYMENT"
            elif status == "unavailable" and pay_total > 0:
                issue = "unavailable_order_paid"
                c_status = "action_required"
                resp = [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}]
                refund = pay_total
                action = ["issue_full_refund"]
                cause = "ORDER_UNAVAILABLE_AFTER_PAYMENT"
            elif delivery_finding.delivered_after_estimate and delivery_finding.any_seller_handoff_late:
                issue = "late_delivery_seller"
                c_status = "action_required"
                seller_id = delivery_finding.late_seller_ids[0] if delivery_finding.late_seller_ids else "UNKNOWN_SELLER"
                resp = [{"party_type": "seller", "party_id": seller_id}]
                refund = freight_total
                action = ["refund_freight"]
                cause = "SELLER_HANDOFF_AFTER_LIMIT"
            elif delivery_finding.delivered_after_estimate and not delivery_finding.any_seller_handoff_late:
                issue = "late_delivery_logistics"
                c_status = "action_required"
                resp = [{"party_type": "logistics_provider", "party_id": "LOGISTICS_PROVIDER"}]
                refund = freight_total
                action = ["refund_freight"]
                cause = "CARRIER_DELIVERED_AFTER_ESTIMATE"
            elif payment_finding.is_split_payment and payment_finding.reconciled_within_010:
                issue = "valid_split_payment"
                c_status = "no_action"
                resp = []
                refund = 0.0
                action = ["explain_valid_split_payment"]
                cause = "MULTIPLE_PAYMENTS_RECONCILED"
            else:
                issue = "unsupported_late_claim"
                c_status = "no_action"
                resp = []
                refund = 0.0
                action = ["reject_late_refund"]
                cause = "DELIVERY_WITHIN_ESTIMATE"

            evidence = list(
                dict.fromkeys(
                    order_seller_finding.evidence
                    + delivery_finding.evidence
                    + payment_finding.evidence
                    + [f"policy:{cause}"]
                )
            )[:10]

            decision = PolicyDecision(
                primary_issue=issue,
                case_status=c_status,
                confidence=0.90,
                ranked_causes=[{"cause_code": cause, "rank": 1}],
                responsible_parties=resp,
                recommended_refund_brl=round(refund, 2),
                resolution_actions=action,
                evidence=evidence,
            )

        elapsed = (time.time() - t0) * 1000
        return decision, elapsed

    def _run_verifier_step(
        self,
        case: CaseInput,
        facts: OrderFacts,
        order_seller_finding: OrderSellerFinding,
        delivery_finding: DeliveryFinding,
        payment_finding: PaymentFinding,
        policy_decision: PolicyDecision,
    ) -> Tuple[CaseOutput, float]:
        t0 = time.time()
        if VerifierAgent and hasattr(VerifierAgent, "run"):
            output = VerifierAgent.run(
                case,
                facts,
                order_seller_finding,
                delivery_finding,
                payment_finding,
                policy_decision,
            )
        else:
            # Stub Verifier Agent (Tùng - Verification & Schema enforcement)
            evidence_ids = list(dict.fromkeys(policy_decision.evidence))[:10]
            
            output = CaseOutput(
                case_id=case.case_id,
                assessment={
                    "primary_issue": policy_decision.primary_issue,
                    "case_status": policy_decision.case_status,
                    "confidence": policy_decision.confidence,
                },
                affected_entities={
                    "order_ids": [case.claimed_order_id] if case.claimed_order_id else [],
                    "item_ids": order_seller_finding.item_ids[:5],
                    "seller_ids": order_seller_finding.seller_ids[:5],
                    "payment_ids": payment_finding.payment_ids[:5],
                },
                root_cause_analysis={
                    "ranked_causes": policy_decision.ranked_causes[:3],
                    "responsible_parties": policy_decision.responsible_parties[:3],
                },
                evidence_ids=evidence_ids,
                financial_resolution={
                    "currency": "BRL",
                    "item_total_brl": round(payment_finding.item_total, 2),
                    "freight_total_brl": round(payment_finding.freight_total, 2),
                    "payment_total_brl": round(payment_finding.payment_total, 2),
                    "recommended_refund_brl": round(policy_decision.recommended_refund_brl, 2),
                },
                resolution_actions=policy_decision.resolution_actions[:5],
            )
        elapsed = (time.time() - t0) * 1000
        return output, elapsed

    def process_case(self, case: CaseInput) -> CaseOutput:
        """
        Luồng chính điều phối case từ Input -> Domain agents -> Policy -> Verifier -> Output.
        """
        start_time = time.time()
        
        # 1. Load Data
        if load_order:
            facts = load_order(case.claimed_order_id)
        else:
            facts = self._stub_load_order(case.claimed_order_id)

        # Trace Data Load
        trace_event(
            case_id=case.case_id,
            agent="CoordinatorAgent",
            task_type="data_dispatch",
            payload={"claimed_order_id": case.claimed_order_id},
            status="completed",
            output={"found": facts.found, "n_items": len(facts.items)},
            latency_ms=(time.time() - start_time) * 1000,
        )

        # 2. Fan-out Domain Agents (Order/Seller & Payment)
        order_seller_finding, t_os = self._run_order_seller_step(case, facts)
        trace_event(
            case_id=case.case_id,
            agent="OrderSellerAgent",
            task_type="inspect_order_seller",
            payload={"order_id": facts.order_id},
            status="completed",
            output=order_seller_finding.__dict__,
            latency_ms=t_os,
        )

        payment_finding, t_pay = self._run_payment_step(case, facts)
        trace_event(
            case_id=case.case_id,
            agent="PaymentAgent",
            task_type="reconcile_payment",
            payload={"order_id": facts.order_id},
            status="completed",
            output=payment_finding.__dict__,
            latency_ms=t_pay,
        )

        # 3. Delivery Agent (nhận handoff từ Order/Seller)
        delivery_finding, t_del = self._run_delivery_step(case, facts, order_seller_finding)
        trace_event(
            case_id=case.case_id,
            agent="DeliveryAgent",
            task_type="assess_delivery",
            payload={"order_id": facts.order_id},
            status="completed",
            output=delivery_finding.__dict__,
            latency_ms=t_del,
        )

        # 4. Policy Agent (áp dụng rules từ tất cả domain findings)
        policy_decision, t_pol = self._run_policy_step(
            case, order_seller_finding, delivery_finding, payment_finding
        )
        trace_event(
            case_id=case.case_id,
            agent="PolicyAgent",
            task_type="apply_policy",
            payload={"policy_version": case.policy_version},
            status="completed",
            output=policy_decision.__dict__,
            latency_ms=t_pol,
        )

        # 5. Verifier Agent (Xác minh & chuẩn hóa schema)
        output, t_ver = self._run_verifier_step(
            case, facts, order_seller_finding, delivery_finding, payment_finding, policy_decision
        )
        trace_event(
            case_id=case.case_id,
            agent="VerifierAgent",
            task_type="verify_output",
            payload={"case_id": case.case_id},
            status="completed",
            output=output.to_dict(),
            latency_ms=t_ver,
        )

        return output
