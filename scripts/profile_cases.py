"""Profile input cases against Olist facts before a full pipeline run."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.data_layer import load_order


def total(rows, field: str) -> Decimal:
    return sum((Decimal(str(getattr(row, field))) for row in rows), Decimal("0"))


def classify(facts) -> str:
    payment_total = total(facts.payments, "payment_value")
    item_total = total(facts.items, "price")
    freight_total = total(facts.items, "freight_value")
    delivered_late = bool(facts.delivered_customer_ts and facts.estimated_delivery_ts and facts.delivered_customer_ts > facts.estimated_delivery_ts)
    seller_late = any(
        facts.delivered_carrier_ts and item.shipping_limit_ts and facts.delivered_carrier_ts > item.shipping_limit_ts
        for item in facts.items
    )
    if facts.order_status == "canceled" and payment_total > 0:
        return "canceled_order_paid"
    if facts.order_status == "unavailable" and payment_total > 0:
        return "unavailable_order_paid"
    if delivered_late and seller_late:
        return "late_delivery_seller"
    if delivered_late:
        return "late_delivery_logistics"
    if len(facts.payments) >= 2 and abs(payment_total - (item_total + freight_total)) <= Decimal("0.10"):
        return "valid_split_payment"
    return "unsupported_late_claim"


def main() -> int:
    parser = argparse.ArgumentParser(description="Profile EC input cases using deterministic Olist facts.")
    parser.add_argument("input_dir", nargs="?", default=ROOT_DIR / "input", type=Path)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    cases = sorted(args.input_dir.glob("EC_*.json"))
    if args.limit is not None:
        cases = cases[:args.limit]
    if not cases:
        print(f"No EC_*.json files found in {args.input_dir}")
        return 1

    distribution: Counter[str] = Counter()
    missing_orders: list[str] = []
    multi_seller: list[str] = []
    missing_timestamps: list[str] = []

    for path in cases:
        with path.open("r", encoding="utf-8") as stream:
            payload = json.load(stream)
        claimed_order_id = payload.get("customer_request", {}).get("claimed_order_id", "")
        facts = load_order(claimed_order_id)
        if not facts.found:
            missing_orders.append(path.stem)
            continue
        distribution[classify(facts)] += 1
        if len({item.seller_id for item in facts.items}) > 1:
            multi_seller.append(path.stem)
        if any(value is None for value in (facts.delivered_carrier_ts, facts.delivered_customer_ts, facts.estimated_delivery_ts)):
            missing_timestamps.append(path.stem)

    print(f"Profiled {len(cases)} cases")
    print("\nIssue distribution:")
    for issue in ("canceled_order_paid", "unavailable_order_paid", "late_delivery_seller", "late_delivery_logistics", "valid_split_payment", "unsupported_late_claim"):
        print(f"  {issue}: {distribution[issue]}")
    print("\nAnomalies:")
    print(f"  Missing orders ({len(missing_orders)}): {', '.join(missing_orders) or '-'}")
    print(f"  Multi-seller orders ({len(multi_seller)}): {', '.join(multi_seller) or '-'}")
    print(f"  Orders with missing delivery timestamps ({len(missing_timestamps)}): {', '.join(missing_timestamps) or '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
