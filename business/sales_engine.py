"""Sales metrics built from POS365 order data."""

from __future__ import annotations

from datetime import date as Date
from datetime import datetime, timedelta
from typing import Any

from fetch_pos365 import order_date


MIN_COMPARISON_ORDERS = 3
SELLING_WINDOWS = ((5, 10), (15, 20))


def build_sales_metrics(
    orders: list[dict[str, Any]],
    order_details: list[dict[str, Any]],
    previous_orders: list[dict[str, Any]] | None = None,
    previous_order_details: list[dict[str, Any]] | None = None,
    history_orders_by_date: dict[str, list[dict[str, Any]]] | None = None,
    report_date: Date | str | None = None,
) -> dict[str, Any]:
    del order_details, previous_order_details
    previous_orders = previous_orders or []
    history_orders_by_date = history_orders_by_date or {}

    revenue = total_revenue(orders)
    orders_count = len(orders)
    avg_order_value = revenue / orders_count if orders_count else 0

    previous_revenue = total_revenue(previous_orders)
    previous_orders_count = len(previous_orders)
    previous_avg_order_value = (
        previous_revenue / previous_orders_count if previous_orders_count else 0
    )
    sample_too_small = (
        orders_count < MIN_COMPARISON_ORDERS
        or previous_orders_count < MIN_COMPARISON_ORDERS
    )

    seven_day = build_period_metrics(history_orders_by_date, report_date, 7)
    thirty_day = build_period_metrics(history_orders_by_date, report_date, 30)
    hourly = build_hourly_metrics(orders)

    return {
        "revenue": round(revenue),
        "orders_count": orders_count,
        "avg_order_value": round(avg_order_value),
        "revenue_change_pct": percent_change(revenue, previous_revenue, sample_too_small),
        "orders_change_pct": percent_change(
            orders_count, previous_orders_count, sample_too_small
        ),
        "avg_order_change_pct": percent_change(
            avg_order_value, previous_avg_order_value, sample_too_small
        ),
        "seven_day": {
            "revenue": seven_day["revenue"],
            "orders": seven_day["orders"],
            "avg_order": seven_day["avg_order"],
            "daily_trend": seven_day["daily_trend"],
            "revenue_vs_7d_avg_pct": percent_vs_average(
                revenue, seven_day["daily_avg_revenue"]
            ),
            "orders_vs_7d_avg_pct": percent_vs_average(
                orders_count, seven_day["daily_avg_orders"]
            ),
        },
        "thirty_day": {
            "revenue": thirty_day["revenue"],
            "orders": thirty_day["orders"],
            "avg_order": thirty_day["avg_order"],
            "revenue_vs_30d_avg_pct": percent_vs_average(
                revenue, thirty_day["daily_avg_revenue"]
            ),
            "orders_vs_30d_avg_pct": percent_vs_average(
                orders_count, thirty_day["daily_avg_orders"]
            ),
        },
        "hourly": hourly,
    }


def build_period_metrics(
    history_orders_by_date: dict[str, list[dict[str, Any]]],
    report_date: Date | str | None,
    days: int,
) -> dict[str, Any]:
    dates = period_dates(report_date, days)
    daily_trend = []
    revenue = 0.0
    orders_count = 0

    for day in dates:
        key = str(day)
        day_orders = history_orders_by_date.get(key, [])
        day_revenue = total_revenue(day_orders)
        day_orders_count = len(day_orders)
        revenue += day_revenue
        orders_count += day_orders_count
        daily_trend.append(
            {
                "date": key,
                "revenue": round(day_revenue),
                "orders": day_orders_count,
                "avg_order": round(day_revenue / day_orders_count)
                if day_orders_count
                else 0,
            }
        )

    return {
        "revenue": round(revenue),
        "orders": orders_count,
        "avg_order": round(revenue / orders_count) if orders_count else 0,
        "daily_trend": daily_trend,
        "daily_avg_revenue": revenue / days if days else 0,
        "daily_avg_orders": orders_count / days if days else 0,
    }


def build_hourly_metrics(orders: list[dict[str, Any]]) -> dict[str, Any]:
    hourly_sales = [{"hour": hour, "revenue": 0, "orders": 0} for hour in range(24)]
    for order in orders:
        parsed = order_date(order)
        if not parsed:
            continue
        hour = parsed.hour
        hourly_sales[hour]["revenue"] += round(order_revenue(order))
        hourly_sales[hour]["orders"] += 1

    peak = max(hourly_sales, key=lambda item: (item["revenue"], item["orders"]))
    peak_hour = peak["hour"] if peak["revenue"] > 0 or peak["orders"] > 0 else None
    dead_hours = [
        item["hour"]
        for item in hourly_sales
        if is_selling_hour(item["hour"]) and item["orders"] == 0
    ]

    return {
        "hourly_sales": hourly_sales,
        "peak_hour": peak_hour,
        "dead_hours": dead_hours,
    }


def period_dates(report_date: Date | str | None, days: int) -> list[Date]:
    if report_date is None:
        end_date = Date.today()
    elif isinstance(report_date, Date):
        end_date = report_date
    else:
        end_date = datetime.strptime(str(report_date), "%Y-%m-%d").date()
    start_date = end_date - timedelta(days=days - 1)
    return [start_date + timedelta(days=offset) for offset in range(days)]


def is_selling_hour(hour: int) -> bool:
    return any(start <= hour < end for start, end in SELLING_WINDOWS)


def total_revenue(orders: list[dict[str, Any]]) -> float:
    return sum(order_revenue(order) for order in orders)


def order_revenue(order: dict[str, Any]) -> float:
    return number(order.get("Total") or order.get("TotalPayment"))


def percent_change(current: float, previous: float, sample_too_small: bool) -> float | None:
    if sample_too_small or previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 2)


def percent_vs_average(current: float, average: float) -> float | None:
    if average == 0:
        return None
    return round(((current - average) / average) * 100, 2)


def number(value: Any) -> float:
    try:
        if value in (None, ""):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0
