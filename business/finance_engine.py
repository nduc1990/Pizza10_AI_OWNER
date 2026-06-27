"""Finance metrics for owner reporting."""

from __future__ import annotations

from typing import Any


def build_finance_metrics(supplier_debt: Any = None) -> dict[str, Any]:
    return {
        "supplier_debt": supplier_debt,
        "cash": None,
        "bank": None,
        "purchase_today": None,
        "payment_to_supplier": None,
    }
