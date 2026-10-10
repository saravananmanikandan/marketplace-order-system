from typing import Any

from django.db import transaction
from django.utils import timezone

from .. import constants
from ..models import Order
from .base import OrderData, Provider
from .registry import get_providers


def find_provider(payload: dict[str, Any]) -> Provider | None:
    return next(
        (provider for provider in get_providers() if provider.matches(payload)), None
    )


def ingest(provider: Provider, payload: dict[str, Any]) -> Order:
    return save_order(provider.build_order(payload))


def resolve_status(stored: str | None, incoming: str) -> str:
    if stored is None:
        return incoming
    rank = constants.STATUS_ORDER.index
    moves_forward = rank(incoming) > rank(stored)
    if incoming == constants.STATUS_CANCELLED or moves_forward:
        return incoming
    return stored


def save_order(data: OrderData) -> Order:
    identity = {
        "provider": data.provider,
        "external_order_id": data.external_order_id,
    }
    with transaction.atomic():
        stored = (
            Order.objects.filter(**identity).values_list("status", flat=True).first()
        )
        fields = {
            "status": resolve_status(stored, data.status),
            "customer_name": data.customer_name,
            "customer_phone": data.customer_phone,
            "customer_phone_code": data.customer_phone_code,
            "line_items": data.line_items,
            "total_cents": data.total_cents,
            "currency": data.currency,
            "raw_payload": data.raw_payload,
        }
        order, _ = Order.objects.update_or_create(
            **identity,
            defaults=fields,
            create_defaults={
                **fields,
                "created_at": data.created_at or timezone.now(),
            },
        )
    return order
