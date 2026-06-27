"""Finance Intelligence v1: show where owner money stands."""

from __future__ import annotations

from datetime import date as Date
from datetime import datetime, timedelta
from typing import Any
import unicodedata


DEFAULT_SUPPLIER_NAME = "Kitchen Le"


def build_finance_intelligence(
    supplier_debt: Any = None,
    supplier_name: str = DEFAULT_SUPPLIER_NAME,
    cash: Any = None,
    bank: Any = None,
    purchase_today: Any = None,
    purchase_last_7_days: Any = None,
    purchase_last_30_days: Any = None,
    accounting_transactions: list[dict[str, Any]] | None = None,
    accounting_transaction_groups: list[dict[str, Any]] | None = None,
    accounts_tree: list[dict[str, Any]] | None = None,
    order_stocks: list[dict[str, Any]] | None = None,
    order_stocks_history: list[dict[str, Any]] | None = None,
    report_date: Date | str | None = None,
) -> dict[str, Any]:
    debt = nullable_number(supplier_debt)
    account_lookup = build_account_lookup(accounts_tree or [])
    group_lookup = build_group_lookup(accounting_transaction_groups or [])
    cash_flow = build_cash_flow_metrics(
        accounting_transactions or [],
        account_lookup,
        group_lookup,
        cash,
        bank,
    )
    purchase_metrics = build_purchase_metrics(
        order_stocks or [],
        order_stocks_history or [],
        report_date,
        purchase_today,
        purchase_last_7_days,
        purchase_last_30_days,
    )

    return {
        "cash_position": {
            "cash": cash_flow["cash"],
            "bank": cash_flow["bank"],
            "total_cash": total_cash(cash_flow["cash"], cash_flow["bank"]),
        },
        "cash_flow": cash_flow,
        "total_receipts": cash_flow["total_receipts"],
        "total_payments": cash_flow["total_payments"],
        "net_cash_flow": cash_flow["net_cash_flow"],
        "supplier_payment_today": cash_flow["supplier_payment_today"],
        "supplier": build_supplier_metrics(debt, supplier_name, cash_flow["supplier_payment_today"]),
        "purchase": purchase_metrics,
        "purchase_today": purchase_metrics["today"],
        "purchase_7_days": purchase_metrics["last_7_days"],
        "purchase_30_days": purchase_metrics["last_30_days"],
        "cash_health": build_cash_health(debt, cash_flow["net_cash_flow"]),
    }


def build_cash_flow_metrics(
    transactions: list[dict[str, Any]],
    account_lookup: dict[Any, dict[str, Any]],
    group_lookup: dict[Any, dict[str, Any]],
    fallback_cash: Any = None,
    fallback_bank: Any = None,
) -> dict[str, Any]:
    total_receipts = 0.0
    total_payments = 0.0
    supplier_payment_today = 0.0
    cash_total = nullable_number(fallback_cash)
    bank_total = nullable_number(fallback_bank)
    inferred_cash = 0.0
    inferred_bank = 0.0
    cash_or_bank_found = False

    for row in transactions:
        amount = nullable_number(row.get("Amount"))
        if amount is None:
            continue

        transaction_type = transaction_type_value(row)
        if transaction_type == 1:
            total_receipts += amount
        elif transaction_type == 2:
            total_payments += amount

        account_kind = classify_account(row, account_lookup)
        if account_kind == "cash":
            cash_or_bank_found = True
            inferred_cash += amount if transaction_type == 1 else -amount
        elif account_kind == "bank":
            cash_or_bank_found = True
            inferred_bank += amount if transaction_type == 1 else -amount

        if transaction_type == 2 and is_supplier_payment(row, group_lookup):
            supplier_payment_today += amount

    if cash_or_bank_found:
        cash_total = inferred_cash if cash_total is None else cash_total
        bank_total = inferred_bank if bank_total is None else bank_total

    return {
        "total_receipts": total_receipts,
        "total_payments": total_payments,
        "net_cash_flow": total_receipts - total_payments,
        "cash": cash_total,
        "bank": bank_total,
        "supplier_payment_today": supplier_payment_today,
        "transactions_count": len(transactions),
    }


def build_purchase_metrics(
    order_stocks: list[dict[str, Any]],
    order_stocks_history: list[dict[str, Any]],
    report_date: Date | str | None,
    fallback_today: Any = None,
    fallback_7_days: Any = None,
    fallback_30_days: Any = None,
) -> dict[str, Any]:
    today = sum_money(order_stocks, ("Total", "TotalPayment", "Amount"))
    target_date = parse_report_date(report_date) if report_date else None

    last_7_days = nullable_number(fallback_7_days)
    last_30_days = nullable_number(fallback_30_days)
    if order_stocks_history and target_date:
        last_7_days = sum_purchase_range(order_stocks_history, target_date - timedelta(days=6), target_date)
        last_30_days = sum_purchase_range(order_stocks_history, target_date - timedelta(days=29), target_date)

    return {
        "today": today if order_stocks or fallback_today is None else nullable_number(fallback_today),
        "last_7_days": last_7_days,
        "last_30_days": last_30_days,
        "documents_today": len(order_stocks),
        "documents_history": len(order_stocks_history),
    }


def build_supplier_metrics(
    debt: float | None,
    supplier_name: str,
    supplier_payment_today: float | None = None,
) -> dict[str, Any]:
    status = supplier_health_status(debt)
    supplier_row = {
        "name": supplier_name,
        "debt": debt,
        "status": status,
        "payment_today": supplier_payment_today,
    }
    return {
        "total_supplier_debt": debt,
        "supplier_count": 1 if debt is not None or supplier_payment_today else 0,
        "largest_supplier": supplier_name if debt is not None else None,
        "largest_supplier_debt": debt,
        "supplier_payment_today": supplier_payment_today,
        "supplier_health": [supplier_row] if debt is not None or supplier_payment_today else [],
    }


def build_cash_health(debt: float | None, net_cash_flow: float | None = None) -> dict[str, Any]:
    if debt is None and net_cash_flow is None:
        return {
            "score": None,
            "status": "Unknown",
        }

    score = 100
    status = "Healthy"
    if debt is not None:
        if debt >= 20_000_000:
            score = min(score, 30)
            status = "Critical"
        elif debt >= 10_000_000:
            score = min(score, 60)
            status = "Warning"
        elif debt >= 5_000_000:
            score = min(score, 80)
            status = "Watch"

    if net_cash_flow is not None and net_cash_flow < 0:
        score = min(score, 75)
        if status == "Healthy":
            status = "Watch"

    return {
        "score": score,
        "status": status,
    }


def supplier_health_status(debt: float | None) -> str:
    if debt is None:
        return "Unknown"
    if debt < 5_000_000:
        return "Healthy"
    if debt < 10_000_000:
        return "Watch"
    if debt < 20_000_000:
        return "Warning"
    return "Critical"


def transaction_type_value(row: dict[str, Any]) -> int | None:
    value = row.get("AccountingTransactionType")
    try:
        if value is not None:
            return int(value)
    except (TypeError, ValueError):
        pass

    code = normalize_text(row.get("Code"))
    if code.startswith("pt"):
        return 1
    if code.startswith("pc"):
        return 2
    return None


def is_supplier_payment(row: dict[str, Any], group_lookup: dict[Any, dict[str, Any]]) -> bool:
    text_parts = [
        row.get("Description"),
        row.get("Code"),
        nested_value(row, ("Group", "Name")),
        nested_value(row, ("Partner", "Name")),
    ]
    group_id = row.get("GroupId")
    if group_id in group_lookup:
        text_parts.append(group_lookup[group_id].get("Name"))

    partner = row.get("Partner") if isinstance(row.get("Partner"), dict) else {}
    partner_type = partner.get("Type")
    text = normalize_text(" ".join(str(part or "") for part in text_parts))

    return (
        partner_type == 2
        or "ncc" in text
        or "supplier" in text
        or "purchase" in text
        or "mua hang" in text
        or "tra no" in text
    )


def classify_account(row: dict[str, Any], account_lookup: dict[Any, dict[str, Any]]) -> str | None:
    account = row.get("Account") if isinstance(row.get("Account"), dict) else {}
    account_id = row.get("AccountId") or account.get("Id")
    account_name = account.get("Name") or account.get("Code")
    if account_id in account_lookup:
        found = account_lookup[account_id]
        account_name = account_name or found.get("Name") or found.get("Code")

    text = normalize_text(account_name)
    if not text:
        return None
    if "tien mat" in text or "cash" in text:
        return "cash"
    if "ngan hang" in text or "bank" in text or "chuyen khoan" in text:
        return "bank"
    return None


def build_group_lookup(groups: list[dict[str, Any]]) -> dict[Any, dict[str, Any]]:
    return {group.get("Id"): group for group in groups if group.get("Id") is not None}


def build_account_lookup(accounts_tree: list[dict[str, Any]]) -> dict[Any, dict[str, Any]]:
    lookup: dict[Any, dict[str, Any]] = {}

    def walk(items: list[dict[str, Any]]) -> None:
        for item in items:
            account_id = item.get("Id") or item.get("id")
            if account_id is not None:
                lookup[account_id] = item
            children = (
                item.get("items")
                or item.get("Items")
                or item.get("children")
                or item.get("Children")
                or []
            )
            if isinstance(children, list):
                walk([child for child in children if isinstance(child, dict)])

    walk(accounts_tree)
    return lookup


def sum_purchase_range(rows: list[dict[str, Any]], start: Date, end: Date) -> float:
    total = 0.0
    for row in rows:
        parsed = first_row_date(row, ("DocumentDate", "CreatedDate", "Date"))
        if parsed and start <= parsed <= end:
            total += first_number(row, ("Total", "TotalPayment", "Amount")) or 0
    return total


def sum_money(rows: list[dict[str, Any]], fields: tuple[str, ...]) -> float:
    return sum(first_number(row, fields) or 0 for row in rows)


def first_number(row: dict[str, Any], fields: tuple[str, ...]) -> float | None:
    for field in fields:
        value = nullable_number(row.get(field))
        if value is not None:
            return value
    return None


def first_row_date(row: dict[str, Any], fields: tuple[str, ...]) -> Date | None:
    for field in fields:
        parsed = parse_pos365_datetime(row.get(field))
        if parsed:
            return parsed.date()
    return None


def parse_report_date(value: Date | str) -> Date:
    if isinstance(value, Date):
        return value
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def parse_pos365_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if text.startswith("/Date(") and text.endswith(")/"):
        number = text[6:-2].split("+", 1)[0].split("-", 1)[0]
        try:
            return datetime.fromtimestamp(int(number) / 1000)
        except (TypeError, ValueError, OSError):
            return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:19], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def nested_value(row: dict[str, Any], path: tuple[str, str]) -> Any:
    first = row.get(path[0])
    if isinstance(first, dict):
        return first.get(path[1])
    return None


def total_cash(cash: float | None, bank: float | None) -> float | None:
    if cash is None and bank is None:
        return None
    return (cash or 0) + (bank or 0)


def nullable_number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_text(value: Any) -> str:
    text = str(value or "").replace("đ", "d").replace("Đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return " ".join(text.casefold().split())
