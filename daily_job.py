"""Daily owner report job for Pizza 10 Điểm."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date as Date
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ai_advisor import AI_NOT_CONFIGURED, generate_ai_advice
from business.business_snapshot import build_business_snapshot
from config import settings
from decision.decision_engine import build_decision_package
from fetch_pos365 import Pos365Client, order_date
from rules.rule_engine import evaluate_rules, make_rule
from telegram_sender import print_console, send_telegram_message


def main() -> None:
    configure_console_encoding()
    args = parse_args()
    report_date = parse_cli_date(args.date)
    previous_date = report_date - timedelta(days=1)

    products: list[dict[str, Any]] = []
    orders: list[dict[str, Any]] = []
    order_details: list[dict[str, Any]] = []
    previous_orders: list[dict[str, Any]] = []
    previous_order_details: list[dict[str, Any]] = []
    history_orders_by_date = build_empty_history(report_date, 30)
    history_order_details_by_date = build_empty_history(report_date, 30)

    fetch_error = None
    try:
        client = Pos365Client(
            settings.pos365_base_url,
            settings.pos365_username,
            settings.pos365_password,
        )
        client.authenticate()
        products = client.get_products()
        orders = client.get_orders(report_date)
        order_details = fetch_details(client, orders)
        previous_orders = client.get_orders(previous_date)
        previous_order_details = fetch_details(client, previous_orders)
        history_orders = client.get_orders_range(
            report_date - timedelta(days=29), report_date
        )
        history_orders_by_date = group_orders_by_date(history_orders, report_date, 30)
        history_order_details_by_date = fetch_history_details_by_date(
            client, history_orders_by_date
        )
    except Exception as exc:
        fetch_error = str(exc)

    snapshot = build_business_snapshot(
        report_date,
        orders,
        order_details,
        products,
        previous_orders,
        previous_order_details,
        history_orders_by_date,
        history_order_details_by_date,
    )
    snapshot["rules"] = evaluate_rules(snapshot)
    if fetch_error:
        rule = make_rule(
            "POS365_FETCH_ERROR",
            "HIGH",
            "Chưa lấy được dữ liệu POS365",
            fetch_error,
            "pos365_fetch",
            None,
            "success",
            "Kiểm tra kết nối POS365, thông tin đăng nhập và chứng chỉ HTTPS.",
        )
        snapshot["rules"]["high"].append(rule)
        snapshot["rules"]["all"] = (
            snapshot["rules"]["high"]
            + snapshot["rules"]["medium"]
            + snapshot["rules"]["low"]
        )
    snapshot["decision_package"] = build_decision_package(snapshot)

    ai_text = generate_ai_advice(snapshot)
    if not args.no_save:
        save_daily_report(snapshot, ai_text)

    final_text = (
        format_owner_brief(snapshot, ai_text)
        if args.brief
        else format_owner_report(snapshot, ai_text)
    )
    print_console(final_text)
    if args.send:
        send_telegram_message(final_text)


def fetch_details(client: Pos365Client, orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    for order in orders:
        order_id = order.get("Id") or order.get("ID") or order.get("OrderId")
        if not order_id:
            continue
        for row in client.get_order_detail(order_id):
            row["OrderId"] = order_id
            details.append(row)
    return details


def build_empty_history(report_date: Date, days: int) -> dict[str, list[dict[str, Any]]]:
    start_date = report_date - timedelta(days=days - 1)
    return {
        str(start_date + timedelta(days=offset)): []
        for offset in range(days)
    }


def group_orders_by_date(
    orders: list[dict[str, Any]], report_date: Date, days: int
) -> dict[str, list[dict[str, Any]]]:
    grouped = build_empty_history(report_date, days)
    for order in orders:
        parsed = order_date(order)
        if not parsed:
            continue
        key = str(parsed.date())
        if key in grouped:
            grouped[key].append(order)
    return grouped


def fetch_history_details_by_date(
    client: Pos365Client, history_orders_by_date: dict[str, list[dict[str, Any]]]
) -> dict[str, list[dict[str, Any]]]:
    return {
        day: fetch_details(client, orders)
        for day, orders in history_orders_by_date.items()
    }


def configure_console_encoding() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Pizza 10 Điểm owner report.")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD, yesterday, or blank for today")
    parser.add_argument("--no-save", action="store_true", help="Do not save JSON report")
    parser.add_argument("--brief", action="store_true", help="Send a short owner brief")
    parser.add_argument("--send", action="store_true", help="Send the report to Telegram")
    return parser.parse_args()


def parse_cli_date(value: str | None) -> Date:
    if not value:
        return Date.today()
    if value.lower() == "yesterday":
        return Date.today() - timedelta(days=1)
    return datetime.strptime(value, "%Y-%m-%d").date()


def format_owner_report(snapshot: dict[str, Any], ai_text: str) -> str:
    report_date = datetime.strptime(snapshot["report_date"], "%Y-%m-%d").strftime("%d/%m/%Y")
    sales = snapshot["sales"]
    products = snapshot["products"]
    product_intelligence = snapshot.get("product_intelligence") or {}
    finance_intelligence = snapshot.get("finance_intelligence") or {}
    inventory_intelligence = snapshot.get("inventory_intelligence") or {}
    decision_package = snapshot.get("decision_package") or {}
    rules = snapshot.get("rules") or {"high": [], "medium": [], "low": []}

    lines = [
        "🍕 PIZZA 10 ĐIỂM - OWNER REPORT",
        f"Ngày: {report_date}",
        "",
        "📊 SALES",
        f"Doanh thu: {money(sales['revenue'])}{change(sales['revenue_change_pct'])}",
        f"Số đơn: {sales['orders_count']}{change(sales['orders_change_pct'])}",
        f"TB/đơn: {money(sales['avg_order_value'])}{change(sales['avg_order_change_pct'])}",
        "",
        "📈 XU HƯỚNG",
        format_trend_line("7 ngày", sales.get("seven_day") or {}),
        format_trend_line("30 ngày", sales.get("thirty_day") or {}),
        format_vs_average(sales),
        "",
        "🕒 THEO GIỜ",
        format_hourly(sales.get("hourly") or {}),
        "",
        "🍕 MENU HEALTH",
        format_menu_health(product_intelligence),
        "",
        "💰 FINANCE",
        format_finance(finance_intelligence),
        "",
        "📦 INVENTORY",
        format_inventory(inventory_intelligence),
        "",
        "🎯 TODAY'S PRIORITIES",
        *format_priorities(decision_package),
        "",
        "🔥 TOP MÓN",
    ]

    top_products = products.get("top_products") or []
    if top_products:
        for index, item in enumerate(top_products[:5], start=1):
            share = f" - {item['share_pct']:g}%" if item.get("share_pct") is not None else ""
            lines.append(
                f"{index}. {item['name']} - {item['qty']} - {money(item['revenue'])}{share}"
            )
    else:
        lines.append("- Chưa có dữ liệu món bán.")

    lines.extend(["", "⚠ CẢNH BÁO"])
    has_rules = False
    for level in ("high", "medium", "low"):
        messages = rules.get(level) or []
        if not messages:
            continue
        has_rules = True
        lines.append(f"{level.upper()}:")
        lines.extend(format_rule(message) for message in messages)
        lines.append("")
    if not has_rules:
        lines.append("Không có cảnh báo đáng chú ý.")
    elif lines[-1] == "":
        lines.pop()

    lines.extend(["", "🤖 AI ADVISOR", limit_ai_section(ai_text)])
    return "\n".join(lines)


def format_owner_brief(snapshot: dict[str, Any], ai_text: str) -> str:
    report_date = datetime.strptime(snapshot["report_date"], "%Y-%m-%d").strftime("%d/%m/%Y")
    sales = snapshot["sales"]
    decision_package = snapshot.get("decision_package") or {}
    rules = snapshot.get("rules") or {"high": [], "medium": [], "low": []}

    lines = [
        f"🍕 OWNER BRIEF - {report_date}",
        "",
        "📊 Kết quả",
        f"Doanh thu: {money(sales['revenue'])}",
        f"Số đơn: {sales['orders_count']}",
        f"AOV: {money(sales['avg_order_value'])}",
        "",
        "🎯 Ưu tiên hôm nay",
        *format_priorities(decision_package),
        "",
        "⚠ Cảnh báo chính",
        *format_brief_warnings(rules),
        "",
        "🤖 AI Advisor",
        format_brief_ai(ai_text),
    ]
    return "\n".join(lines)


def limit_ai_section(ai_text: str, max_chars: int = 1200) -> str:
    text = (ai_text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def format_brief_ai(ai_text: str) -> str:
    text = (ai_text or "").strip()
    if text == AI_NOT_CONFIGURED:
        return "AI Advisor: chưa cấu hình."
    return limit_ai_section(text)


def format_brief_warnings(rules: dict[str, Any], limit: int = 2) -> list[str]:
    warnings: list[str] = []
    for level in ("high", "medium", "low"):
        for rule in rules.get(level) or []:
            warnings.append(format_rule(rule))
            if len(warnings) >= limit:
                return warnings
    return ["- Không có cảnh báo đáng chú ý."]


def save_daily_report(snapshot: dict[str, Any], ai_text: str) -> Path:
    reports_dir = Path(__file__).resolve().parent / "data" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    report_date = snapshot["report_date"]
    report = {
        "report_date": report_date,
        "store": snapshot.get("store"),
        "sales": snapshot.get("sales"),
        "products": snapshot.get("products"),
        "product_intelligence": snapshot.get("product_intelligence"),
        "finance": snapshot.get("finance"),
        "finance_intelligence": snapshot.get("finance_intelligence"),
        "inventory_intelligence": snapshot.get("inventory_intelligence"),
        "decision_package": snapshot.get("decision_package"),
        "rules": snapshot.get("rules"),
        "ai_advice": ai_text,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }

    output_path = reports_dir / f"{report_date}.json"
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def money(value: Any) -> str:
    amount = int(round(float(value or 0)))
    return f"{amount:,}".replace(",", ".") + "đ"


def format_trend_line(label: str, period: dict[str, Any]) -> str:
    return (
        f"{label}: doanh thu {money(period.get('revenue', 0))}, "
        f"đơn {period.get('orders', 0)}, "
        f"TB/đơn {money(period.get('avg_order', 0))}"
    )


def format_vs_average(sales: dict[str, Any]) -> str:
    seven_day = sales.get("seven_day") or {}
    thirty_day = sales.get("thirty_day") or {}
    return (
        "So với TB: "
        f"7 ngày DT {pct(seven_day.get('revenue_vs_7d_avg_pct'))}, "
        f"đơn {pct(seven_day.get('orders_vs_7d_avg_pct'))}; "
        f"30 ngày DT {pct(thirty_day.get('revenue_vs_30d_avg_pct'))}, "
        f"đơn {pct(thirty_day.get('orders_vs_30d_avg_pct'))}"
    )


def format_hourly(hourly: dict[str, Any]) -> str:
    peak_hour = hourly.get("peak_hour")
    dead_hours = hourly.get("dead_hours") or []
    peak_text = f"{int(peak_hour):02d}:00" if peak_hour is not None else "N/A"
    dead_text = ", ".join(f"{int(hour):02d}:00" for hour in dead_hours[:8])
    if len(dead_hours) > 8:
        dead_text += f" (+{len(dead_hours) - 8})"
    if not dead_text:
        dead_text = "Không có"
    return f"Giờ cao nhất: {peak_text}; Giờ chết: {dead_text}"


def format_menu_health(product_intelligence: dict[str, Any]) -> str:
    abc = product_intelligence.get("abc_analysis") or {"A": [], "B": [], "C": []}
    dependency = product_intelligence.get("product_dependency") or {}
    slow_moving = product_intelligence.get("slow_moving_products") or []
    score = product_intelligence.get("menu_health_score", 0)
    top3 = dependency.get("top3_revenue_share_pct", 0)
    return (
        f"Score: {score}/100; "
        f"ABC: A {len(abc.get('A', []))}, B {len(abc.get('B', []))}, C {len(abc.get('C', []))}; "
        f"Top3 chiếm {share_pct(top3)}; "
        f"Slow Moving: {len(slow_moving)}"
    )


def format_finance(finance_intelligence: dict[str, Any]) -> str:
    cash_health = finance_intelligence.get("cash_health") or {}
    supplier = finance_intelligence.get("supplier") or {}
    supplier_rows = supplier.get("supplier_health") or []

    score = cash_health.get("score")
    cash_status = cash_health.get("status") or "Unknown"
    score_text = "N/A" if score is None else f"{score:g}/100"

    if supplier_rows:
        first_supplier = supplier_rows[0]
        supplier_name = first_supplier.get("name") or "N/A"
        supplier_debt = money(first_supplier.get("debt"))
        supplier_status = first_supplier.get("status") or "Unknown"
    else:
        supplier_name = "N/A"
        supplier_debt = "N/A"
        supplier_status = "Unknown"

    return (
        f"Cash Health: {score_text} - {cash_status}; "
        f"Supplier Health: {supplier_name} - {supplier_debt} - {supplier_status}"
    )


def format_inventory(inventory_intelligence: dict[str, Any]) -> str:
    score = inventory_intelligence.get("stock_health_score")
    score_text = "N/A" if score is None else f"{score:g}/100"
    inventory_value = inventory_intelligence.get("inventory_value")
    value_text = "N/A" if inventory_value is None else money(inventory_value)
    low_stock = inventory_intelligence.get("low_stock_items") or []
    stockout_risk = inventory_intelligence.get("stockout_risk") or []
    status = inventory_intelligence.get("status") or "Unknown"
    return (
        f"Health: {score_text} - {status}; "
        f"Stock Value: {value_text}; "
        f"Low Stock: {len(low_stock)}; "
        f"Stockout Risk: {len(stockout_risk)}"
    )


def format_priorities(decision_package: dict[str, Any]) -> list[str]:
    priorities = decision_package.get("top_priorities") or []
    if not priorities:
        return ["Không có vấn đề nghiêm trọng cần xử lý hôm nay."]
    return [
        (
            f"{item['rank']}. {item['title']} "
            f"({item['category']} / {item['owner']} / score {item['score']}): "
            f"{item['reason']}"
        )
        for item in priorities[:3]
    ]


def change(value: float | None) -> str:
    if value is None:
        return " (N/A)"
    sign = "+" if value > 0 else ""
    return f" ({sign}{value:g}%)"


def pct(value: Any) -> str:
    if value is None:
        return "N/A"
    numeric = float(value)
    sign = "+" if numeric > 0 else ""
    return f"{sign}{numeric:g}%"


def share_pct(value: Any) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):g}%"


def format_rule(rule: Any) -> str:
    if isinstance(rule, dict):
        return f"- {rule.get('title')}: {rule.get('message')}"
    return f"- {rule}"


if __name__ == "__main__":
    main()
