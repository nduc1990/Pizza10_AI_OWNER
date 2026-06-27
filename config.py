"""Configuration for Pizza10 AI Owner reporting."""

from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> bool:
        return False


load_dotenv()


@dataclass(frozen=True)
class Settings:
    pos365_base_url: str = os.getenv("POS365_BASE_URL", "https://pizza10.pos365.vn").rstrip("/")
    pos365_username: str = os.getenv("POS365_USERNAME", "")
    pos365_password: str = os.getenv("POS365_PASSWORD", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    ai_model: str = os.getenv("AI_MODEL", "gpt-4o-mini")
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_owner_chat_id: str = os.getenv("TELEGRAM_OWNER_CHAT_ID", "")


settings = Settings()
