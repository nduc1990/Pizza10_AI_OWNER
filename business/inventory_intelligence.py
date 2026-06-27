"""Inventory Intelligence v1 for read-only stock health analysis."""

from __future__ import annotations

from typing import Any


def build_inventory_intelligence(
    stock_items: list[dict[str, Any]] | None = None,
    products_inventory: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    items = normalize_stock_items(products_inventory or stock_items or [])
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
    inventory_value = sum(number(item.get("inventory_value")) for item in items)

    return {
        "inventory_value": round(inventory_value),
        "stock_health_score": stock_health_score(low_stock_items, stockout_risk),
        "status": stock_health_status(low_stock_items, stockout_risk),
        "stock_items": items,
        "low_stock_items": low_stock_items,
        "overstock_items": overstock_items,
        "stockout_risk": stockout_risk,
        "inventory_days": None,
    }


def normalize_stock_items(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row in rows:
        on_hand = first_number(row, ("OnHand", "on_hand", "quantity"))
        total_on_hand = first_number(row, ("TotalOnHand", "total_on_hand"))
        cost = first_number(row, ("Cost", "cost"))
        recent_purchase_price = first_number(row, ("RecentPurchasePrice", "recent_purchase_price"))
        min_quantity = first_number(row, ("MinQuantity", "min_quantity", "minimum_quantity"))
        max_quantity = first_number(row, ("MaxQuantity", "max_quantity", "maximum_quantity"))
        compare_min_quantity = first_number(row, ("CompareMinQuantity", "compare_min_quantity"))
        unit_cost = cost if cost is not None else recent_purchase_price

        item = {
            "product_id": row.get("Id") or row.get("ProductId") or row.get("product_id"),
            "code": row.get("Code") or row.get("code"),
            "name": row.get("Name") or row.get("name"),
            "unit": row.get("Unit") or row.get("unit"),
            "on_hand": on_hand,
            "total_on_hand": total_on_hand,
            "cost": cost,
            "recent_purchase_price": recent_purchase_price,
            "min_quantity": min_quantity,
            "max_quantity": max_quantity,
            "compare_min_quantity": compare_min_quantity,
            "category_id": row.get("CategoryId") or row.get("category_id"),
            "inventory_value": (on_hand or 0) * (unit_cost or 0),
            "raw": row,
        }
        items.append(item)
    return items


def stock_health_score(
    low_stock_items: list[dict[str, Any]], stockout_risk: list[dict[str, Any]]
) -> int:
    if len(stockout_risk) >= 3:
        return 30
    if stockout_risk:
        return 50
    if low_stock_items:
        return 80
    return 100


def stock_health_status(
    low_stock_items: list[dict[str, Any]], stockout_risk: list[dict[str, Any]]
) -> str:
    if len(stockout_risk) >= 3:
        return "Critical"
    if stockout_risk:
        return "Warning"
    if low_stock_items:
        return "Good"
    return "Excellent"


def is_low_stock(item: dict[str, Any]) -> bool:
    on_hand = nullable_number(item.get("on_hand"))
    minimum = nullable_number(item.get("min_quantity"))
    return on_hand is not None and minimum is not None and minimum > 0 and on_hand <= minimum


def is_overstock(item: dict[str, Any]) -> bool:
    on_hand = nullable_number(item.get("on_hand"))
    maximum = nullable_number(item.get("max_quantity"))
    return on_hand is not None and maximum is not None and maximum > 0 and on_hand >= maximum


def is_stockout_risk(item: dict[str, Any]) -> bool:
    on_hand = nullable_number(item.get("on_hand"))
    return on_hand is not None and on_hand <= 0


def first_number(row: dict[str, Any], fields: tuple[str, ...]) -> float | None:
    for field in fields:
        parsed = nullable_number(row.get(field))
        if parsed is not None:
            return parsed
    return None


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
