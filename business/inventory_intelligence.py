"""Inventory Intelligence v1 for read-only stock health analysis."""

from __future__ import annotations

from typing import Any


def build_inventory_intelligence(
    stock_items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    items = stock_items or []
    if not items:
        return {
            "inventory_value": None,
            "stock_health_score": None,
            "status": "Unknown",
            "stock_items": [],
            "low_stock_items": [],
            "overstock_items": [],
            "stockout_risk": [],
            "inventory_days": None,
        }

    low_stock_items = [item for item in items if is_low_stock(item)]
    overstock_items = [item for item in items if is_overstock(item)]
    stockout_risk = [item for item in items if is_stockout_risk(item)]
    inventory_value = sum(number(item.get("stock_value")) for item in items)

    return {
        "inventory_value": round(inventory_value),
        "stock_health_score": stock_health_score(low_stock_items, stockout_risk),
        "status": stock_health_status(low_stock_items, stockout_risk),
        "stock_items": items,
        "low_stock_items": low_stock_items,
        "overstock_items": overstock_items,
        "stockout_risk": stockout_risk,
        "inventory_days": inventory_days(items),
    }


def stock_health_score(
    low_stock_items: list[dict[str, Any]], stockout_risk: list[dict[str, Any]]
) -> int:
    if stockout_risk:
        return 40
    if len(low_stock_items) > 1:
        return 70
    if len(low_stock_items) == 1:
        return 90
    return 100


def stock_health_status(
    low_stock_items: list[dict[str, Any]], stockout_risk: list[dict[str, Any]]
) -> str:
    if stockout_risk:
        return "Stockout Risk"
    if low_stock_items:
        return "Low Stock"
    return "Healthy"


def inventory_days(items: list[dict[str, Any]]) -> float | None:
    days_values = [
        number(item.get("inventory_days"))
        for item in items
        if item.get("inventory_days") is not None
    ]
    if not days_values:
        return None
    return round(sum(days_values) / len(days_values), 2)


def is_low_stock(item: dict[str, Any]) -> bool:
    quantity = nullable_number(item.get("quantity"))
    minimum = nullable_number(item.get("minimum_quantity"))
    return quantity is not None and minimum is not None and quantity <= minimum


def is_overstock(item: dict[str, Any]) -> bool:
    quantity = nullable_number(item.get("quantity"))
    maximum = nullable_number(item.get("maximum_quantity"))
    return quantity is not None and maximum is not None and quantity >= maximum


def is_stockout_risk(item: dict[str, Any]) -> bool:
    quantity = nullable_number(item.get("quantity"))
    daily_usage = nullable_number(item.get("daily_usage"))
    if quantity is None:
        return False
    if quantity <= 0:
        return True
    return daily_usage is not None and daily_usage > 0 and quantity / daily_usage <= 1


def nullable_number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return number(value)


def number(value: Any) -> float:
    try:
        if value in (None, ""):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0
