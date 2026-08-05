"""
src/coordinator.py — Coordinator Agent (Thành viên 1 - Team Lead / Coordinator Architect)
Điều phối luồng công việc giữa 5 Agents (Order/Seller, Delivery, Payment, Policy, Verifier).
Sử dụng Handoff Pattern với các agent thật tuân theo frozen contracts.
"""
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Tuple
from src.contracts import (
    CaseInput,
    OrderFacts,
    OrderSellerFinding,
    DeliveryFinding,
    PaymentFinding,
    PolicyDecision,
    CaseOutput,
)
from src.agents.delivery_agent import DeliveryAgent
from src.agents.order_seller_agent import OrderSellerAgent
from src.agents.payment_agent import PaymentAgent
from src.agents.policy_agent import PolicyAgent
from src.agents.verifier_agent import VerifierAgent
from src.data_layer import load_order
from src.tracing import trace_event


class Coordinator:
    """
    Coordinator Agent điều phối toàn bộ quy trình xử lý case khiếu nại.
    """

    def __init__(self):
        pass

    def _run_order_seller_step(
        self, case: CaseInput, facts: OrderFacts
    ) -> Tuple[OrderSellerFinding, float]:
        t0 = time.time()
        finding = OrderSellerAgent.run(case, facts)
        elapsed = (time.time() - t0) * 1000
        return finding, elapsed

    def _run_payment_step(
        self, case: CaseInput, facts: OrderFacts
    ) -> Tuple[PaymentFinding, float]:
        t0 = time.time()
        finding = PaymentAgent.run(case, facts)
        elapsed = (time.time() - t0) * 1000
        return finding, elapsed

    def _run_delivery_step(
        self, case: CaseInput, facts: OrderFacts, order_seller_finding: OrderSellerFinding
    ) -> Tuple[DeliveryFinding, float]:
        t0 = time.time()
        finding = DeliveryAgent.run(case, facts, order_seller_finding)
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
        decision = PolicyAgent.run(
            case, order_seller_finding, delivery_finding, payment_finding
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
        output = VerifierAgent.run(
            case,
            facts,
            order_seller_finding,
            delivery_finding,
            payment_finding,
            policy_decision,
        )
        elapsed = (time.time() - t0) * 1000
        return output, elapsed

    def process_case(self, case: CaseInput) -> CaseOutput:
        """
        Luồng chính điều phối case từ Input -> Domain agents -> Policy -> Verifier -> Output.
        """
        start_time = time.time()
        
        # 1. Load Data
        facts = load_order(case.claimed_order_id)

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

        # 2. Fan-out independent domain agents (Order/Seller & Payment)
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="domain-agent") as pool:
            order_future = pool.submit(self._run_order_seller_step, case, facts)
            payment_future = pool.submit(self._run_payment_step, case, facts)
            order_seller_finding, t_os = order_future.result()
            payment_finding, t_pay = payment_future.result()

        trace_event(
            case_id=case.case_id,
            agent="OrderSellerAgent",
            task_type="inspect_order_seller",
            payload={"order_id": facts.order_id},
            status="completed",
            output=order_seller_finding.__dict__,
            latency_ms=t_os,
        )

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
