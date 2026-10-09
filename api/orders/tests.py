import hashlib
import hmac
import json
import tempfile
from pathlib import Path

from django.conf import settings
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from . import constants
from .models import Order
from .providers import registry
from .providers.base import (
    InvalidPayloadError,
    OrderClient,
    OrderData,
    OrderLookupError,
    Provider,
)
from .providers.doordash import DoorDashProvider
from .providers.uber import STATUS_MAP, FixtureOrderClient, UberProvider

FIXTURES_DIR = settings.REPO_ROOT / "fixtures"
UBER_SECRET = "test-uber-secret"
DOORDASH_AUTH = "Bearer test-doordash-token-0001"


def fixture_bytes(name: str) -> bytes:
    return (FIXTURES_DIR / name).read_bytes()


def sign_uber(body: bytes, secret: str = UBER_SECRET) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def make_order(**overrides) -> Order:
    fields = {
        "provider": constants.PROVIDER_UBER,
        "external_order_id": "order-1",
        "total_cents": 1000,
        "currency": "USD",
    }
    fields.update(overrides)
    return Order.objects.create(**fields)


class OrderModelTests(TestCase):
    def test_same_provider_and_external_id_is_rejected(self):
        make_order()
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_order()

    def test_same_external_id_is_allowed_for_another_provider(self):
        make_order()
        make_order(provider=constants.PROVIDER_DOORDASH)
        self.assertEqual(Order.objects.count(), 2)

    def test_next_status_walks_the_progression_and_stops(self):
        order = make_order()
        seen = [order.status]
        while order.next_status():
            order.status = order.next_status()
            seen.append(order.status)
        self.assertEqual(tuple(seen), constants.STATUS_PROGRESSION)

    def test_cancelled_has_no_next_status(self):
        self.assertIsNone(make_order(status=constants.STATUS_CANCELLED).next_status())


class StubProvider(Provider):
    def matches(self, payload):
        return "stub" in payload

    def authenticate(self, raw_body, headers):
        return True

    def build_order(self, payload):
        return OrderData(
            provider="stub",
            external_order_id=str(payload["stub"]),
            status=constants.STATUS_NEW,
            customer_name="Stub Customer",
            customer_phone="",
            line_items=[],
            total_cents=100,
            currency="USD",
            raw_payload=payload,
        )


class StubOrderClient(OrderClient):
    def get_order(self, resource_id):
        return {"id": resource_id}


class RegistryTests(SimpleTestCase):
    @override_settings(WEBHOOK_PROVIDERS=["orders.tests.StubProvider"])
    def test_providers_are_loaded_from_settings(self):
        providers = registry.get_providers()
        self.assertEqual(len(providers), 1)
        self.assertIsInstance(providers[0], StubProvider)

    @override_settings(WEBHOOK_PROVIDERS=[])
    def test_empty_provider_setting_loads_nothing(self):
        self.assertEqual(registry.get_providers(), [])

    @override_settings(UBER_ORDER_CLIENT="orders.tests.StubOrderClient")
    def test_order_client_is_loaded_from_settings(self):
        client = registry.get_order_client()
        self.assertIsInstance(client, StubOrderClient)
        self.assertEqual(client.get_order("abc"), {"id": "abc"})


@override_settings(
    UBER_CLIENT_SECRET=UBER_SECRET,
    UBER_GET_ORDER_FIXTURE=FIXTURES_DIR / "uber_get_order.json",
)
class UberProviderTests(SimpleTestCase):
    def setUp(self):
        self.provider = UberProvider()
        self.body = fixture_bytes("uber_webhook.json")
        self.payload = json.loads(self.body)

    def test_matches_only_payloads_with_a_resource_id(self):
        self.assertTrue(self.provider.matches(self.payload))
        self.assertFalse(self.provider.matches({"meta": {}}))
        self.assertFalse(self.provider.matches({"event": {}, "order": {}}))

    def test_valid_signature_is_accepted(self):
        headers = {"X-Uber-Signature": sign_uber(self.body)}
        self.assertTrue(self.provider.authenticate(self.body, headers))

    def test_tampered_body_wrong_secret_and_missing_header_are_rejected(self):
        signature = sign_uber(self.body)
        self.assertFalse(
            self.provider.authenticate(self.body + b" ", {"X-Uber-Signature": signature})
        )
        wrong = sign_uber(self.body, "another-secret")
        self.assertFalse(self.provider.authenticate(self.body, {"X-Uber-Signature": wrong}))
        self.assertFalse(self.provider.authenticate(self.body, {}))

    def test_non_ascii_signature_is_rejected_without_error(self):
        self.assertFalse(self.provider.authenticate(self.body, {"X-Uber-Signature": "é"}))

    def test_build_order_maps_the_fetched_order(self):
        data = self.provider.build_order(self.payload)
        self.assertEqual(data.provider, constants.PROVIDER_UBER)
        self.assertEqual(data.external_order_id, "f9f363d1-e1c2-4595-b477-c649845bc953")
        self.assertEqual(data.status, constants.STATUS_NEW)
        self.assertEqual(data.customer_name, "Larry")
        self.assertEqual(data.customer_phone, "+1 555-555-5555")
        self.assertEqual(data.total_cents, 1399)
        self.assertEqual(data.currency, "USD")
        self.assertEqual(
            data.line_items[0],
            {
                "name": "Fresh-baked muffin",
                "quantity": 1,
                "unit_price_cents": 350,
                "line_total_cents": 350,
            },
        )
        self.assertEqual(len(data.line_items), 3)
        self.assertEqual(data.created_at.isoformat(), "2019-05-14T15:16:54-05:00")
        self.assertEqual(data.raw_payload["webhook"], self.payload)

    def test_provider_state_map_covers_every_documented_state(self):
        self.assertEqual(STATUS_MAP["CREATED"], constants.STATUS_NEW)
        self.assertEqual(STATUS_MAP["ACCEPTED"], constants.STATUS_ACCEPTED)
        self.assertEqual(STATUS_MAP["DENIED"], constants.STATUS_CANCELLED)
        self.assertEqual(STATUS_MAP["CANCELED"], constants.STATUS_CANCELLED)
        self.assertEqual(STATUS_MAP["FINISHED"], constants.STATUS_COMPLETED)
        self.assertEqual(STATUS_MAP["UNKNOWN"], constants.STATUS_NEW)

    def test_notification_status_is_never_used_as_order_status(self):
        self.assertEqual(self.payload["meta"]["status"], "pos")
        self.assertEqual(self.provider.build_order(self.payload).status, constants.STATUS_NEW)

    def test_missing_fixture_raises_a_lookup_error(self):
        client = FixtureOrderClient(fixture_path="/nonexistent/order.json")
        with self.assertRaises(OrderLookupError):
            client.get_order("anything")

    def test_unusable_fetched_order_raises_a_lookup_error(self):
        class BrokenClient(OrderClient):
            def get_order(self, resource_id):
                return {"id": resource_id}

        provider = UberProvider(order_client=BrokenClient())
        with self.assertRaises(OrderLookupError):
            provider.build_order(self.payload)


@override_settings(DOORDASH_WEBHOOK_AUTH_HEADER=DOORDASH_AUTH, DEFAULT_CURRENCY="USD")
class DoorDashProviderTests(SimpleTestCase):
    def setUp(self):
        self.provider = DoorDashProvider()
        self.body = fixture_bytes("doordash_order.json")
        self.payload = json.loads(self.body)

    def test_matches_only_payloads_with_event_and_order(self):
        self.assertTrue(self.provider.matches(self.payload))
        self.assertFalse(self.provider.matches({"event": {}}))
        self.assertFalse(self.provider.matches({"event": {}, "order": "text"}))
        self.assertFalse(self.provider.matches({"meta": {"resource_id": "x"}}))

    def test_matching_authorization_header_is_accepted(self):
        self.assertTrue(
            self.provider.authenticate(self.body, {"Authorization": DOORDASH_AUTH})
        )

    def test_wrong_missing_and_prefix_only_headers_are_rejected(self):
        for headers in (
            {"Authorization": "Bearer wrong-token-00000001"},
            {},
            {"Authorization": "Bearer"},
            {"Authorization": "é"},
        ):
            with self.subTest(headers=headers):
                self.assertFalse(self.provider.authenticate(self.body, headers))

    def test_build_order_maps_the_payload(self):
        data = self.provider.build_order(self.payload)
        self.assertEqual(data.provider, constants.PROVIDER_DOORDASH)
        self.assertEqual(data.external_order_id, "abc12345")
        self.assertEqual(data.status, constants.STATUS_NEW)
        self.assertEqual(data.customer_name, "Kelley W.")
        self.assertEqual(data.customer_phone, "+18559731040")
        self.assertEqual(data.total_cents, 2300)
        self.assertEqual(data.currency, "USD")
        self.assertEqual(
            data.line_items,
            [
                {
                    "name": "Burrito Scram-Bowl",
                    "quantity": 1,
                    "unit_price_cents": 0,
                    "line_total_cents": 0,
                }
            ],
        )
        self.assertIsNone(data.created_at)
        self.assertEqual(data.raw_payload, self.payload)

    def test_tips_are_not_part_of_the_total(self):
        self.payload["order"]["tip_amount"] = 500
        self.payload["order"]["merchant_tip_amount"] = 200
        self.assertEqual(self.provider.build_order(self.payload).total_cents, 2300)

    def test_missing_fields_and_unknown_status_raise_invalid_payload(self):
        del self.payload["order"]["subtotal"]
        with self.assertRaises(InvalidPayloadError):
            self.provider.build_order(self.payload)
        self.payload = json.loads(self.body)
        self.payload["event"]["status"] = "SOMETHING_ELSE"
        with self.assertRaises(InvalidPayloadError):
            self.provider.build_order(self.payload)


WEBHOOK_SETTINGS = {
    "UBER_CLIENT_SECRET": UBER_SECRET,
    "DOORDASH_WEBHOOK_AUTH_HEADER": DOORDASH_AUTH,
    "UBER_GET_ORDER_FIXTURE": FIXTURES_DIR / "uber_get_order.json",
    "DEFAULT_CURRENCY": "USD",
}


class WebhookTestCase(APITestCase):
    def post_raw(self, body: bytes, **headers):
        return self.client.generic(
            "POST",
            reverse("webhook-orders"),
            data=body,
            content_type="application/json",
            **headers,
        )

    def post_uber(self, body: bytes | None = None, signature: str | None = None):
        body = body if body is not None else fixture_bytes("uber_webhook.json")
        signature = signature if signature is not None else sign_uber(body)
        return self.post_raw(body, HTTP_X_UBER_SIGNATURE=signature)

    def post_doordash(self, body: bytes | None = None, authorization: str = DOORDASH_AUTH):
        body = body if body is not None else fixture_bytes("doordash_order.json")
        return self.post_raw(body, HTTP_AUTHORIZATION=authorization)


@override_settings(**WEBHOOK_SETTINGS)
class WebhookAuthTests(WebhookTestCase):
    def assert_rejected(self, response):
        self.assertEqual(response.status_code, 401)
        self.assertEqual(Order.objects.count(), 0)

    def test_uber_valid_signature_returns_200_with_empty_body(self):
        response = self.post_uber()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")

    def test_uber_tampered_body_is_rejected(self):
        body = fixture_bytes("uber_webhook.json")
        response = self.post_uber(body.replace(b"pos", b"abc"), sign_uber(body))
        self.assert_rejected(response)

    def test_uber_wrong_secret_is_rejected(self):
        body = fixture_bytes("uber_webhook.json")
        self.assert_rejected(self.post_uber(body, sign_uber(body, "wrong-secret")))

    def test_uber_missing_signature_header_is_rejected(self):
        self.assert_rejected(self.post_raw(fixture_bytes("uber_webhook.json")))

    def test_doordash_matching_header_returns_200(self):
        response = self.post_doordash()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.count(), 1)

    def test_doordash_wrong_header_is_rejected(self):
        self.assert_rejected(self.post_doordash(authorization="Bearer wrong-token-000001"))

    def test_doordash_missing_header_is_rejected(self):
        self.assert_rejected(self.post_raw(fixture_bytes("doordash_order.json")))

    def test_doordash_prefix_only_header_is_rejected(self):
        self.assert_rejected(self.post_doordash(authorization="Bearer"))


def find_keys(node, key: str) -> bool:
    if isinstance(node, dict):
        return key in node or any(find_keys(value, key) for value in node.values())
    if isinstance(node, list):
        return any(find_keys(value, key) for value in node)
    return False


@override_settings(**WEBHOOK_SETTINGS)
class WebhookIngestTests(WebhookTestCase):
    def test_uber_webhook_produces_one_correct_order(self):
        self.post_uber()
        order = Order.objects.get()
        self.assertEqual(order.provider, constants.PROVIDER_UBER)
        self.assertEqual(order.external_order_id, "f9f363d1-e1c2-4595-b477-c649845bc953")
        self.assertEqual(order.status, constants.STATUS_NEW)
        self.assertEqual(order.customer_name, "Larry")
        self.assertEqual(order.customer_phone, "+1 555-555-5555")
        self.assertEqual(order.total_cents, 1399)
        self.assertEqual(order.currency, "USD")
        self.assertEqual([item["name"] for item in order.line_items][0], "Fresh-baked muffin")
        self.assertEqual(
            order.raw_payload["webhook"], json.loads(fixture_bytes("uber_webhook.json"))
        )
        self.assertEqual(
            order.raw_payload["order"], json.loads(fixture_bytes("uber_get_order.json"))
        )

    def test_doordash_webhook_produces_one_correct_order(self):
        self.post_doordash()
        order = Order.objects.get()
        self.assertEqual(order.provider, constants.PROVIDER_DOORDASH)
        self.assertEqual(order.external_order_id, "abc12345")
        self.assertEqual(order.status, constants.STATUS_NEW)
        self.assertEqual(order.customer_name, "Kelley W.")
        self.assertEqual(order.customer_phone, "+18559731040")
        self.assertEqual(order.total_cents, 2300)
        self.assertEqual(order.currency, "USD")
        self.assertEqual(order.line_items[0]["name"], "Burrito Scram-Bowl")
        self.assertEqual(order.raw_payload, json.loads(fixture_bytes("doordash_order.json")))

    def test_unknown_payload_shape_returns_400(self):
        response = self.post_raw(b'{"hello": "world"}')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)

    def test_invalid_json_returns_400(self):
        for body in (b"{not json", b"", b"[1, 2]"):
            with self.subTest(body=body):
                self.assertEqual(self.post_raw(body).status_code, 400)

    def test_doordash_payload_missing_required_fields_returns_400(self):
        payload = json.loads(fixture_bytes("doordash_order.json"))
        del payload["order"]["subtotal"]
        response = self.post_doordash(json.dumps(payload).encode())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)

    def test_failing_order_lookup_returns_502_and_saves_nothing(self):
        with override_settings(UBER_GET_ORDER_FIXTURE=FIXTURES_DIR / "missing.json"):
            response = self.post_uber()
        self.assertEqual(response.status_code, 502)
        self.assertEqual(Order.objects.count(), 0)

    def test_no_official_fixture_contains_a_provider_key(self):
        paths = list(FIXTURES_DIR.rglob("*.json"))
        self.assertGreaterEqual(len(paths), 7)
        for path in paths:
            with self.subTest(path=path.name):
                self.assertFalse(find_keys(json.loads(path.read_bytes()), "provider"))

    @override_settings(
        WEBHOOK_PROVIDERS=[
            "orders.providers.uber.UberProvider",
            "orders.providers.doordash.DoorDashProvider",
            "orders.tests.StubProvider",
        ]
    )
    def test_third_provider_is_ingested_without_touching_view_or_service(self):
        response = self.post_raw(b'{"stub": "stub-1"}')
        self.assertEqual(response.status_code, 200)
        order = Order.objects.get()
        self.assertEqual((order.provider, order.external_order_id), ("stub", "stub-1"))

    def test_same_webhook_twice_leaves_one_row(self):
        self.post_uber()
        self.post_uber()
        self.post_doordash()
        self.post_doordash()
        self.assertEqual(Order.objects.count(), 2)

    def test_retried_webhook_does_not_move_status_backwards(self):
        self.post_uber()
        Order.objects.update(status=constants.STATUS_PREPARING)
        self.post_uber()
        self.assertEqual(Order.objects.get().status, constants.STATUS_PREPARING)

    def test_retry_keeps_the_original_created_at(self):
        self.post_doordash()
        first = Order.objects.get().created_at
        self.post_doordash()
        self.assertEqual(Order.objects.get().created_at, first)

    def test_cancelled_from_provider_is_applied_and_sticks(self):
        self.post_uber()
        Order.objects.update(status=constants.STATUS_PREPARING)
        order_payload = json.loads(fixture_bytes("uber_get_order.json"))
        order_payload["current_state"] = "CANCELED"
        with tempfile.TemporaryDirectory() as directory:
            cancelled_path = Path(directory) / "cancelled.json"
            cancelled_path.write_text(json.dumps(order_payload))
            with override_settings(UBER_GET_ORDER_FIXTURE=cancelled_path):
                self.post_uber()
        self.assertEqual(Order.objects.get().status, constants.STATUS_CANCELLED)
        self.post_uber()
        self.assertEqual(Order.objects.get().status, constants.STATUS_CANCELLED)
