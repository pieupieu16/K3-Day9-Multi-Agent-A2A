"""Payment Agent for the Olist e-commerce dispute workflow."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, DefaultDict, Iterable, Mapping, Optional

from .financial_resolution import FinancialTotals, money, recommended_refund


PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent
MAX_PAYMENT_ENTITY_IDS = 5
DEFAULT_PAYMENTS_CSV = REPO_ROOT / "data" / "olist_order_payments_dataset.csv"
DEFAULT_ITEMS_CSV = REPO_ROOT / "data" / "olist_order_items_dataset.csv"
DEFAULT_ORDERS_CSV = REPO_ROOT / "data" / "olist_orders_dataset.csv"
DEFAULT_INPUT_DIR = REPO_ROOT / "input"
SUPPORTED_POLICY_VERSION = "EC_POLICY_V1"


@dataclass(frozen=True)
class PaymentRow:
    order_id: str
    payment_sequential: int
    payment_type: str
    payment_installments: int
    payment_value: Decimal


@dataclass(frozen=True)
class ItemAmount:
    price: Decimal
    freight_value: Decimal


class PaymentAgent:
    """Load payment data once and analyze any number of dispute cases.

    The agent owns payment reconciliation and financial resolution only. The
    Coordinator/Policy Agent should pass the selected ``primary_issue`` when it
    needs the final recommended refund.
    """

    def __init__(
        self,
        payments_csv: Path | str = DEFAULT_PAYMENTS_CSV,
        items_csv: Path | str = DEFAULT_ITEMS_CSV,
        orders_csv: Path | str = DEFAULT_ORDERS_CSV,
    ) -> None:
        self.payments_csv = Path(payments_csv)
        self.items_csv = Path(items_csv)
        self.orders_csv = Path(orders_csv)
        self._payments = self._load_payments(self.payments_csv)
        self._items = self._load_items(self.items_csv)
        self._order_statuses = self._load_order_statuses(self.orders_csv)

    @staticmethod
    def _rows(path: Path) -> Iterable[Mapping[str, str]]:
        if not path.is_file():
            raise FileNotFoundError(f"Required Olist CSV not found: {path}")
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            yield from csv.DictReader(handle)

    @classmethod
    def _load_payments(cls, path: Path) -> dict[str, list[PaymentRow]]:
        result: DefaultDict[str, list[PaymentRow]] = defaultdict(list)
        for row in cls._rows(path):
            order_id = row["order_id"].strip()
            result[order_id].append(
                PaymentRow(
                    order_id=order_id,
                    payment_sequential=int(row["payment_sequential"]),
                    payment_type=row["payment_type"].strip(),
                    payment_installments=int(row["payment_installments"]),
                    payment_value=money(row["payment_value"]),
                )
            )
        for rows in result.values():
            rows.sort(key=lambda value: value.payment_sequential)
        return dict(result)

    @classmethod
    def _load_items(cls, path: Path) -> dict[str, list[ItemAmount]]:
        result: DefaultDict[str, list[ItemAmount]] = defaultdict(list)
        for row in cls._rows(path):
            result[row["order_id"].strip()].append(
                ItemAmount(
                    price=money(row["price"]),
                    freight_value=money(row["freight_value"]),
                )
            )
        return dict(result)

    @classmethod
    def _load_order_statuses(cls, path: Path) -> dict[str, str]:
        return {
            row["order_id"].strip(): row["order_status"].strip().lower()
            for row in cls._rows(path)
        }

    @staticmethod
    def _sum_money(values: Iterable[Decimal]) -> Decimal:
        return money(sum(values, Decimal("0")))

    def analyze(
        self, order_id: str, primary_issue: Optional[str] = None
    ) -> dict[str, Any]:
        """Analyze payments and return a Coordinator-ready JSON-safe result.

        If ``primary_issue`` is omitted, canceled/unavailable paid orders can be
        inferred safely from the order status. Other issues need delivery/policy
        evidence and are deliberately not guessed by this agent.
        """

        order_id = order_id.strip()
        if not order_id:
            raise ValueError("order_id must be a non-empty string")
        if order_id not in self._order_statuses:
            raise KeyError(f"Order does not exist in orders CSV: {order_id}")

        payments = self._payments.get(order_id, [])
        items = self._items.get(order_id, [])
        totals = FinancialTotals(
            item_total=self._sum_money(item.price for item in items),
            freight_total=self._sum_money(item.freight_value for item in items),
            payment_total=self._sum_money(row.payment_value for row in payments),
        )

        effective_issue = primary_issue
        status = self._order_statuses[order_id]
        if effective_issue is None and totals.payment_total > 0:
            if status == "canceled":
                effective_issue = "canceled_order_paid"
            elif status == "unavailable":
                effective_issue = "unavailable_order_paid"

        all_payment_ids = [
            f"{order_id}:{row.payment_sequential}" for row in payments
        ]
        payment_ids = all_payment_ids[:MAX_PAYMENT_ENTITY_IDS]
        is_split_payment = len(payments) >= 2
        is_valid_split_payment = is_split_payment and totals.is_reconciled

        if not items and totals.payment_total > 0 and status in {"canceled", "unavailable"}:
            reconciliation_status = "unverifiable_terminal_order_without_items"
        elif not items and not payments:
            reconciliation_status = "no_financial_rows"
        elif totals.is_reconciled:
            reconciliation_status = "reconciled"
        else:
            reconciliation_status = "payment_total_mismatch"

        financial_issue_candidate = None
        financial_root_cause_candidate = None
        if totals.payment_total > 0 and status == "canceled":
            financial_issue_candidate = "canceled_order_paid"
            financial_root_cause_candidate = "ORDER_CANCELED_AFTER_PAYMENT"
        elif totals.payment_total > 0 and status == "unavailable":
            financial_issue_candidate = "unavailable_order_paid"
            financial_root_cause_candidate = "ORDER_UNAVAILABLE_AFTER_PAYMENT"
        elif is_valid_split_payment:
            financial_issue_candidate = "valid_split_payment"
            financial_root_cause_candidate = "MULTIPLE_PAYMENTS_RECONCILED"

        anomalies = []
        if reconciliation_status == "payment_total_mismatch":
            anomalies.append("PAYMENT_TOTAL_MISMATCH")
        if not payments and items:
            anomalies.append("ITEMS_WITHOUT_PAYMENT_ROWS")

        return {
            "order_id": order_id,
            "order_status": status,
            "payment_ids": payment_ids,
            "payment_evidence_ids": [f"payment:{value}" for value in payment_ids],
            "payment_count": len(payments),
            "payment_ids_truncated": len(all_payment_ids) > len(payment_ids),
            "payment_rows": [
                {
                    "payment_id": f"{order_id}:{row.payment_sequential}",
                    "payment_sequential": row.payment_sequential,
                    "payment_type": row.payment_type,
                    "payment_installments": row.payment_installments,
                    "payment_value_brl": float(row.payment_value),
                }
                for row in payments[:MAX_PAYMENT_ENTITY_IDS]
            ],
            "has_payment": bool(payments),
            "is_split_payment": is_split_payment,
            "is_valid_split_payment": is_valid_split_payment,
            "is_reconciled": totals.is_reconciled,
            "reconciliation_status": reconciliation_status,
            "reconciliation_difference_brl": float(totals.difference),
            "financial_issue_candidate": financial_issue_candidate,
            "financial_root_cause_candidate": financial_root_cause_candidate,
            "anomalies": anomalies,
            "financial_resolution": {
                "currency": "BRL",
                "item_total_brl": float(totals.item_total),
                "freight_total_brl": float(totals.freight_total),
                "expected_total_brl": float(totals.expected_total),
                "payment_total_brl": float(totals.payment_total),
                "recommended_refund_brl": float(
                    recommended_refund(effective_issue, totals)
                ),
            },
            "trace": [
                {
                    "step": "load_financial_rows",
                    "detail": f"loaded {len(items)} item rows and {len(payments)} payment rows",
                },
                {
                    "step": "aggregate_totals",
                    "detail": (
                        f"items={totals.item_total}, freight={totals.freight_total}, "
                        f"payments={totals.payment_total} BRL"
                    ),
                },
                {
                    "step": "reconcile_payment",
                    "detail": (
                        f"status={reconciliation_status}, difference={totals.difference} BRL"
                    ),
                },
                {
                    "step": "calculate_refund",
                    "detail": f"primary_issue={effective_issue or 'pending_policy_decision'}",
                },
            ],
        }

    def analyze_case(
        self,
        case: Mapping[str, Any],
        primary_issue: Optional[str] = None,
    ) -> dict[str, Any]:
        """Validate one input case and create an A2A-style handoff response."""

        if not isinstance(case, Mapping):
            raise TypeError("case must be a mapping")
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("case.case_id must be a non-empty string")
        policy_version = case.get("policy_version")
        if policy_version != SUPPORTED_POLICY_VERSION:
            raise ValueError(
                f"Unsupported policy version for {case_id}: {policy_version!r}"
            )
        customer_request = case.get("customer_request")
        if not isinstance(customer_request, Mapping):
            raise ValueError(f"{case_id}.customer_request must be an object")
        order_id = customer_request.get("claimed_order_id")
        if not isinstance(order_id, str) or not order_id.strip():
            raise ValueError(f"{case_id}.customer_request.claimed_order_id is required")

        analysis = self.analyze(order_id, primary_issue)
        return {
            "case_id": case_id,
            "agent": "payment_agent",
            "policy_version": policy_version,
            "handoff_status": "completed",
            **analysis,
        }

    def analyze_input_directory(
        self,
        input_dir: Path | str = DEFAULT_INPUT_DIR,
        primary_issues: Optional[Mapping[str, str]] = None,
    ) -> list[dict[str, Any]]:
        """Analyze all EC_*.json inputs in filename order without writing output."""

        directory = Path(input_dir)
        if not directory.is_dir():
            raise FileNotFoundError(f"Input directory not found: {directory}")
        paths = sorted(directory.glob("EC_*.json"))
        if not paths:
            raise ValueError(f"No EC_*.json cases found in {directory}")

        results = []
        seen_case_ids = set()
        for path in paths:
            with path.open("r", encoding="utf-8-sig") as handle:
                case = json.load(handle)
            case_id = case.get("case_id")
            if path.stem != case_id:
                raise ValueError(
                    f"Case/file mismatch: {path.name} contains case_id={case_id!r}"
                )
            if case_id in seen_case_ids:
                raise ValueError(f"Duplicate case_id: {case_id}")
            seen_case_ids.add(case_id)
            issue = primary_issues.get(case_id) if primary_issues else None
            results.append(self.analyze_case(case, issue))
        return results


def analyze_payment(
    order_id: str,
    primary_issue: Optional[str] = None,
    *,
    agent: Optional[PaymentAgent] = None,
) -> dict[str, Any]:
    """Small functional entry point useful for a Coordinator handoff."""

    return (agent or PaymentAgent()).analyze(order_id, primary_issue)

