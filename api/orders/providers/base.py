from abc import ABC, abstractmethod
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from http import HTTPStatus
from typing import Any


class OrderLookupError(Exception):
    """The provider's order could not be fetched, so nothing can be saved."""


class InvalidOrderPayload(Exception):
    """The order data is missing or invalid, so a retry cannot fix it."""


MAPPING_ERRORS = (KeyError, TypeError, ValueError, AttributeError, OverflowError)


@contextmanager
def invalid_order_on_mapping_error() -> Iterator[None]:
    try:
        yield
    except MAPPING_ERRORS as error:
        raise InvalidOrderPayload("The order has a missing or invalid field.") from error


@dataclass(frozen=True)
class OrderData:
    provider: str
    external_order_id: str
    status: str
    customer_name: str
    customer_phone: str
    line_items: list[dict[str, Any]]
    total_cents: int
    currency: str
    raw_payload: dict[str, Any]
    created_at: datetime | None = field(default=None)


@dataclass(frozen=True)
class WebhookReply:
    status: int
    body: dict[str, Any] | None = None


class Provider(ABC):
    @abstractmethod
    def matches(self, payload: dict[str, Any]) -> bool:
        """Return True when the payload has this provider's shape."""

    @abstractmethod
    def authenticate(self, raw_body: bytes, headers: Mapping[str, str]) -> bool:
        """Return True when the request carries valid proof of origin."""

    @abstractmethod
    def build_order(self, payload: dict[str, Any]) -> OrderData:
        """Turn the webhook payload into the internal order fields."""

    def ignored_event(self, payload: dict[str, Any]) -> str | None:
        """Return the event type when the event is not an order to ingest."""
        return None

    def ignored_reply(self, event_type: str) -> WebhookReply:
        return WebhookReply(HTTPStatus.OK, {"ignored": event_type})

    def accepted_reply(self, order_id: int) -> WebhookReply:
        return WebhookReply(HTTPStatus.OK)

    def rejected_reply(self, message: str) -> WebhookReply:
        return WebhookReply(HTTPStatus.BAD_REQUEST, {"detail": message})


class OrderClient(ABC):
    @abstractmethod
    def get_order(self, resource_id: str) -> dict[str, Any]:
        """Fetch the full order, raising OrderLookupError on failure."""
