from django.conf import settings
from django.utils.module_loading import import_string

from .base import OrderClient, Provider


def get_providers() -> list[Provider]:
    return [import_string(path)() for path in settings.WEBHOOK_PROVIDERS]


def get_order_client() -> OrderClient:
    return import_string(settings.UBER_ORDER_CLIENT)()
