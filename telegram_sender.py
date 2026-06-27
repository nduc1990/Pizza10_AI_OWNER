"""Telegram delivery for owner reports."""

from __future__ import annotations

import sys
from typing import Any

import requests

from config import settings


def send_telegram_message(text: str) -> None:
    token = settings.telegram_bot_token
    chat_id = settings.telegram_owner_chat_id
    if not token or not chat_id:
        print_console("Telegram chưa cấu hình, chỉ in báo cáo ra console.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    try:
        response = requests.post(url, json=payload, timeout=30)
    except requests.RequestException as exc:
        print_console(f"Không gửi được Telegram: lỗi kết nối - {sanitize_error(exc, token)}")
        return

    if response.ok:
        print_console("Đã gửi Telegram thành công.")
        return

    print_console(
        "Không gửi được Telegram: "
        f"status={response.status_code}, lỗi={shorten(sanitize_text(response.text, token))}"
    )


def print_console(text: str) -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="backslashreplace").decode("ascii"))


def sanitize_error(exc: Exception, token: str) -> str:
    return shorten(sanitize_text(f"{type(exc).__name__}: {exc}", token))


def sanitize_text(text: Any, token: str) -> str:
    safe_text = str(text or "")
    if token:
        safe_text = safe_text.replace(token, "<TELEGRAM_BOT_TOKEN>")
    return safe_text.replace("\r", " ").replace("\n", " ")


def shorten(text: str, limit: int = 300) -> str:
    compact = " ".join(str(text or "").split())
    if len(compact) <= limit:
        return compact
    return compact[:limit].rstrip() + "..."
