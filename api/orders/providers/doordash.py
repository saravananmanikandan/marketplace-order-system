import hmac
from collections.abc import Mapping
from typing import Any

from django.conf import settings

from .. import constants
from .base import InvalidPayloadError, OrderData, Provider

STATUS_MAP = {
    "NEW": constants.STATUS_NEW,
}


class DoorDashProvider(Provider):
    def __init__(self, expected_authorization: str | None = None) -> None:
        self.expected_authorization = (
            expected_authorization or settings.DOORDASH_WEBHOOK_AUTH_HEADER
        )

    def matches(self, payload: dict[str, Any]) -> bool:
        return isinstance(payload.get("event"), dict) and isinstance(
            payload.get("order"), dict
        )

    def authenticate(self, raw_body: bytes, headers: Mapping[str, str]) -> bool:
        provided = headers.get(constants.AUTHORIZATION_HEADER)
        if not provided:
            return False
        return hmac.compare_digest(
            self.expected_authorization.encode(), provided.encode()
        )

    def build_order(self, payload: dict[str, Any]) -> OrderData:
        try:
            return self._map_order(payload["event"], payload["order"])
        except (KeyError, TypeError, ValueError) as error:
            raise InvalidPayloadError(f"Unusable DoorDash order: {error!r}") from error

    def _map_order(self, event: dict[str, Any], order: dict[str, Any]) -> OrderData:
        consumer = order.get("consumer") or {}
        return OrderData(
            provider=constants.PROVIDER_DOORDASH,
            external_order_id=str(order["id"]),
            status=STATUS_MAP[event["status"]],
            customer_name=self._customer_name(consumer),
            customer_phone=consumer.get("phone", ""),
            line_items=self._line_items(order["categories"]),
            total_cents=int(order["subtotal"]) + int(order["tax"]),
            currency=settings.DEFAULT_CURRENCY,
            raw_payload={"event": event, "order": order},
        )

    @staticmethod
    def _customer_name(consumer: dict[str, Any]) -> str:
        parts = [consumer.get("first_name", ""), consumer.get("last_name", "")]
        return " ".join(part for part in parts if part)

    @staticmethod
    def _line_items(categories: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "name": item["name"],
                "quantity": item["quantity"],
                "unit_price_cents": int(item["price"]),
                "line_total_cents": int(item["price"]) * int(item["quantity"]),
            }
            for category in categories
            for item in category["items"]
        ]
