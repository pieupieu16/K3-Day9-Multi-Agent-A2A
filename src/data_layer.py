"""Cached Olist CSV access returning the frozen ``OrderFacts`` contract."""

from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.contracts import ItemFact, OrderFacts, PaymentFact

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
FIXTURES_DIR = ROOT_DIR / "tests" / "fixtures"


def _optional(value: Any) -> str | None:
    value = str(value or "").strip()
    return value or None


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _integer(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


class OlistDataLayer:
    """Preloads CSVs once and exposes O(1) order lookup after warm-up."""

    def __init__(self, data_dir: str | Path = DATA_DIR) -> None:
        self.data_dir = Path(data_dir)
        self._loaded = False
        self._orders: dict[str, dict[str, str]] = {}
        self._items_by_order: dict[str, list[dict[str, str]]] = defaultdict(list)
        self._payments_by_order: dict[str, list[dict[str, str]]] = defaultdict(list)
        self._seller_ids: set[str] = set()
        self._fixtures: dict[str, dict[str, Any]] | None = None

    def _read_csv(self, filename: str) -> list[dict[str, str]]:
        path = self.data_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing required Olist CSV: {path}")
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            return list(csv.DictReader(stream))

    def load(self) -> None:
        """Read and index four required CSV files exactly once."""
        if self._loaded:
            return

        for row in self._read_csv("olist_orders_dataset.csv"):
            order_id = _optional(row.get("order_id"))
            if order_id:
                self._orders[order_id] = row
        for row in self._read_csv("olist_order_items_dataset.csv"):
            order_id = _optional(row.get("order_id"))
            if order_id:
                self._items_by_order[order_id].append(row)
        for row in self._read_csv("olist_order_payments_dataset.csv"):
            order_id = _optional(row.get("order_id"))
            if order_id:
                self._payments_by_order[order_id].append(row)
        for row in self._read_csv("olist_sellers_dataset.csv"):
            seller_id = _optional(row.get("seller_id"))
            if seller_id:
                self._seller_ids.add(seller_id)
        self._loaded = True

    def _load_fixtures(self) -> None:
        if self._fixtures is not None:
            return
        self._fixtures = {}
        if not FIXTURES_DIR.exists():
            return
        for path in FIXTURES_DIR.glob("*.json"):
            with path.open("r", encoding="utf-8") as stream:
                data = json.load(stream)
            order_id = _optional(data.get("order_id"))
            if order_id:
                self._fixtures[order_id] = data

    @staticmethod
    def _facts_from_dict(data: dict[str, Any]) -> OrderFacts:
        order_id = str(data.get("order_id", ""))
        items = [
            ItemFact(
                order_id=str(row.get("order_id", order_id)),
                order_item_id=_integer(row.get("order_item_id")),
                product_id=str(row.get("product_id", "")),
                seller_id=str(row.get("seller_id", "")),
                shipping_limit_ts=_optional(row.get("shipping_limit_ts")),
                price=_number(row.get("price")),
                freight_value=_number(row.get("freight_value")),
            )
            for row in data.get("items", [])
        ]
        payments = [
            PaymentFact(
                order_id=str(row.get("order_id", order_id)),
                payment_sequential=_integer(row.get("payment_sequential")),
                payment_type=str(row.get("payment_type", "")),
                installments=_integer(row.get("installments")),
                payment_value=_number(row.get("payment_value")),
            )
            for row in data.get("payments", [])
        ]
        return OrderFacts(
            found=bool(data.get("found", False)), order_id=order_id,
            customer_id=_optional(data.get("customer_id")),
            order_status=_optional(data.get("order_status")),
            purchase_ts=_optional(data.get("purchase_ts")),
            approved_ts=_optional(data.get("approved_ts")),
            delivered_carrier_ts=_optional(data.get("delivered_carrier_ts")),
            delivered_customer_ts=_optional(data.get("delivered_customer_ts")),
            estimated_delivery_ts=_optional(data.get("estimated_delivery_ts")),
            items=items, payments=payments,
        )

    def load_order(self, order_id: str) -> OrderFacts:
        """Return one order's facts; fixture mode is enabled by ``FIXTURE_MODE=1``."""
        order_id = str(order_id or "").strip()
        if os.getenv("FIXTURE_MODE", "").lower() in {"1", "true", "yes"}:
            self._load_fixtures()
            assert self._fixtures is not None
            if order_id in self._fixtures:
                return self._facts_from_dict(self._fixtures[order_id])
            return OrderFacts(found=False, order_id=order_id)

        self.load()
        order = self._orders.get(order_id)
        if order is None:
            return OrderFacts(found=False, order_id=order_id)

        items = [
            ItemFact(
                order_id=order_id,
                order_item_id=_integer(row.get("order_item_id")),
                product_id=str(row.get("product_id", "")),
                seller_id=str(row.get("seller_id", "")),
                shipping_limit_ts=_optional(row.get("shipping_limit_date")),
                price=_number(row.get("price")),
                freight_value=_number(row.get("freight_value")),
            )
            for row in self._items_by_order.get(order_id, [])
        ]
        payments = [
            PaymentFact(
                order_id=order_id,
                payment_sequential=_integer(row.get("payment_sequential")),
                payment_type=str(row.get("payment_type", "")),
                installments=_integer(row.get("payment_installments")),
                payment_value=_number(row.get("payment_value")),
            )
            for row in self._payments_by_order.get(order_id, [])
        ]
        return OrderFacts(
            found=True, order_id=order_id,
            customer_id=_optional(order.get("customer_id")),
            order_status=_optional(order.get("order_status")),
            purchase_ts=_optional(order.get("order_purchase_timestamp")),
            approved_ts=_optional(order.get("order_approved_at")),
            delivered_carrier_ts=_optional(order.get("order_delivered_carrier_date")),
            delivered_customer_ts=_optional(order.get("order_delivered_customer_date")),
            estimated_delivery_ts=_optional(order.get("order_estimated_delivery_date")),
            items=items, payments=payments,
        )


_default_layer = OlistDataLayer()


def load_order(order_id: str) -> OrderFacts:
    """Coordinator-facing cached order lookup."""
    return _default_layer.load_order(order_id)


def order_facts_to_dict(facts: OrderFacts) -> dict[str, Any]:
    """Serialize facts for fixture/debug use without custom encoders."""
    return asdict(facts)
