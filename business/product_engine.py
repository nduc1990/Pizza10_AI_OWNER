"""Product metrics built from POS365 order details."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def build_product_metrics(
    order_details: list[dict[str, Any]], products: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    product_lookup = build_product_lookup(products or [])
    totals: dict[Any, dict[str, Any]] = defaultdict(
        lambda: {"name": "Khong ro mon", "qty": 0.0, "revenue": 0.0}
    )

    for row in order_details:
        product_id = row.get("ProductId") or row.get("ProductID") or row.get("Id")
        name = (
            row.get("ProductName")
            or row.get("Product")
            or row.get("Name")
            or row.get("ItemName")
            or product_lookup.get(product_id)
            or f"ProductID {product_id or 'unknown'}"
        )
        qty = number(row.get("Quantity") or row.get("Qty"))
        revenue = number(row.get("Total") or row.get("Amount") or row.get("Revenue"))
        if revenue == 0:
            revenue = qty * number(row.get("Price") or row.get("UnitPrice"))

        key = product_id or name
        totals[key]["name"] = str(name)
        totals[key]["qty"] += qty
        totals[key]["revenue"] += revenue

    total_product_revenue = sum(item["revenue"] for item in totals.values())
    top_products = []
    for item in sorted(totals.values(), key=lambda row: row["revenue"], reverse=True)[:10]:
        share_pct = (
            round((item["revenue"] / total_product_revenue) * 100, 2)
            if total_product_revenue
            else None
        )
        top_products.append(
            {
                "name": item["name"],
                "qty": clean_number(item["qty"]),
                "revenue": round(item["revenue"]),
                "share_pct": share_pct,
            }
        )

    return {
        "top_products": top_products,
        "product_count": len(totals),
    }


def build_product_lookup(products: list[dict[str, Any]]) -> dict[Any, str]:
    lookup: dict[Any, str] = {}
    for product in products:
        product_id = product.get("Id") or product.get("ID") or product.get("ProductId")
        name = product.get("Name") or product.get("ProductName") or product.get("Code")
        if product_id is not None and name:
            lookup[product_id] = str(name)
    return lookup


def number(value: Any) -> float:
    try:
        if value in (None, ""):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def clean_number(value: float) -> int | float:
    return int(value) if float(value).is_integer() else round(value, 2)
