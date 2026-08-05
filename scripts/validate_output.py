"""Validate submitted EC_POLICY_V1 output files without external dependencies."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_FILES = {f"EC_{number:03d}.json" for number in range(1, 51)}
ISSUES = {
    "canceled_order_paid", "unavailable_order_paid", "late_delivery_seller",
    "late_delivery_logistics", "valid_split_payment", "unsupported_late_claim",
}
CAUSES = {
    "SELLER_HANDOFF_AFTER_LIMIT", "CARRIER_DELIVERED_AFTER_ESTIMATE",
    "ORDER_CANCELED_AFTER_PAYMENT", "ORDER_UNAVAILABLE_AFTER_PAYMENT",
    "MULTIPLE_PAYMENTS_RECONCILED", "DELIVERY_WITHIN_ESTIMATE",
}
EVIDENCE = [
    re.compile(r"^order:[^:]+$"), re.compile(r"^item:[^:]+:[1-9][0-9]*$"),
    re.compile(r"^payment:[^:]+:[1-9][0-9]*$"), re.compile(r"^seller:[^:]+$"),
    re.compile(r"^policy:(" + "|".join(CAUSES) + r")$"),
]
TOP_LEVEL_KEYS = {
    "case_id", "assessment", "affected_entities", "root_cause_analysis",
    "evidence_ids", "financial_resolution", "resolution_actions",
}


def _is_money(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and round(value, 2) == value


def validate_case(path: Path) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"{path.name}: invalid JSON ({error})"]
    errors: list[str] = []
    if not isinstance(data, dict) or set(data) != TOP_LEVEL_KEYS:
        errors.append(f"{path.name}: top-level keys must exactly match schema")
        return errors
    if data["case_id"] != path.stem:
        errors.append(f"{path.name}: case_id must match filename")
    assessment = data["assessment"]
    entities = data["affected_entities"]
    analysis = data["root_cause_analysis"]
    financial = data["financial_resolution"]
    if not isinstance(assessment, dict) or assessment.get("primary_issue") not in ISSUES:
        errors.append(f"{path.name}: invalid primary_issue")
    if not isinstance(assessment, dict) or assessment.get("case_status") not in {"action_required", "no_action"}:
        errors.append(f"{path.name}: invalid case_status")
    confidence = assessment.get("confidence") if isinstance(assessment, dict) else None
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
        errors.append(f"{path.name}: confidence must be in [0, 1]")
    if not isinstance(entities, dict) or set(entities) != {"order_ids", "item_ids", "seller_ids", "payment_ids"}:
        errors.append(f"{path.name}: invalid affected_entities keys")
    elif any(not isinstance(entities[key], list) or len(entities[key]) > 5 for key in entities):
        errors.append(f"{path.name}: entity ID sets must be lists of at most 5")
    evidence = data["evidence_ids"]
    if not isinstance(evidence, list) or len(evidence) > 10 or any(not isinstance(entry, str) or not any(rule.fullmatch(entry) for rule in EVIDENCE) for entry in evidence):
        errors.append(f"{path.name}: invalid evidence IDs")
    if not isinstance(analysis, dict) or set(analysis) != {"ranked_causes", "responsible_parties"}:
        errors.append(f"{path.name}: invalid root_cause_analysis keys")
    else:
        causes = analysis["ranked_causes"]
        parties = analysis["responsible_parties"]
        if not isinstance(causes, list) or len(causes) > 3 or any(not isinstance(cause, dict) or cause.get("cause_code") not in CAUSES for cause in causes):
            errors.append(f"{path.name}: invalid ranked_causes")
        if not isinstance(parties, list) or len(parties) > 3 or any(not isinstance(party, dict) or set(party) != {"party_type", "party_id"} for party in parties):
            errors.append(f"{path.name}: invalid responsible_parties")
    if not isinstance(financial, dict) or set(financial) != {"currency", "item_total_brl", "freight_total_brl", "payment_total_brl", "recommended_refund_brl"}:
        errors.append(f"{path.name}: invalid financial_resolution keys")
    elif financial.get("currency") != "BRL" or any(not _is_money(financial[key]) for key in ("item_total_brl", "freight_total_brl", "payment_total_brl", "recommended_refund_brl")):
        errors.append(f"{path.name}: financial values must be finite 2-decimal BRL numbers")
    actions = data["resolution_actions"]
    if not isinstance(actions, list) or len(actions) > 5 or not all(isinstance(action, str) for action in actions):
        errors.append(f"{path.name}: resolution_actions must be strings, at most 5")
    return errors


def validate_directory(output_dir: Path) -> list[str]:
    actual = {path.name for path in output_dir.glob("*.json")}
    errors = []
    missing, unexpected = EXPECTED_FILES - actual, actual - EXPECTED_FILES
    if missing:
        errors.append(f"missing files: {', '.join(sorted(missing))}")
    if unexpected:
        errors.append(f"unexpected files: {', '.join(sorted(unexpected))}")
    for filename in sorted(EXPECTED_FILES & actual):
        errors.extend(validate_case(output_dir / filename))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output")
    args = parser.parse_args()
    errors = validate_directory(args.output_dir)
    if errors:
        print("Validation failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"Validation passed: 50 files in {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())