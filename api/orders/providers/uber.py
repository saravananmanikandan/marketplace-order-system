import hashlib
import hmac
import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from django.conf import settings

from .. import constants
from .base import OrderClient, OrderData, OrderLookupError, Provider
from .registry import get_order_client

STATUS_MAP = {
    "CREATED": constants.STATUS_NEW,
    "ACCEPTED": constants.STATUS_ACCEPTED,
    "DENIED": constants.STATUS_CANCELLED,
    "CANCELED": constants.STATUS_CANCELLED,
    "FINISHED": constants.STATUS_COMPLETED,
    "UNKNOWN": constants.STATUS_NEW,
}


class FixtureOrderClient(OrderClient):
    def __init__(self, fixture_path: str | None = None) -> None:
        self.fixture_path = fixture_path or settings.UBER_GET_ORDER_FIXTURE

    def get_order(self, resource_id: str) -> dict[str, Any]:
        # The official webhook and Get Order examples carry different ids, so
        # the fixture is returned for any resource id.
        try:
            with open(self.fixture_path, encoding="utf-8") as fixture:
                return json.load(fixture)
        except (OSError, json.JSONDecodeError) as error:
            raise OrderLookupError(f"Could not read the order fixture: {error}") from error


class UberProvider(Provider):
    def __init__(
        self, client_secret: str | None = None, order_client: OrderClient | None = None
    ) -> None:
        self.client_secret = client_secret or settings.UBER_CLIENT_SECRET
        self.order_client = order_client or get_order_client()

    def matches(self, payload: dict[str, Any]) -> bool:
        meta = payload.get("meta")
        return isinstance(meta, dict) and "resource_id" in meta

    def authenticate(self, raw_body: bytes, headers: Mapping[str, str]) -> bool:
        provided = headers.get(constants.UBER_SIGNATURE_HEADER)
        if not provided:
            return False
        expected = hmac.new(
            self.client_secret.encode(), raw_body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected.encode(), provided.encode())

    def build_order(self, payload: dict[str, Any]) -> OrderData:
        order = self.order_client.get_order(payload["meta"]["resource_id"])
        try:
            return self._map_order(payload, order)
        except (KeyError, TypeError, ValueError) as error:
            raise OrderLookupError(f"Fetched order is unusable: {error!r}") from error

    def _map_order(self, payload: dict[str, Any], order: dict[str, Any]) -> OrderData:
        total = order["payment"]["charges"]["total"]
        return OrderData(
            provider=constants.PROVIDER_UBER,
            external_order_id=order["id"],
            status=STATUS_MAP.get(order["current_state"], constants.STATUS_NEW),
            customer_name=self._customer_name(order.get("eater") or {}),
            customer_phone=(order.get("eater") or {}).get("phone", ""),
            line_items=[self._line_item(item) for item in order["cart"]["items"]],
            total_cents=int(total["amount"]),
            currency=total["currency_code"],
            raw_payload={"webhook": payload, "order": order},
            created_at=self._placed_at(order),
        )

    @staticmethod
    def _customer_name(eater: dict[str, Any]) -> str:
        parts = [eater.get("first_name", ""), eater.get("last_name", "")]
        return " ".join(part for part in parts if part)

    @staticmethod
    def _line_item(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": item["title"],
            "quantity": item["quantity"],
            "unit_price_cents": int(item["price"]["unit_price"]["amount"]),
            "line_total_cents": int(item["price"]["total_price"]["amount"]),
        }

    @staticmethod
    def _placed_at(order: dict[str, Any]) -> datetime | None:
        placed_at = order.get("placed_at")
        return datetime.fromisoformat(placed_at) if placed_at else None
