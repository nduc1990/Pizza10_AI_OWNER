"""Rule Engine v2 for structured owner alerts."""

from __future__ import annotations

from typing import Any

from rules.rule_config import RULE_CONFIG


def evaluate_rules(
    snapshot: dict[str, Any], config: dict[str, Any] | None = None
) -> dict[str, list[dict[str, Any]]]:
    cfg = {**RULE_CONFIG, **(config or {})}
    high: list[dict[str, Any]] = []
    medium: list[dict[str, Any]] = []
    low: list[dict[str, Any]] = []

    sales = snapshot.get("sales") or {}
    products = snapshot.get("products") or {}
    product_intelligence = snapshot.get("product_intelligence") or {}
    finance = snapshot.get("finance") or {}
    finance_intelligence = snapshot.get("finance_intelligence") or {}
    inventory_intelligence = snapshot.get("inventory_intelligence") or {}
    seven_day = sales.get("seven_day") or {}
    hourly = sales.get("hourly") or {}

    orders_count = int(number(sales.get("orders_count")))
    avg_order_value = number(sales.get("avg_order_value"))
    revenue_change_pct = nullable_number(sales.get("revenue_change_pct"))
    orders_change_pct = nullable_number(sales.get("orders_change_pct"))
    supplier_debt = nullable_number(finance.get("supplier_debt"))
    top_products = products.get("top_products") or []
    product_dependency = product_intelligence.get("product_dependency") or {}
    cash_health = finance_intelligence.get("cash_health") or {}
    supplier_metrics = finance_intelligence.get("supplier") or {}
    low_stock_items = inventory_intelligence.get("low_stock_items") or []
    overstock_items = inventory_intelligence.get("overstock_items") or []
    stockout_risk = inventory_intelligence.get("stockout_risk") or []
    stock_health_score = nullable_number(inventory_intelligence.get("stock_health_score"))

    if orders_count == 0:
        high.append(
            make_rule(
                "NO_ORDERS",
                "HIGH",
                "Không có đơn hàng",
                "Hôm nay chưa có đơn nào.",
                "orders_count",
                orders_count,
                1,
                "Kiểm tra POS365, ca bán hàng và xác nhận đây có phải ngày test dữ liệu không.",
            )
        )
    elif orders_count < cfg["target_orders_per_day"]:
        medium.append(
            make_rule(
                "LOW_ORDERS",
                "MEDIUM",
                "Số đơn thấp hơn mục tiêu",
                f"Hôm nay có {orders_count} đơn, thấp hơn mục tiêu {cfg['target_orders_per_day']} đơn/ngày.",
                "orders_count",
                orders_count,
                cfg["target_orders_per_day"],
                "Kiểm tra tình hình bán hàng trong khung cao điểm và xác nhận đây có phải ngày test dữ liệu không.",
            )
        )

    if avg_order_value > cfg["high_avg_order_value"]:
        medium.append(
            make_rule(
                "HIGH_AVG_ORDER",
                "MEDIUM",
                "TB/đơn cao bất thường",
                f"TB/đơn là {format_money(avg_order_value)}, cao hơn ngưỡng {format_money(cfg['high_avg_order_value'])}.",
                "avg_order_value",
                round(avg_order_value),
                cfg["high_avg_order_value"],
                "Kiểm tra có đơn sỉ, đơn gộp hoặc dữ liệu nhập sai không.",
            )
        )

    add_drop_rule(
        high,
        medium,
        revenue_change_pct,
        "revenue_change_pct",
        "REVENUE_DROP",
        "Doanh thu giảm mạnh",
        cfg["revenue_drop_high_pct"],
        cfg["revenue_drop_medium_pct"],
        "So sánh doanh thu với ngày liền trước và kiểm tra nguyên nhân giảm theo khung giờ.",
    )
    add_drop_rule(
        high,
        medium,
        orders_change_pct,
        "orders_change_pct",
        "ORDERS_DROP",
        "Số đơn giảm mạnh",
        cfg["orders_drop_high_pct"],
        cfg["orders_drop_medium_pct"],
        "Kiểm tra traffic bán hàng, kênh đặt đơn và hoạt động trong khung cao điểm.",
    )

    revenue_vs_7d_avg_pct = nullable_number(seven_day.get("revenue_vs_7d_avg_pct"))
    if (
        revenue_vs_7d_avg_pct is not None
        and revenue_vs_7d_avg_pct <= cfg["revenue_below_7d_avg_pct"]
    ):
        medium.append(
            make_rule(
                "REVENUE_BELOW_7D_AVG",
                "MEDIUM",
                "Doanh thu thấp hơn TB 7 ngày",
                f"Doanh thu hôm nay thấp hơn TB 7 ngày {format_pct(abs(revenue_vs_7d_avg_pct))}.",
                "revenue_vs_7d_avg_pct",
                revenue_vs_7d_avg_pct,
                cfg["revenue_below_7d_avg_pct"],
                "So sánh doanh thu theo khung giờ và kiểm tra kênh bán hàng chính.",
            )
        )

    orders_vs_7d_avg_pct = nullable_number(seven_day.get("orders_vs_7d_avg_pct"))
    if (
        orders_vs_7d_avg_pct is not None
        and orders_vs_7d_avg_pct <= cfg["orders_below_7d_avg_pct"]
    ):
        medium.append(
            make_rule(
                "ORDERS_BELOW_7D_AVG",
                "MEDIUM",
                "Số đơn thấp hơn TB 7 ngày",
                f"Số đơn hôm nay thấp hơn TB 7 ngày {format_pct(abs(orders_vs_7d_avg_pct))}.",
                "orders_vs_7d_avg_pct",
                orders_vs_7d_avg_pct,
                cfg["orders_below_7d_avg_pct"],
                "Kiểm tra lượng khách trong khung cao điểm và các kênh nhận đơn.",
            )
        )

    hourly_sales = hourly.get("hourly_sales") or []
    if not has_orders_in_window(
        hourly_sales, cfg["morning_peak_start"], cfg["morning_peak_end"]
    ):
        high.append(
            make_rule(
                "NO_PEAK_HOUR_SALES",
                "HIGH",
                "Không có đơn trong cao điểm sáng",
                "Khung 05:00-08:00 không có đơn hàng.",
                "morning_peak_orders",
                0,
                1,
                "Kiểm tra ca mở bán, kênh nhận đơn buổi sáng và dữ liệu đồng bộ POS365.",
            )
        )

    if not has_orders_in_window(
        hourly_sales, cfg["afternoon_shift_start"], cfg["afternoon_shift_end"]
    ):
        medium.append(
            make_rule(
                "DEAD_SHIFT",
                "MEDIUM",
                "Ca chiều không có đơn",
                "Cả ca 15:00-20:00 không có đơn hàng.",
                "afternoon_shift_orders",
                0,
                1,
                "Kiểm tra tình hình mở bán ca chiều và các kênh đặt đơn.",
            )
        )

    if top_products:
        top_product = top_products[0]
        share_pct = nullable_number(top_product.get("share_pct"))
        if share_pct is not None and share_pct > cfg["top_product_share_warning"]:
            low.append(
                make_rule(
                    "TOP_PRODUCT_DEPENDENCY",
                    "LOW",
                    "Phụ thuộc món bán chạy",
                    f"{top_product.get('name')} chiếm {format_pct(share_pct)} doanh thu.",
                    "top_product_share_pct",
                    share_pct,
                    cfg["top_product_share_warning"],
                    "Theo dõi tồn kho món bán chạy và đẩy thêm combo/món bổ trợ để giảm phụ thuộc.",
                )
            )

    top3_share = nullable_number(product_dependency.get("top3_revenue_share_pct"))
    if top3_share is not None and top3_share > 80:
        medium.append(
            make_rule(
                "MENU_DEPENDENCY",
                "MEDIUM",
                "Menu phụ thuộc vào top 3 món",
                f"Top 3 món chiếm {format_pct(top3_share)} doanh thu.",
                "top3_revenue_share_pct",
                top3_share,
                80,
                "Kiểm tra rủi ro thiếu hàng nhóm bán chạy và thử đẩy combo/món bổ trợ để phân tán doanh thu.",
            )
        )

    if supplier_debt is not None:
        if supplier_debt > cfg["supplier_debt_high"]:
            high.append(
                make_rule(
                    "SUPPLIER_DEBT_HIGH",
                    "HIGH",
                    "Công nợ NCC rất cao",
                    f"Công nợ NCC là {format_money(supplier_debt)}, vượt ngưỡng {format_money(cfg['supplier_debt_high'])}.",
                    "supplier_debt",
                    round(supplier_debt),
                    cfg["supplier_debt_high"],
                    "Ưu tiên đối soát công nợ NCC và lập kế hoạch thanh toán.",
                )
            )
        elif supplier_debt > cfg["supplier_debt_medium"]:
            medium.append(
                make_rule(
                    "SUPPLIER_DEBT_MEDIUM",
                    "MEDIUM",
                    "Công nợ NCC vượt ngưỡng",
                    f"Công nợ NCC là {format_money(supplier_debt)}, vượt ngưỡng {format_money(cfg['supplier_debt_medium'])}.",
                    "supplier_debt",
                    round(supplier_debt),
                    cfg["supplier_debt_medium"],
                    "Kiểm tra lịch thanh toán NCC và dòng tiền trong ngày.",
                )
            )

    supplier_status = supplier_health_status(supplier_metrics)
    supplier_debt_value = nullable_number(supplier_metrics.get("total_supplier_debt"))
    if supplier_status == "Critical":
        high.append(
            make_rule(
                "SUPPLIER_HEALTH_CRITICAL",
                "HIGH",
                "Supplier health critical",
                f"Công nợ NCC ở mức Critical: {format_money(supplier_debt_value)}.",
                "supplier_health",
                supplier_status,
                "Critical",
                "Ưu tiên kiểm tra công nợ NCC và kế hoạch thanh toán ngay.",
            )
        )
    elif supplier_status == "Warning":
        medium.append(
            make_rule(
                "SUPPLIER_HEALTH_WARNING",
                "MEDIUM",
                "Supplier health warning",
                f"Công nợ NCC ở mức Warning: {format_money(supplier_debt_value)}.",
                "supplier_health",
                supplier_status,
                "Warning",
                "Theo dõi công nợ NCC và chuẩn bị lịch thanh toán phù hợp.",
            )
        )

    cash_score = nullable_number(cash_health.get("score"))
    if cash_score is not None and cash_score < 80:
        medium.append(
            make_rule(
                "LOW_CASH_HEALTH",
                "MEDIUM",
                "Cash health thấp",
                f"Cash Health Score là {cash_score:g}/100.",
                "cash_health_score",
                cash_score,
                80,
                "Kiểm tra tiền mặt, ngân hàng và công nợ NCC để tránh thiếu dòng tiền.",
            )
        )

    if low_stock_items:
        medium.append(
            make_rule(
                "LOW_STOCK",
                "MEDIUM",
                "Có mặt hàng tồn thấp",
                f"Có {len(low_stock_items)} mặt hàng tồn thấp.",
                "low_stock_items",
                len(low_stock_items),
                0,
                "Kiểm tra tồn kho các mặt hàng bán chạy và kế hoạch nhập hàng.",
            )
        )

    if stockout_risk:
        high.append(
            make_rule(
                "OUT_OF_STOCK",
                "HIGH",
                "Có nguy cơ hết hàng",
                f"Có {len(stockout_risk)} mặt hàng có nguy cơ hết hàng.",
                "stockout_risk",
                len(stockout_risk),
                0,
                "Ưu tiên kiểm tra tồn kho thực tế và kế hoạch bổ sung hàng.",
            )
        )

    if overstock_items:
        low.append(
            make_rule(
                "OVERSTOCK",
                "LOW",
                "Có mặt hàng tồn cao",
                f"Có {len(overstock_items)} mặt hàng tồn cao.",
                "overstock_items",
                len(overstock_items),
                0,
                "Theo dõi tốc độ bán và tránh nhập thêm các mặt hàng đang tồn cao.",
            )
        )

    if stock_health_score is not None and stock_health_score < 70:
        medium.append(
            make_rule(
                "LOW_STOCK_HEALTH",
                "MEDIUM",
                "Stock health thấp",
                f"Stock Health Score là {stock_health_score:g}/100.",
                "stock_health_score",
                stock_health_score,
                70,
                "Kiểm tra nhóm hàng tồn thấp và nguy cơ hết hàng.",
            )
        )

    all_rules = high + medium + low
    return {
        "high": high,
        "medium": medium,
        "low": low,
        "all": all_rules,
    }


def add_drop_rule(
    high: list[dict[str, Any]],
    medium: list[dict[str, Any]],
    value: float | None,
    metric: str,
    code_prefix: str,
    title: str,
    high_threshold: float,
    medium_threshold: float,
    suggested_action: str,
) -> None:
    if value is None:
        return
    if value <= high_threshold:
        high.append(
            make_rule(
                f"{code_prefix}_HIGH",
                "HIGH",
                title,
                f"{title} {format_pct(value)} so với ngày trước.",
                metric,
                value,
                high_threshold,
                suggested_action,
            )
        )
    elif value <= medium_threshold:
        medium.append(
            make_rule(
                f"{code_prefix}_MEDIUM",
                "MEDIUM",
                title,
                f"{title} {format_pct(value)} so với ngày trước.",
                metric,
                value,
                medium_threshold,
                suggested_action,
            )
        )


def make_rule(
    code: str,
    severity: str,
    title: str,
    message: str,
    metric: str,
    value: Any,
    threshold: Any,
    suggested_action: str,
) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "title": title,
        "message": message,
        "metric": metric,
        "value": value,
        "threshold": threshold,
        "suggested_action": suggested_action,
    }


def has_orders_in_window(
    hourly_sales: list[dict[str, Any]], start_hour: int, end_hour: int
) -> bool:
    for row in hourly_sales:
        hour = int(number(row.get("hour")))
        if start_hour <= hour < end_hour and number(row.get("orders")) > 0:
            return True
    return False


def supplier_health_status(supplier_metrics: dict[str, Any]) -> str | None:
    health_rows = supplier_metrics.get("supplier_health") or []
    if health_rows:
        return health_rows[0].get("status")
    return None


def nullable_number(value: Any) -> float | None:
    if value is None:
        return None
    return number(value)


def number(value: Any) -> float:
    try:
        if value in (None, ""):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def format_money(value: Any) -> str:
    return f"{int(round(number(value))):,}".replace(",", ".") + "đ"


def format_pct(value: Any) -> str:
    return f"{number(value):g}%"
