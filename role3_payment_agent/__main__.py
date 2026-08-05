"""Command-line entry point: python -m role3_payment_agent."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .agent import DEFAULT_INPUT_DIR, PaymentAgent


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a concise, JSON-serializable batch report."""

    return {
        "case_count": len(results),
        "all_handoffs_completed": all(
            result["handoff_status"] == "completed" for result in results
        ),
        "order_statuses": dict(Counter(result["order_status"] for result in results)),
        "reconciliation_statuses": dict(
            Counter(result["reconciliation_status"] for result in results)
        ),
        "financial_issue_candidates": dict(
            Counter(
                result["financial_issue_candidate"] or "pending_delivery_policy"
                for result in results
            )
        ),
        "split_payment_cases": sum(
            result["is_split_payment"] for result in results
        ),
        "automatic_refund_total_brl": round(
            sum(
                result["financial_resolution"]["recommended_refund_brl"]
                for result in results
            ),
            2,
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Role 3 Payment Agent")
    parser.add_argument("order_id", nargs="?", help="analyze one Olist order")
    parser.add_argument("--primary-issue", default=None)
    parser.add_argument(
        "--input-dir",
        type=Path,
        help=f"analyze all EC_*.json cases (example: {DEFAULT_INPUT_DIR})",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="print a concise summary instead of all handoff payloads",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        help="optionally save the JSON result to a file",
    )
    args = parser.parse_args()

    agent = PaymentAgent()
    if args.input_dir:
        results = agent.analyze_input_directory(args.input_dir)
        payload: Any = summarize(results) if args.summary else results
    elif args.order_id:
        payload = agent.analyze(args.order_id, args.primary_issue)
    else:
        parser.error("provide order_id or --input-dir")

    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output_file:
        args.output_file.parent.mkdir(parents=True, exist_ok=True)
        args.output_file.write_text(rendered + "\n", encoding="utf-8")
        print(f"Wrote {args.output_file}")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
