"""Backward-compatible analytics wrapper over the Business Engine."""

from __future__ import annotations

from datetime import date as Date
from typing import Any

from business.business_snapshot import build_business_snapshot
from rules.rule_engine import evaluate_rules


def build_daily_analytics(
    report_date: Date | str,
    orders: list[dict[str, Any]],
    order_details: list[dict[str, Any]],
    products: list[dict[str, Any]],
    previous_orders: list[dict[str, Any]] | None = None,
    previous_order_details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    snapshot = build_business_snapshot(
        report_date,
        orders,
        order_details,
        products,
        previous_orders,
        previous_order_details,
    )
    snapshot["rules"] = evaluate_rules(snapshot)

    sales = snapshot["sales"]
    products_metrics = snapshot["products"]
    rules = snapshot["rules"]
    return {
        "report_date": snapshot["report_date"],
        "revenue": sales["revenue"],
        "orders_count": sales["orders_count"],
        "avg_order_value": sales["avg_order_value"],
        "top_items": products_metrics["top_products"],
        "low_sales_items": [
            item for item in products_metrics["top_products"] if item["qty"] <= 1
        ],
        "alerts": [format_rule(rule) for rule in rules["all"]],
        "comparison": {
            "revenue_change_pct": sales["revenue_change_pct"],
            "orders_change_pct": sales["orders_change_pct"],
            "avg_order_change_pct": sales["avg_order_change_pct"],
        },
        "snapshot": snapshot,
    }


def format_rule(rule: dict[str, Any]) -> str:
    return f"{rule.get('title')}: {rule.get('message')}"
