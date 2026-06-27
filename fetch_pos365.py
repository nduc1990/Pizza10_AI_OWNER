"""Read-only POS365 API client for owner reporting."""

from __future__ import annotations

from datetime import date as Date
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


CA_BUNDLE_PATH = Path(__file__).resolve().parent / "certs" / "pos365_ca_bundle.pem"


class Pos365Client:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.timeout = 30
        self.verify = str(CA_BUNDLE_PATH) if CA_BUNDLE_PATH.exists() else True
        self.authenticated = False

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        response = self.session.get(
            url, params=params or {}, timeout=self.timeout, verify=self.verify
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _results(payload: dict[str, Any]) -> list[dict[str, Any]]:
        results = payload.get("results")
        if isinstance(results, list):
            return results
        if isinstance(payload, list):
            return payload
        return []

    def authenticate(self) -> None:
        if not self.username or not self.password:
            raise ValueError("Thiếu POS365_USERNAME hoặc POS365_PASSWORD trong .env")

        params = {
            "UserName": self.username,
            "Password": self.password,
            "RememberMe": "true",
        }
        self._get("/api/json/reply/Authenticate", params)
        self.authenticated = True

    def get_products(self) -> list[dict[str, Any]]:
        payload = self._get("/api/json/reply/ProductList", {"Take": 1000})
        return self._results(payload)

    def get_orders(self, date: Date | str) -> list[dict[str, Any]]:
        target_date = parse_report_date(date)
        payload = self._get("/api/json/reply/OrderList", {"Take": 1000})
        orders = self._results(payload)
        return [order for order in orders if same_local_day(order_date(order), target_date)]

    def get_orders_range(self, start_date: Date | str, end_date: Date | str) -> list[dict[str, Any]]:
        start = parse_report_date(start_date)
        end = parse_report_date(end_date)
        payload = self._get("/api/json/reply/OrderList", {"Take": 1000})
        orders = self._results(payload)
        result = []
        for order in orders:
            parsed = order_date(order)
            if parsed and start <= parsed.date() <= end:
                result.append(order)
        return result

    def get_order_detail(self, order_id: Any) -> list[dict[str, Any]]:
        payload = self._get("/api/json/reply/OrderGetDetail", {"OrderId": order_id})
        return self._results(payload)


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


def order_date(order: dict[str, Any]) -> datetime | None:
    for field in ("PurchaseDate", "CreatedDate", "CreatedAt", "Date"):
        parsed = parse_pos365_datetime(order.get(field))
        if parsed:
            return parsed
    return None


def same_local_day(value: datetime | None, target_date: Date) -> bool:
    return value is not None and value.date() == target_date
