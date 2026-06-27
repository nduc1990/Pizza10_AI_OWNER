"""Build the owner business snapshot consumed by rules and AI."""

from __future__ import annotations

from datetime import date as Date
from typing import Any

from business.finance_engine import build_finance_metrics
from business.finance_intelligence import build_finance_intelligence
from business.inventory_intelligence import build_inventory_intelligence
from business.product_engine import build_product_metrics
from business.product_intelligence import build_product_intelligence
from business.sales_engine import build_sales_metrics


def build_business_snapshot(
    report_date: Date | str,
    orders: list[dict[str, Any]],
    order_details: list[dict[str, Any]],
    products: list[dict[str, Any]] | None = None,
    previous_orders: list[dict[str, Any]] | None = None,
    previous_order_details: list[dict[str, Any]] | None = None,
    history_orders_by_date: dict[str, list[dict[str, Any]]] | None = None,
    history_order_details_by_date: dict[str, list[dict[str, Any]]] | None = None,
    supplier_debt: Any = None,
    stock_items: list[dict[str, Any]] | None = None,
    store: str = "Pizza 10 Điểm - CS1",
) -> dict[str, Any]:
    return {
        "report_date": str(report_date),
        "store": store,
        "sales": build_sales_metrics(
            orders,
            order_details,
            previous_orders,
            previous_order_details,
            history_orders_by_date,
            report_date,
        ),
        "products": build_product_metrics(order_details, products),
        "product_intelligence": build_product_intelligence(
            order_details,
            products,
            previous_order_details,
            history_order_details_by_date,
        ),
        "finance": build_finance_metrics(supplier_debt),
        "finance_intelligence": build_finance_intelligence(supplier_debt),
        "inventory_intelligence": build_inventory_intelligence(stock_items),
    }
