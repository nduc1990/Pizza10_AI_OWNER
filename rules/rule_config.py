"""Default thresholds for Rule Engine v2."""

RULE_CONFIG = {
    "target_orders_per_day": 50,
    "high_avg_order_value": 200000,
    "supplier_debt_medium": 10000000,
    "supplier_debt_high": 20000000,
    "top_product_share_warning": 50,
    "revenue_drop_medium_pct": -20,
    "revenue_drop_high_pct": -35,
    "orders_drop_medium_pct": -15,
    "orders_drop_high_pct": -30,
    "revenue_below_7d_avg_pct": -20,
    "orders_below_7d_avg_pct": -20,
    "morning_peak_start": 5,
    "morning_peak_end": 8,
    "afternoon_shift_start": 15,
    "afternoon_shift_end": 20,
}
