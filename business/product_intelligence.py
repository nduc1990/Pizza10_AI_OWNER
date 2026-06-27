"""Product Intelligence v2 for menu performance and health."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def build_product_intelligence(
    order_details: list[dict[str, Any]],
    products: list[dict[str, Any]] | None = None,
    previous_order_details: list[dict[str, Any]] | None = None,
    history_order_details_by_date: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    products = products or []
    previous_order_details = previous_order_details or []
    history_order_details_by_date = history_order_details_by_date or {}

    performance = build_product_performance(order_details, products)
    abc_analysis = build_abc_analysis(performance)
    pareto = build_pareto(performance)
    dependency = build_product_dependency(performance)
    trends = build_product_trends(
        order_details,
        previous_order_details,
        history_order_details_by_date,
        products,
    )
    slow_moving = build_slow_moving_products(products, history_order_details_by_date)
    menu_health_score = calculate_menu_health_score(
        abc_analysis,
        pareto,
        dependency,
        slow_moving,
        performance,
    )

    return {
        "product_performance": performance,
        "abc_analysis": abc_analysis,
        "pareto": pareto,
        "product_trend": trends,
        "product_dependency": dependency,
        "slow_moving_products": slow_moving,
        "menu_health_score": menu_health_score,
    }


def build_product_performance(
    order_details: list[dict[str, Any]], products: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    lookup = build_product_lookup(products)
    totals = summarize_details(order_details, lookup)
    total_revenue = sum(item["revenue"] for item in totals.values())
    total_quantity = sum(item["quantity"] for item in totals.values())

    by_revenue = sorted(totals.values(), key=lambda item: item["revenue"], reverse=True)
    by_quantity = sorted(totals.values(), key=lambda item: item["quantity"], reverse=True)
    revenue_rank = {item["key"]: index for index, item in enumerate(by_revenue, start=1)}
    quantity_rank = {item["key"]: index for index, item in enumerate(by_quantity, start=1)}

    performance = []
    for item in by_revenue:
        quantity = item["quantity"]
        revenue = item["revenue"]
        performance.append(
            {
                "product_id": item.get("product_id"),
                "name": item["name"],
                "revenue": round(revenue),
                "quantity": clean_number(quantity),
                "average_price": round(revenue / quantity) if quantity else 0,
                "revenue_share_pct": pct(revenue, total_revenue),
                "quantity_share_pct": pct(quantity, total_quantity),
                "rank_by_revenue": revenue_rank[item["key"]],
                "rank_by_quantity": quantity_rank[item["key"]],
            }
        )
    return performance


def build_abc_analysis(performance: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    abc = {"A": [], "B": [], "C": []}
    cumulative = 0.0
    for item in performance:
        product = minimal_product(item)
        if cumulative < 70:
            abc["A"].append(product)
        elif cumulative < 90:
            abc["B"].append(product)
        else:
            abc["C"].append(product)
        cumulative += number(item.get("revenue_share_pct"))
    return abc


def build_pareto(performance: list[dict[str, Any]]) -> dict[str, Any]:
    product_count = len(performance)
    top_count = max(1, round(product_count * 0.2)) if product_count else 0
    top_products = performance[:top_count]
    total_revenue = sum(number(item.get("revenue")) for item in performance)
    revenue_from_top20 = sum(number(item.get("revenue")) for item in top_products)
    return {
        "top_20pct_products": [minimal_product(item) for item in top_products],
        "revenue_from_top20": round(revenue_from_top20),
        "revenue_pct_from_top20": pct(revenue_from_top20, total_revenue),
    }


def build_product_dependency(performance: list[dict[str, Any]]) -> dict[str, Any]:
    top1 = sum_share(performance, 1)
    top3 = sum_share(performance, 3)
    top5 = sum_share(performance, 5)
    return {
        "top1_revenue_share_pct": top1,
        "top3_revenue_share_pct": top3,
        "top5_revenue_share_pct": top5,
        "menu_dependency_rule_triggered": top3 > 80,
    }


def build_product_trends(
    today_details: list[dict[str, Any]],
    previous_details: list[dict[str, Any]],
    history_details_by_date: dict[str, list[dict[str, Any]]],
    products: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    lookup = build_product_lookup(products)
    today = summarize_details(today_details, lookup)
    yesterday = summarize_details(previous_details, lookup)
    seven_day_totals = summarize_history(history_details_by_date, 7, lookup)

    trends = []
    for key, item in sorted(today.items(), key=lambda row: row[1]["revenue"], reverse=True):
        today_revenue = item["revenue"]
        yesterday_revenue = yesterday.get(key, {}).get("revenue", 0)
        seven_day_avg = seven_day_totals.get(key, {}).get("revenue", 0) / 7
        trends.append(
            {
                "product_id": item.get("product_id"),
                "name": item["name"],
                "today_revenue": round(today_revenue),
                "yesterday_revenue": round(yesterday_revenue),
                "seven_day_avg_revenue": round(seven_day_avg),
                "growth_pct_vs_yesterday": percent_change(today_revenue, yesterday_revenue),
                "growth_pct_vs_7d_avg": percent_change(today_revenue, seven_day_avg),
            }
        )
    return trends


def build_slow_moving_products(
    products: list[dict[str, Any]],
    history_details_by_date: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    lookup = build_product_lookup(products)
    windows = {7: summarize_history(history_details_by_date, 7, lookup),
               14: summarize_history(history_details_by_date, 14, lookup),
               30: summarize_history(history_details_by_date, 30, lookup)}
    slow = []
    for product in products:
        product_id = product.get("Id") or product.get("ID") or product.get("ProductId")
        name = product.get("Name") or product.get("ProductName") or product.get("Code")
        if product_id is None or not name:
            continue
        key = product_id
        days_without_sales = None
        if number(windows[30].get(key, {}).get("quantity")) == 0:
            days_without_sales = 30
        elif number(windows[14].get(key, {}).get("quantity")) == 0:
            days_without_sales = 14
        elif number(windows[7].get(key, {}).get("quantity")) == 0:
            days_without_sales = 7
        if days_without_sales:
            slow.append(
                {
                    "product_id": product_id,
                    "name": str(name),
                    "days_without_sales": days_without_sales,
                }
            )
    return slow


def calculate_menu_health_score(
    abc_analysis: dict[str, list[dict[str, Any]]],
    pareto: dict[str, Any],
    dependency: dict[str, Any],
    slow_moving: list[dict[str, Any]],
    performance: list[dict[str, Any]],
) -> int:
    score = 100
    if not performance:
        return 0

    if not abc_analysis["A"]:
        score -= 15
    if number(pareto.get("revenue_pct_from_top20")) > 85:
        score -= 15
    if number(dependency.get("top3_revenue_share_pct")) > 80:
        score -= 20
    elif number(dependency.get("top3_revenue_share_pct")) > 65:
        score -= 10
    slow_ratio = len(slow_moving) / max(len(performance), 1)
    if slow_ratio > 1:
        score -= 20
    elif slow_ratio > 0.5:
        score -= 10
    if performance and number(performance[0].get("revenue_share_pct")) > 50:
        score -= 15
    return max(0, min(100, score))


def summarize_history(
    history_details_by_date: dict[str, list[dict[str, Any]]],
    days: int,
    lookup: dict[Any, str],
) -> dict[Any, dict[str, Any]]:
    selected_dates = sorted(history_details_by_date.keys())[-days:]
    rows: list[dict[str, Any]] = []
    for day in selected_dates:
        rows.extend(history_details_by_date.get(day, []))
    return summarize_details(rows, lookup)


def summarize_details(
    order_details: list[dict[str, Any]], lookup: dict[Any, str]
) -> dict[Any, dict[str, Any]]:
    totals: dict[Any, dict[str, Any]] = defaultdict(
        lambda: {
            "key": None,
            "product_id": None,
            "name": "Không rõ món",
            "quantity": 0.0,
            "revenue": 0.0,
        }
    )
    for row in order_details:
        product_id = row.get("ProductId") or row.get("ProductID") or row.get("Id")
        name = (
            row.get("ProductName")
            or row.get("Product")
            or row.get("Name")
            or row.get("ItemName")
            or lookup.get(product_id)
            or f"ProductID {product_id or 'unknown'}"
        )
        quantity = number(row.get("Quantity") or row.get("Qty"))
        revenue = number(row.get("Total") or row.get("Amount") or row.get("Revenue"))
        if revenue == 0:
            revenue = quantity * number(row.get("Price") or row.get("UnitPrice"))
        key = product_id or name
        totals[key]["key"] = key
        totals[key]["product_id"] = product_id
        totals[key]["name"] = str(name)
        totals[key]["quantity"] += quantity
        totals[key]["revenue"] += revenue
    return totals


def build_product_lookup(products: list[dict[str, Any]]) -> dict[Any, str]:
    lookup: dict[Any, str] = {}
    for product in products:
        product_id = product.get("Id") or product.get("ID") or product.get("ProductId")
        name = product.get("Name") or product.get("ProductName") or product.get("Code")
        if product_id is not None and name:
            lookup[product_id] = str(name)
    return lookup


def minimal_product(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": item.get("name"),
        "revenue": item.get("revenue"),
        "quantity": item.get("quantity"),
        "revenue_share_pct": item.get("revenue_share_pct"),
    }


def sum_share(performance: list[dict[str, Any]], count: int) -> float:
    return round(sum(number(item.get("revenue_share_pct")) for item in performance[:count]), 2)


def pct(value: float, total: float) -> float:
    if total == 0:
        return 0.0
    return round((value / total) * 100, 2)


def percent_change(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 2)


def number(value: Any) -> float:
    try:
        if value in (None, ""):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def clean_number(value: float) -> int | float:
    return int(value) if float(value).is_integer() else round(value, 2)
