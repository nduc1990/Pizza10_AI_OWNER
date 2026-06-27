"""Finance Intelligence v1: show where owner money stands."""

from __future__ import annotations

from typing import Any


DEFAULT_SUPPLIER_NAME = "Kitchen Lê"


def build_finance_intelligence(
    supplier_debt: Any = None,
    supplier_name: str = DEFAULT_SUPPLIER_NAME,
    cash: Any = None,
    bank: Any = None,
    purchase_today: Any = None,
    purchase_last_7_days: Any = None,
    purchase_last_30_days: Any = None,
) -> dict[str, Any]:
    debt = nullable_number(supplier_debt)
    cash_value = nullable_number(cash)
    bank_value = nullable_number(bank)

    return {
        "cash_position": {
            "cash": cash_value,
            "bank": bank_value,
            "total_cash": total_cash(cash_value, bank_value),
        },
        "supplier": build_supplier_metrics(debt, supplier_name),
        "purchase": {
            "today": nullable_number(purchase_today),
            "last_7_days": nullable_number(purchase_last_7_days),
            "last_30_days": nullable_number(purchase_last_30_days),
        },
        "cash_health": build_cash_health(debt),
    }


def build_supplier_metrics(debt: float | None, supplier_name: str) -> dict[str, Any]:
    status = supplier_health_status(debt)
    supplier_row = {
        "name": supplier_name,
        "debt": debt,
        "status": status,
    }
    return {
        "total_supplier_debt": debt,
        "supplier_count": 1 if debt is not None else 0,
        "largest_supplier": supplier_name if debt is not None else None,
        "largest_supplier_debt": debt,
        "supplier_health": [supplier_row] if debt is not None else [],
    }


def build_cash_health(debt: float | None) -> dict[str, Any]:
    if debt is None:
        return {
            "score": None,
            "status": "Unknown",
        }
    if debt == 0:
        return {
            "score": 100,
            "status": "Không có công nợ",
        }
    if debt < 5_000_000:
        return {
            "score": 95,
            "status": "Healthy",
        }
    if debt < 10_000_000:
        return {
            "score": 80,
            "status": "Watch",
        }
    if debt < 20_000_000:
        return {
            "score": 60,
            "status": "Warning",
        }
    return {
        "score": 30,
        "status": "Critical",
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
