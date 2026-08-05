"""Payment specialist: deterministic reconciliation with a small-LLM note."""

from __future__ import annotations

import json
from typing import Any

from src.contracts import CaseInput, OrderFacts, PaymentFinding
from src.financial import calculate_totals, is_reconciled
from src.llm_client import MODEL_NAME, call_llm


SYSTEM_PROMPT = """You are PaymentAgent using a model below 10B parameters.
Review only the supplied payment rows and deterministic financial totals.
Return one JSON object with a concise `notes` string. Do not infer facts from
other business domains. Never recalculate or alter amounts."""


def _llm_notes(facts: OrderFacts, totals: tuple[float, float, float]) -> str:
    """Ask the LLM for commentary without exposing another agent's data."""
    items, freight, payments = totals
    payload = {
        "agent": "payment",
        "payment_rows": [
            {
                "order_id": row.order_id,
                "payment_sequential": row.payment_sequential,
                "payment_type": row.payment_type,
                "installments": row.installments,
                "payment_value": row.payment_value,
            }
            for row in (facts.payments or [])
        ],
        "deterministic_totals": {
            "item_total": items,
            "freight_total": freight,
            "payment_total": payments,
        },
    }
    try:
        response = call_llm(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            system_prompt=SYSTEM_PROMPT,
            json_mode=True,
        )
        if isinstance(response, dict):
            note = response.get("notes")
            if isinstance(note, str) and note.strip():
                return note.strip()
    except Exception:
        # Reconciliation remains available if the optional explanation fails.
        pass
    return f"Deterministic payment reconciliation; explanation model={MODEL_NAME}"


def analyze_payment(case: CaseInput, facts: OrderFacts) -> PaymentFinding:
    """Build the authoritative payment finding for one order."""
    del case  # Case text and timestamps are intentionally outside this agent's scope.
    totals = calculate_totals(facts.items or [], facts.payments or [])
    items, freight, payments = totals
    payment_rows = list(facts.payments or [])

    # Entity collections are bounded by the output contract. n_payment_rows still
    # reports the complete row count.
    payment_ids = [
        f"{facts.order_id}:{row.payment_sequential}" for row in payment_rows
    ][:5]
    evidence = [f"payment:{payment_id}" for payment_id in payment_ids]

    return PaymentFinding(
        n_payment_rows=len(payment_rows),
        payment_total=payments,
        item_total=items,
        freight_total=freight,
        reconciled_within_010=is_reconciled(payments, items, freight),
        is_split_payment=len(payment_rows) >= 2,
        payment_ids=payment_ids,
        evidence=evidence,
        notes=_llm_notes(facts, totals),
    )


class PaymentAgent:
    """Coordinator-compatible agent facade."""

    @staticmethod
    def run(case: CaseInput, facts: OrderFacts) -> PaymentFinding:
        return analyze_payment(case, facts)


run = analyze_payment
