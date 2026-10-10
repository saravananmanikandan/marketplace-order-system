import hashlib
import hmac
import json
import threading
import urllib.error
import urllib.request

from django.conf import settings
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from orders import constants
from orders.providers.base import InvalidOrderPayload, OrderLookupError

from . import builders, staging
from .clients import StagedOrderClient


class MockUberOrderView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request, order_id: str) -> Response:
        if not self._has_valid_token(request.headers.get(constants.AUTHORIZATION_HEADER, "")):
            return Response({"detail": "Unauthorized."}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            order = StagedOrderClient().get_order(order_id)
        except InvalidOrderPayload:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        except OrderLookupError as error:
            return Response({"detail": str(error)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(order)

    @staticmethod
    def _has_valid_token(provided: str) -> bool:
        if not settings.UBER_ACCESS_TOKEN:
            return False
        expected = constants.BEARER_PREFIX + settings.UBER_ACCESS_TOKEN
        return hmac.compare_digest(expected.encode(), provided.encode())


SEND_TIMEOUT_SECONDS = 15
MAX_RESPONSE_BODY_LENGTH = 2000
MASK = "****"
VISIBLE_SECRET_CHARACTERS = 4
JSON_CONTENT_TYPE_HEADER = {"Content-Type": constants.JSON_CONTENT_TYPE}


def send_webhook(url: str, body: bytes, headers: dict[str, str]) -> tuple[int | None, str]:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=SEND_TIMEOUT_SECONDS) as response:
            return response.status, response.read().decode(errors="replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode(errors="replace")
    except (urllib.error.URLError, OSError):
        return None, f"Could not reach {url}."


def deliver(sender, url: str, body: bytes, headers: dict[str, str], count: int) -> list[dict]:
    if count == 1:
        results = [sender(url, body, headers)]
    else:
        results = _deliver_at_once(sender, url, body, headers, count)
    return [
        {"status": status_code, "body": text[:MAX_RESPONSE_BODY_LENGTH]}
        for status_code, text in results
    ]


def _deliver_at_once(
    sender, url: str, body: bytes, headers: dict[str, str], count: int
) -> list[tuple[int | None, str]]:
    results: list[tuple[int | None, str]] = [(None, "")] * count
    # The barrier releases every thread together, so the copies really
    # arrive at the same moment, like a provider retrying in parallel.
    barrier = threading.Barrier(count)

    def run(index: int) -> None:
        barrier.wait()
        results[index] = sender(url, body, headers)

    threads = [threading.Thread(target=run, args=(index,)) for index in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return results


def tamper(value: str) -> str:
    return value[:-1] + ("0" if value[-1] != "0" else "1")


def mask_authorization(value: str) -> str:
    prefix = constants.BEARER_PREFIX if value.startswith(constants.BEARER_PREFIX) else ""
    secret = value[len(prefix) :]
    long_enough = len(secret) > 2 * VISIBLE_SECRET_CHARACTERS
    visible = secret[-VISIBLE_SECRET_CHARACTERS:] if long_enough else ""
    return prefix + MASK + visible


def uber_headers(body: bytes, valid: bool) -> tuple[dict[str, str], dict[str, str]]:
    signature = hmac.new(settings.UBER_CLIENT_SECRET.encode(), body, hashlib.sha256).hexdigest()
    sent = signature if valid else tamper(signature)
    headers = {**JSON_CONTENT_TYPE_HEADER, constants.UBER_SIGNATURE_HEADER: sent}
    return headers, headers


def doordash_headers(valid: bool) -> tuple[dict[str, str], dict[str, str]]:
    token = settings.DOORDASH_WEBHOOK_AUTH_HEADER
    sent = token if valid else tamper(token)
    headers = {**JSON_CONTENT_TYPE_HEADER, constants.AUTHORIZATION_HEADER: sent}
    shown = {**JSON_CONTENT_TYPE_HEADER, constants.AUTHORIZATION_HEADER: mask_authorization(sent)}
    return headers, shown


class SimulatorConfigView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request) -> Response:
        return Response(
            {
                "enabled": True,
                "providers": builders.PROVIDERS,
                "presets": builders.PRESETS,
                "uber_states": builders.UBER_STATES,
                "last_order_ids": staging.last_order_ids(),
                "limits": {
                    "items": builders.MAX_ITEMS,
                    "quantity": builders.MAX_QUANTITY,
                    "unit_price_cents": builders.MAX_UNIT_PRICE_CENTS,
                },
            }
        )


class SimulatorSendView(APIView):
    authentication_classes: list = []
    permission_classes: list = []
    sender = staticmethod(send_webhook)

    def post(self, request) -> Response:
        try:
            options = builders.parse_options(request.data)
        except builders.InvalidOptions as error:
            return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)

        order_id = (
            builders.new_order_id(options.provider)
            if options.order_id == builders.NEW_ORDER_ID
            else options.order_id
        )
        payload, staged = self._build(options, order_id)
        body = json.dumps(payload).encode()
        # Headers come after serialising, because the Uber signature covers
        # the exact bytes that are sent.
        if options.provider == builders.PROVIDER_UBER:
            headers, shown_headers = uber_headers(body, options.auth_valid)
        else:
            headers, shown_headers = doordash_headers(options.auth_valid)
        url = request.build_absolute_uri(reverse("webhook-orders"))
        deliveries = deliver(self.sender, url, body, headers, options.deliveries)
        staging.remember_last_order_id(options.provider, order_id)
        return Response(
            {
                "provider": options.provider,
                "order_id": order_id,
                "last_order_ids": staging.last_order_ids(),
                "deliveries": deliveries,
                "sent": {
                    "url": url,
                    "headers": shown_headers,
                    "body": payload,
                    "staged_get_order": staged,
                },
            }
        )

    @staticmethod
    def _build(options: builders.Options, order_id: str):
        customer, items = builders.order_content(options)
        if options.provider == builders.PROVIDER_UBER:
            order = builders.build_uber_order(
                order_id, options.preset, customer, items, options.uber_state
            )
            # Staged before the notification goes out, because the core
            # fetches the order while it handles the notification.
            staging.stage_order(order_id, order)
            return builders.build_uber_notification(order_id, options.preset), order
        return builders.build_doordash_webhook(order_id, options.preset, customer, items), None
