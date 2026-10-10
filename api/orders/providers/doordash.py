import hmac
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

from django.conf import settings

from .. import constants
from . import validation
from .base import (
    InvalidOrderPayload,
    OrderData,
    Provider,
    WebhookReply,
    invalid_order_on_mapping_error,
)

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
        event_status = event.get("status")
        # The documented envelope always has both fields. Without a type the
        # event cannot be identified, so it is rejected rather than ignored.
        if not isinstance(event_type, str) or not event_type.strip():
            raise InvalidOrderPayload("event.type must be a non-empty string.")
        # A list or object cannot be looked up in the status map, so it is
        # rejected here instead of failing the lookup.
        if not isinstance(event_status, str):
            raise InvalidOrderPayload("event.status must be a string.")
        if event_type == ORDER_CREATE_EVENT and event_status in STATUS_MAP:
            return None
        return event_type

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
        with invalid_order_on_mapping_error():
            return self._map_order(payload["event"], payload["order"])

    def _map_order(self, event: dict[str, Any], order: dict[str, Any]) -> OrderData:
        consumer = validation.optional_object(order.get("consumer"), "order.consumer")
        subtotal = validation.require_money(order.get("subtotal"), "order.subtotal")
        tax = validation.require_money(order.get("tax"), "order.tax")
        return OrderData(
            provider=constants.PROVIDER_DOORDASH,
            external_order_id=validation.require_order_id(order.get("id"), "order.id"),
            status=STATUS_MAP[event["status"]],
            customer_name=validation.customer_name(consumer, "order.consumer"),
            customer_phone=validation.customer_phone(consumer, "order.consumer"),
            line_items=self._line_items(order.get("categories")),
            total_cents=subtotal + tax,
            currency=settings.DEFAULT_CURRENCY,
            raw_payload={"event": event, "order": order},
        )

    @staticmethod
    def _line_items(raw_categories: Any) -> list[dict[str, Any]]:
        categories = validation.require_list(raw_categories, "order.categories")
        return [
            DoorDashProvider._line_item(item)
            for category in categories
            for item in validation.require_list(
                validation.require_object(category, "order.categories[]").get("items"),
                "order.categories[].items",
            )
        ]

    @staticmethod
    def _line_item(raw_item: Any) -> dict[str, Any]:
        item = validation.require_object(raw_item, "item")
        price = validation.require_money(item.get("price"), "item.price")
        quantity = validation.require_quantity(item.get("quantity"), "item.quantity")
        return {
            "name": validation.require_text(item.get("name"), "item.name"),
            "quantity": quantity,
            "unit_price_cents": price,
            "line_total_cents": price * quantity,
        }
