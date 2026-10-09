import hashlib
import hmac
import json

from django.conf import settings
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase, override_settings

from . import constants
from .models import Order
from .providers import registry
from .providers.base import OrderClient, OrderLookupError, Provider
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
        raise NotImplementedError


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
