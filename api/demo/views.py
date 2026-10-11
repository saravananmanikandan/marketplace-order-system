import hashlib
import hmac
import json
import shlex
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

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
# Uber adds this header to every webhook; the docs say it names the API the
# request comes from, `production` or `sandbox`. The simulator is never production.
UBER_ENVIRONMENT_HEADER = "X-Environment"
UBER_ENVIRONMENT_SANDBOX = "sandbox"


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
    headers = {
        **JSON_CONTENT_TYPE_HEADER,
        UBER_ENVIRONMENT_HEADER: UBER_ENVIRONMENT_SANDBOX,
        constants.UBER_SIGNATURE_HEADER: sent,
    }
    return headers, headers


def doordash_headers(valid: bool) -> tuple[dict[str, str], dict[str, str]]:
    token = settings.DOORDASH_WEBHOOK_AUTH_HEADER
    sent = token if valid else tamper(token)
    headers = {**JSON_CONTENT_TYPE_HEADER, constants.AUTHORIZATION_HEADER: sent}
    shown = {**JSON_CONTENT_TYPE_HEADER, constants.AUTHORIZATION_HEADER: mask_authorization(sent)}
    return headers, shown


DOORDASH_TOKEN_VARIABLE = "DOORDASH_WEBHOOK_AUTH_HEADER"
INVALID_DOORDASH_AUTHORIZATION = "Bearer not-the-configured-token"
# Only the token line is read; running .env as shell code would also run
# anything else pasted into it.
LOAD_ENV_LINES = (
    "# Run from the project folder; this reads only the DoorDash token from .env.",
    f"{DOORDASH_TOKEN_VARIABLE}=\"$(grep '^{DOORDASH_TOKEN_VARIABLE}=' .env"
    " | tail -n 1 | cut -d= -f2- | tr -d '\"')\"",
)


def curl_command(url: str, body: bytes, headers: dict[str, str], provider: str, valid: bool) -> str:
    # The body is quoted byte for byte, so a repeated Uber request still
    # matches its signature; the DoorDash token is read from .env, never shown.
    header_options = []
    for name, value in headers.items():
        if name == constants.AUTHORIZATION_HEADER and provider == builders.PROVIDER_DOORDASH:
            value = f"${DOORDASH_TOKEN_VARIABLE}" if valid else INVALID_DOORDASH_AUTHORIZATION
            header_options.append(f'-H "{name}: {value}"')
        else:
            header_options.append(f"-H {shlex.quote(f'{name}: {value}')}")
    options = [
        f"curl -i -X POST {shlex.quote(url)}",
        *header_options,
        f"--data-binary {shlex.quote(body.decode())}",
    ]
    command = " \\\n  ".join(options)
    uses_env = provider == builders.PROVIDER_DOORDASH and valid
    return "\n".join([*LOAD_ENV_LINES, "", command]) if uses_env else command


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


@dataclass(frozen=True)
class PreparedWebhook:
    options: builders.Options
    order_id: str
    url: str
    payload: dict[str, Any]
    body: bytes
    headers: dict[str, str]
    shown_headers: dict[str, str]
    staged_order: dict[str, Any] | None


def prepare_webhook(request) -> PreparedWebhook:
    options = builders.parse_options(request.data)
    order_id = (
        builders.new_order_id(options.provider)
        if options.order_id == builders.NEW_ORDER_ID
        else options.order_id
    )
    payload, staged_order = _build_payload(options, order_id)
    body = json.dumps(payload).encode()
    # Headers come after serialising, because the Uber signature covers
    # the exact bytes that are sent.
    if options.provider == builders.PROVIDER_UBER:
        headers, shown_headers = uber_headers(body, options.auth_valid)
    else:
        headers, shown_headers = doordash_headers(options.auth_valid)
    return PreparedWebhook(
        options=options,
        order_id=order_id,
        url=request.build_absolute_uri(reverse("webhook-orders")),
        payload=payload,
        body=body,
        headers=headers,
        shown_headers=shown_headers,
        staged_order=staged_order,
    )


def _build_payload(options: builders.Options, order_id: str):
    customer, items = builders.order_content(options)
    if options.provider == builders.PROVIDER_UBER:
        order = builders.build_uber_order(
            order_id, options.preset, customer, items, options.uber_state
        )
        # Staged before the notification can arrive, because the core fetches
        # the order while it handles the notification.
        staging.stage_order(order_id, order)
        return builders.build_uber_notification(order_id, options.preset), order
    return builders.build_doordash_webhook(order_id, options.preset, customer, items), None


def invalid_options(error: builders.InvalidOptions) -> Response:
    return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)


class SimulatorSendView(APIView):
    authentication_classes: list = []
    permission_classes: list = []
    sender = staticmethod(send_webhook)

    def post(self, request) -> Response:
        try:
            prepared = prepare_webhook(request)
        except builders.InvalidOptions as error:
            return invalid_options(error)
        options = prepared.options
        deliveries = deliver(
            self.sender, prepared.url, prepared.body, prepared.headers, options.deliveries
        )
        staging.remember_last_order_id(options.provider, prepared.order_id)
        return Response(
            {
                "provider": options.provider,
                "order_id": prepared.order_id,
                "last_order_ids": staging.last_order_ids(),
                "deliveries": deliveries,
                "sent": {
                    "url": prepared.url,
                    "headers": prepared.shown_headers,
                    "body": prepared.payload,
                    "staged_get_order": prepared.staged_order,
                },
            }
        )


class SimulatorCurlView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    # Nothing is sent: the caller runs the command, so a new id here means a
    # new order when it is pasted. The id is not remembered for "reuse",
    # because it may never be sent.
    def post(self, request) -> Response:
        try:
            prepared = prepare_webhook(request)
        except builders.InvalidOptions as error:
            return invalid_options(error)
        options = prepared.options
        return Response(
            {
                "provider": options.provider,
                "order_id": prepared.order_id,
                "curl": curl_command(
                    prepared.url,
                    prepared.body,
                    prepared.headers,
                    options.provider,
                    options.auth_valid,
                ),
            }
        )
