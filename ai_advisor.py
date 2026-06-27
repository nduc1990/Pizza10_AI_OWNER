"""Generate concise owner advice from the owner decision package."""

from __future__ import annotations

import json
import sys
from typing import Any

from config import settings


AI_NOT_CONFIGURED = "AI chưa cấu hình"
AI_UNAVAILABLE = "AI chưa khả dụng do hết quota hoặc lỗi API."


def generate_ai_advice(snapshot: dict[str, Any]) -> str:
    if not settings.openai_api_key:
        return AI_NOT_CONFIGURED

    try:
        from openai import OpenAI
    except ImportError:
        return AI_NOT_CONFIGURED

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = (
        "Bạn là trợ lý điều hành cho chủ chuỗi Pizza 10 Điểm.\n"
        "Bạn không làm kế toán.\n"
        "Bạn không bịa dữ liệu.\n"
        "Bạn chỉ dựa trên business snapshot và decision package.\n"
        "Viết ngắn, thực dụng, ưu tiên hành động.\n"
        "AI không tính KPI, không tạo rule mới, không bịa số liệu.\n"
        "Chỉ diễn giải: tình hình hôm nay, 3 vấn đề ưu tiên, việc chủ cần làm, "
        "việc giao cho quản lý cửa hàng.\n"
        "Trả về text theo format:\n"
        "TÓM TẮT\n"
        "...\n\n"
        "ƯU TIÊN HÔM NAY\n"
        "1. ...\n"
        "2. ...\n"
        "3. ...\n\n"
        "GIAO VIỆC\n"
        "- Owner: ...\n"
        "- Store Manager: ...\n\n"
        "LƯU Ý\n"
        "..."
    )
    payload = build_ai_payload(snapshot)

    try:
        response = client.responses.create(
            model=settings.ai_model,
            input=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False, indent=2),
                },
            ],
        )
    except Exception as exc:
        log_ai_error(exc)
        return AI_UNAVAILABLE

    return (response.output_text or "").strip() or AI_UNAVAILABLE


def build_ai_payload(snapshot: dict[str, Any]) -> dict[str, Any]:
    rules = snapshot.get("rules") or {}
    return {
        "decision_package": snapshot.get("decision_package"),
        "rules": {
            "all": rules.get("all") or [],
        },
        "sales": snapshot.get("sales"),
        "product_intelligence": snapshot.get("product_intelligence"),
        "finance_intelligence": snapshot.get("finance_intelligence"),
        "inventory_intelligence": snapshot.get("inventory_intelligence"),
    }


def log_ai_error(exc: Exception) -> None:
    status_code = getattr(exc, "status_code", None)
    error_code = getattr(exc, "code", None)
    print(
        f"AI Advisor error: status={status_code} code={error_code} detail={exc!r}",
        file=sys.stderr,
    )
