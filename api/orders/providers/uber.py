import hashlib
import hmac
import json
import logging
import re
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from django.conf import settings

from .. import constants
from . import validation
from .base import (
    InvalidOrderPayload,
    OrderClient,
    OrderData,
    OrderLookupError,
    Provider,
    invalid_order_on_mapping_error,
)
from .registry import get_order_client

logger = logging.getLogger(__name__)

STATUS_MAP = {
    "CREATED": constants.STATUS_NEW,
    "ACCEPTED": constants.STATUS_ACCEPTED,
    "DENIED": constants.STATUS_CANCELLED,
    "CANCELED": constants.STATUS_CANCELLED,
    "FINISHED": constants.STATUS_COMPLETED,
    "UNKNOWN": constants.STATUS_NEW,
}


def require_resource_id(resource_id: Any) -> str:
    is_valid = (
        isinstance(resource_id, str)
        and len(resource_id) <= constants.UBER_RESOURCE_ID_MAX_LENGTH
        and re.fullmatch(constants.UBER_RESOURCE_ID_PATTERN, resource_id)
    )
    if not is_valid:
        raise InvalidOrderPayload(
            "meta.resource_id may only contain letters, digits, - and _, "
            f"up to {constants.UBER_RESOURCE_ID_MAX_LENGTH} characters."
        )
    return resource_id


class FixtureOrderClient(OrderClient):
    def __init__(
        self, fixture_path: Path | str | None = None, demo_dir: Path | str | None = None
    ) -> None:
        self.fixture_path = Path(fixture_path or settings.UBER_GET_ORDER_FIXTURE)
        self.demo_dir = Path(demo_dir or settings.UBER_DEMO_ORDERS_DIR)

    def get_order(self, resource_id: str) -> dict[str, Any]:
        require_resource_id(resource_id)
        demo_path = self.demo_dir / f"{resource_id}.json"
        if self._is_file(demo_path):
            return self._load(demo_path)
        # The official webhook and Get Order examples carry different ids, so
        # the official order is reused under the id Uber asked for.
        order = self._load(self.fixture_path)
        order["id"] = resource_id
        order["display_id"] = resource_id[-constants.UBER_DISPLAY_ID_LENGTH :]
        return order

    @staticmethod
    def _is_file(path: Path) -> bool:
        try:
            return path.is_file()
        except OSError as error:
            raise OrderLookupError("Could not look up the order fixture.") from error

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        try:
            with open(path, encoding="utf-8") as fixture:
                return json.load(fixture)
        except (OSError, json.JSONDecodeError) as error:
            raise OrderLookupError("Could not read the order fixture.") from error


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
        self._require_order_event(payload.get("event_type"))
        resource_id = require_resource_id(payload["meta"]["resource_id"])
        order = self.order_client.get_order(resource_id)
        with invalid_order_on_mapping_error():
            return self._map_order(payload, validation.require_object(order, "order"))

    @staticmethod
    def _require_order_event(event_type: Any) -> None:
        if not (
            isinstance(event_type, str)
            and event_type.startswith(constants.UBER_ORDER_EVENT_PREFIX)
        ):
            raise InvalidOrderPayload(
                f"event_type must start with {constants.UBER_ORDER_EVENT_PREFIX}"
            )

    def _map_order(self, payload: dict[str, Any], order: dict[str, Any]) -> OrderData:
        eater = validation.optional_object(order.get("eater"), "eater")
        payment = validation.require_object(order.get("payment"), "payment")
        charges = validation.require_object(payment.get("charges"), "payment.charges")
        total_cents, currency = self._total(charges)
        cart = validation.require_object(order.get("cart"), "cart")
        items = validation.require_list(cart.get("items"), "cart.items")
        return OrderData(
            provider=constants.PROVIDER_UBER,
            external_order_id=validation.require_text(
                order.get("id"), "id", constants.MAX_EXTERNAL_ID_LENGTH
            ),
            status=STATUS_MAP.get(order.get("current_state"), constants.STATUS_NEW),
            customer_name=validation.customer_name(eater, "eater"),
            customer_phone=validation.customer_phone(eater, "eater"),
            line_items=[self._line_item(item) for item in items],
            total_cents=total_cents,
            currency=currency,
            raw_payload={"webhook": payload, "order": order},
            created_at=self._placed_at(order.get("placed_at")),
        )

    # The Get Order docs mark `total` as optional, so its documented parts
    # `sub_total` and `tax` stand in for it when it is missing.
    def _total(self, charges: dict[str, Any]) -> tuple[int, str]:
        if charges.get("total") is not None:
            return self._money(charges["total"], "payment.charges.total")
        if charges.get("sub_total") is None:
            raise InvalidOrderPayload("payment.charges has neither total nor sub_total.")
        amount, currency = self._money(charges["sub_total"], "payment.charges.sub_total")
        if charges.get("tax") is None:
            return amount, currency
        tax, tax_currency = self._money(charges["tax"], "payment.charges.tax")
        if tax_currency != currency:
            raise InvalidOrderPayload("payment.charges.tax has a different currency.")
        return amount + tax, currency

    @staticmethod
    def _money(raw_money: Any, field: str) -> tuple[int, str]:
        money = validation.require_object(raw_money, field)
        return (
            UberProvider._amount(money, field),
            validation.require_currency(money.get("currency_code"), f"{field}.currency_code"),
        )

    @staticmethod
    def _amount(raw_money: Any, field: str) -> int:
        money = validation.require_object(raw_money, field)
        return validation.require_money(money.get("amount"), f"{field}.amount")

    @staticmethod
    def _line_item(raw_item: Any) -> dict[str, Any]:
        item = validation.require_object(raw_item, "cart.items[]")
        price = validation.require_object(item.get("price"), "cart.items[].price")
        return {
            "name": validation.require_text(item.get("title"), "cart.items[].title"),
            "quantity": validation.require_quantity(
                item.get("quantity"), "cart.items[].quantity"
            ),
            "unit_price_cents": UberProvider._amount(
                price.get("unit_price"), "cart.items[].price.unit_price"
            ),
            "line_total_cents": UberProvider._amount(
                price.get("total_price"), "cart.items[].price.total_price"
            ),
        }

    # `placed_at` is optional; a bad value must not cost the order, so the
    # received time is used instead.
    @staticmethod
    def _placed_at(placed_at: Any) -> datetime | None:
        if placed_at is None:
            return None
        try:
            parsed = datetime.fromisoformat(placed_at)
        except (TypeError, ValueError):
            parsed = None
        if parsed is None or parsed.tzinfo is None:
            logger.warning("Uber placed_at %r is not a timestamp with an offset", placed_at)
            return None
        return parsed
