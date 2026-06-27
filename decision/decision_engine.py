"""Decision Engine v1: rank owner priorities from snapshot rules."""

from __future__ import annotations

from typing import Any


SEVERITY_SCORE = {
    "HIGH": 100,
    "MEDIUM": 60,
    "LOW": 20,
}

CATEGORY_OWNER = {
    "Sales": "Store Manager",
    "Finance": "Owner",
    "Inventory": "Store Manager",
    "Product": "Owner",
    "Operations": "Store Manager",
}

RULE_CATEGORY = {
    "NO_ORDERS": "Sales",
    "LOW_ORDERS": "Sales",
    "HIGH_AVG_ORDER": "Sales",
    "REVENUE_DROP_HIGH": "Sales",
    "REVENUE_DROP_MEDIUM": "Sales",
    "ORDERS_DROP_HIGH": "Sales",
    "ORDERS_DROP_MEDIUM": "Sales",
    "REVENUE_BELOW_7D_AVG": "Sales",
    "ORDERS_BELOW_7D_AVG": "Sales",
    "TOP_PRODUCT_DEPENDENCY": "Product",
    "MENU_DEPENDENCY": "Product",
    "SUPPLIER_DEBT_HIGH": "Finance",
    "SUPPLIER_DEBT_MEDIUM": "Finance",
    "SUPPLIER_HEALTH_WARNING": "Finance",
    "SUPPLIER_HEALTH_CRITICAL": "Finance",
    "LOW_CASH_HEALTH": "Finance",
    "LOW_STOCK": "Inventory",
    "OUT_OF_STOCK": "Inventory",
    "OVERSTOCK": "Inventory",
    "LOW_STOCK_HEALTH": "Inventory",
    "NO_PEAK_HOUR_SALES": "Operations",
    "DEAD_SHIFT": "Operations",
    "POS365_FETCH_ERROR": "Operations",
}

CATEGORY_TITLE = {
    "Sales": "Khôi phục nhịp bán hàng",
    "Finance": "Kiểm tra dòng tiền và công nợ",
    "Inventory": "Kiểm tra tồn kho rủi ro",
    "Product": "Kiểm tra sức khỏe menu",
    "Operations": "Kiểm tra vận hành trong ngày",
}


def build_decision_package(snapshot: dict[str, Any]) -> dict[str, Any]:
    rules = snapshot.get("rules") or {}
    all_rules = rules.get("all") or []
    grouped: dict[str, dict[str, Any]] = {}

    for rule in all_rules:
        category = rule_category(rule)
        severity = str(rule.get("severity") or "").upper()
        score = SEVERITY_SCORE.get(severity, 0)
        entry = grouped.setdefault(
            category,
            {
                "category": category,
                "score": 0,
                "owner": CATEGORY_OWNER.get(category, "Store Manager"),
                "rules": [],
            },
        )
        entry["score"] += score
        entry["rules"].append(rule)

    ranked = sorted(
        grouped.values(),
        key=lambda item: (item["score"], highest_rule_score(item["rules"])),
        reverse=True,
    )
    top_priorities = [
        build_priority(index, item)
        for index, item in enumerate(ranked[:3], start=1)
    ]

    return {
        "top_priorities": top_priorities,
        "summary": {
            "highest_priority": top_priorities[0]["category"] if top_priorities else None,
            "total_high": len(rules.get("high") or []),
            "total_medium": len(rules.get("medium") or []),
            "total_low": len(rules.get("low") or []),
        },
    }


def build_priority(rank: int, item: dict[str, Any]) -> dict[str, Any]:
    rules = item["rules"]
    leading_rule = sorted(
        rules,
        key=lambda rule: SEVERITY_SCORE.get(str(rule.get("severity") or "").upper(), 0),
        reverse=True,
    )[0]
    category = item["category"]
    return {
        "rank": rank,
        "category": category,
        "score": item["score"],
        "owner": item["owner"],
        "title": CATEGORY_TITLE.get(category, leading_rule.get("title")),
        "reason": leading_rule.get("message") or leading_rule.get("title"),
    }


def rule_category(rule: dict[str, Any]) -> str:
    code = str(rule.get("code") or "")
    if code in RULE_CATEGORY:
        return RULE_CATEGORY[code]
    metric = str(rule.get("metric") or "")
    if "supplier" in metric or "cash" in metric:
        return "Finance"
    if "stock" in metric or "inventory" in metric:
        return "Inventory"
    if "product" in metric or "menu" in metric:
        return "Product"
    if "hour" in metric or "shift" in metric or "pos365" in metric:
        return "Operations"
    return "Sales"


def highest_rule_score(rules: list[dict[str, Any]]) -> int:
    if not rules:
        return 0
    return max(
        SEVERITY_SCORE.get(str(rule.get("severity") or "").upper(), 0)
        for rule in rules
    )
