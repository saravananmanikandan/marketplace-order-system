import hmac
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

from django.conf import settings

from .. import constants
from .base import InvalidPayloadError, OrderData, Provider, WebhookReply

ORDER_CREATE_EVENT = "OrderCreate"
STATUS_MAP = {
    "NEW": constants.STATUS_NEW,
}
ORDER_STATUS_SUCCESS = "success"
ORDER_STATUS_FAIL = "fail"


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

    def ignored_event(self, payload: dict[str, Any]) -> str | None:
        event = payload["event"]
        event_type = event.get("type")
        if event_type == ORDER_CREATE_EVENT and event.get("status") in STATUS_MAP:
            return None
        return str(event_type)

    # A 200 is DoorDash's synchronous order confirmation, and its body is the
    # confirmation payload; any non-2xx marks the order as failed.
    def accepted_reply(self, order_id: int) -> WebhookReply:
        return WebhookReply(
            HTTPStatus.OK,
            {"merchant_supplied_id": str(order_id), "order_status": ORDER_STATUS_SUCCESS},
        )

    def rejected_reply(self, message: str) -> WebhookReply:
        return WebhookReply(
            HTTPStatus.BAD_REQUEST,
            {"order_status": ORDER_STATUS_FAIL, "failure_reason": message},
        )

    def build_order(self, payload: dict[str, Any]) -> OrderData:
        try:
            return self._map_order(payload["event"], payload["order"])
        except KeyError as error:
            raise InvalidPayloadError(f"Missing order field: {error.args[0]}.") from error
        except (TypeError, ValueError) as error:
            raise InvalidPayloadError("Invalid order field.") from error

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
