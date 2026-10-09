from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


class OrderLookupError(Exception):
    """The provider's order could not be fetched, so nothing can be saved."""


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


class OrderClient(ABC):
    @abstractmethod
    def get_order(self, resource_id: str) -> dict[str, Any]:
        """Fetch the full order, raising OrderLookupError on failure."""
