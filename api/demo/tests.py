import contextlib
import importlib
import json
import shlex
import threading
import urllib.request
from unittest import mock, skipUnless
from urllib.parse import urlsplit

from django.conf import settings
from django.db import connections
from django.test import LiveServerTestCase, SimpleTestCase, override_settings
from django.urls import clear_url_caches, reverse
from rest_framework.test import APITestCase, APITransactionTestCase

from orders.models import Order
from orders.providers import ingest
from orders.providers.base import InvalidOrderPayload
from orders.providers.doordash import DoorDashProvider
from orders.providers.uber import HttpOrderClient, UberProvider
from orders.tests import (
    OFFICIAL_UBER_RESOURCE_ID,
    WEBHOOK_SETTINGS,
    WebhookClientMixin,
    fixture_bytes,
    uber_webhook_for,
)

from . import builders, staging
from .clients import DEMO_ORDERS_DIR, StagedOrderClient
from .views import SimulatorSendView, uber_headers

DEMO_UBER_RESOURCE_ID = "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
STAGED_ORDER_CLIENT = "demo.clients.StagedOrderClient"
MOCK_TOKEN = "test-demo-access-token"
DEMO_SETTINGS = {**WEBHOOK_SETTINGS, "UBER_ORDER_CLIENT": STAGED_ORDER_CLIENT}

# The demo app and its routes exist only when DEMO_ENABLED is true.
demo_only = skipUnless(settings.DEMO_ENABLED, "DEMO_ENABLED is not true")


def official_order(order_id: str, **changes) -> dict:
    order = json.loads(fixture_bytes("uber_get_order.json"))
    order.update(id=order_id, **changes)
    return order


def reload_root_urls() -> None:
    clear_url_caches()
    importlib.reload(importlib.import_module(settings.ROOT_URLCONF))


@demo_only
class StagingTests(SimpleTestCase):
    def setUp(self):
        staging.clear()

    def test_staged_order_is_a_copy(self):
        order = official_order("staged-1")
        staging.stage_order("staged-1", order)
        order["id"] = "changed"
        self.assertEqual(staging.staged_order("staged-1")["id"], "staged-1")

    def test_only_the_most_recent_orders_are_kept(self):
        for number in range(staging.MAX_STAGED_ORDERS + 1):
            staging.stage_order(f"order-{number}", {"id": f"order-{number}"})
        self.assertIsNone(staging.staged_order("order-0"))
        self.assertIsNotNone(staging.staged_order(f"order-{staging.MAX_STAGED_ORDERS}"))


@demo_only
@override_settings(UBER_GET_ORDER_FIXTURE=settings.REPO_ROOT / "fixtures" / "uber_get_order.json")
class StagedOrderClientTests(SimpleTestCase):
    def setUp(self):
        staging.clear()

    def test_a_staged_order_wins(self):
        staging.stage_order("staged-2", official_order("staged-2", current_state="ACCEPTED"))
        self.assertEqual(StagedOrderClient().get_order("staged-2")["current_state"], "ACCEPTED")

    def test_a_demo_file_is_used_when_nothing_is_staged(self):
        order = StagedOrderClient().get_order(DEMO_UBER_RESOURCE_ID)
        self.assertEqual(order["eater"]["first_name"], "Priya")

    def test_otherwise_the_official_sample_under_the_requested_id(self):
        order = StagedOrderClient().get_order("plain-id-1")
        self.assertEqual(order["id"], "plain-id-1")
        self.assertNotIn("placed_at", order)

    def test_unsafe_ids_are_rejected_before_any_lookup(self):
        for resource_id in ("../x", "a/b", "a" * 129):
            with self.subTest(resource_id=resource_id):
                with self.assertRaises(InvalidOrderPayload):
                    StagedOrderClient().get_order(resource_id)

    def test_demo_orders_have_no_placed_at_so_the_demo_shows_the_received_time(self):
        paths = list(DEMO_ORDERS_DIR.glob("*.json"))
        self.assertGreaterEqual(len(paths), 1)
        for path in paths:
            with self.subTest(path=path.name):
                self.assertNotIn("placed_at", json.loads(path.read_text()))


@demo_only
@override_settings(**DEMO_SETTINGS)
class StagedOrderWebhookTests(WebhookClientMixin, APITestCase):
    def setUp(self):
        staging.clear()

    def test_a_demo_order_file_named_after_the_id_is_used(self):
        self.post_uber(uber_webhook_for(DEMO_UBER_RESOURCE_ID))
        order = Order.objects.get()
        self.assertEqual(order.external_order_id, DEMO_UBER_RESOURCE_ID)
        self.assertEqual(order.customer_name, "Priya S.")
        self.assertEqual(order.total_cents, 1099)

    def test_a_staged_order_is_ingested(self):
        staging.stage_order(
            OFFICIAL_UBER_RESOURCE_ID,
            official_order(OFFICIAL_UBER_RESOURCE_ID, eater={"first_name": "Staged"}),
        )
        self.assertEqual(self.post_uber().status_code, 200)
        self.assertEqual(Order.objects.get().customer_name, "Staged")


@demo_only
@override_settings(UBER_ACCESS_TOKEN=MOCK_TOKEN, **DEMO_SETTINGS)
class MockUberEndpointTests(APITestCase):
    def setUp(self):
        staging.clear()

    def get_order(self, order_id: str, token: str | None = MOCK_TOKEN):
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
        return self.client.get(reverse("demo-mock-uber-get-order", args=[order_id]), **headers)

    def test_a_bearer_token_is_required(self):
        self.assertEqual(self.get_order("abc-1", token=None).status_code, 401)
        self.assertEqual(self.get_order("abc-1", token="wrong").status_code, 401)

    def test_returns_the_official_sample_under_the_requested_id(self):
        response = self.get_order("abc-1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], "abc-1")

    def test_returns_the_staged_order_when_there_is_one(self):
        staging.stage_order("abc-2", official_order("abc-2", current_state="FINISHED"))
        self.assertEqual(self.get_order("abc-2").json()["current_state"], "FINISHED")

    def test_an_unsafe_id_is_not_found(self):
        self.assertEqual(self.get_order("a" * 129).status_code, 404)


# The live server's static-file handler needs STATIC_URL, which the API never sets.
@demo_only
@override_settings(STATIC_URL="/static/", UBER_ACCESS_TOKEN=MOCK_TOKEN, **DEMO_SETTINGS)
class HttpOrderClientThroughMockTests(LiveServerTestCase):
    def test_the_real_http_client_reads_a_staged_order_from_the_mock(self):
        staging.clear()
        staging.stage_order("via-http-1", official_order("via-http-1", current_state="ACCEPTED"))
        client = HttpOrderClient(api_base=f"{self.live_server_url}/demo/mock/uber")
        self.assertEqual(client.get_order("via-http-1")["current_state"], "ACCEPTED")


@demo_only
class DemoSwitchTests(APITestCase):
    def test_demo_routes_are_not_mounted_when_disabled(self):
        self.addCleanup(reload_root_urls)
        with self.settings(DEMO_ENABLED=False):
            reload_root_urls()
            responses = [
                self.client.get("/demo/mock/uber/v2/eats/order/abc-1"),
                self.client.get("/demo/api/config"),
                self.client.post("/demo/api/send", {"provider": "doordash"}, format="json"),
            ]
        self.assertEqual([response.status_code for response in responses], [404, 404, 404])


CUSTOM_ITEMS = [
    {"name": "Test Wrap", "quantity": 2, "unit_price_cents": 650},
    {"name": "Test Tea", "quantity": 1, "unit_price_cents": 300},
]
CUSTOM_TOTAL_CENTS = 2 * 650 + 300
TEST_CUSTOMER = {"first_name": "Test", "last_name": "Person", "phone": "+15550100"}


def client_sender(client, lock=None):
    """Routes the simulator's webhook calls through Django's test client."""

    def send(url: str, body: bytes, headers: dict[str, str]):
        meta = {
            "HTTP_" + name.upper().replace("-", "_"): value
            for name, value in headers.items()
            if name.lower() != "content-type"
        }
        with lock or contextlib.nullcontext():
            try:
                response = client.generic(
                    "POST", urlsplit(url).path, data=body, content_type="application/json", **meta
                )
            finally:
                # A thread that is not the test's own opens its own connection.
                if threading.current_thread() is not threading.main_thread():
                    connections.close_all()
        return response.status_code, response.content.decode()

    return send


class SimulatorClientMixin:
    def send(self, sender=None, **options):
        sender = sender or client_sender(self.client)
        with mock.patch.object(SimulatorSendView, "sender", staticmethod(sender)):
            return self.client.post(reverse("demo-simulator-send"), options, format="json")


@demo_only
@override_settings(**DEMO_SETTINGS)
class SimulatorBuilderTests(SimpleTestCase):
    def setUp(self):
        staging.clear()

    def build_all(self):
        customer = builders.Customer("Test", "Person", "+15550100")
        items = (builders.Item("Test Wrap", 2, 650),)
        for preset in builders.PRESETS:
            yield preset, "uber", builders.build_uber_notification(f"uber-{preset}", preset), (
                builders.build_uber_order(f"uber-{preset}", preset, customer, items, "ACCEPTED")
            )
            yield preset, "doordash", builders.build_doordash_webhook(
                f"dd-{preset}", preset, customer, items
            ), None

    def test_every_built_payload_passes_the_core_detection_and_validation(self):
        for preset, provider_name, payload, order in self.build_all():
            with self.subTest(preset=preset, provider=provider_name):
                provider = ingest.find_provider(payload)
                if provider_name == "uber":
                    self.assertIsInstance(provider, UberProvider)
                    staging.stage_order(payload["meta"]["resource_id"], order)
                    provider = UberProvider(order_client=StagedOrderClient())
                else:
                    self.assertIsInstance(provider, DoorDashProvider)
                provider.build_order(payload)

    def test_every_uber_state_the_simulator_offers_is_accepted_by_the_core(self):
        customer = builders.Customer("Test")
        items = (builders.Item("Test Wrap", 1, 650),)
        for state in builders.UBER_STATES:
            with self.subTest(state=state):
                order_id = f"state-{state.lower()}"
                order = builders.build_uber_order(order_id, "custom", customer, items, state)
                self.assertEqual(order["current_state"], state)
                staging.stage_order(order_id, order)
                payload = builders.build_uber_notification(order_id, "custom")
                UberProvider(order_client=StagedOrderClient()).build_order(payload)

    def test_the_official_preset_keeps_the_sample_state_whatever_state_is_chosen(self):
        sample_state = json.loads(fixture_bytes("uber_get_order.json"))["current_state"]
        for state in builders.UBER_STATES:
            with self.subTest(state=state):
                order = builders.build_uber_order(
                    "official-1", "official", builders.Customer(), (), state
                )
                self.assertEqual(order["current_state"], sample_state)

    def test_the_uber_signature_is_accepted_by_the_core_verifier(self):
        body = json.dumps(builders.build_uber_notification("sig-1", "random")).encode()
        valid, _ = uber_headers(body, valid=True)
        invalid, _ = uber_headers(body, valid=False)
        self.assertTrue(UberProvider().authenticate(body, valid))
        self.assertFalse(UberProvider().authenticate(body, invalid))

    def test_doordash_items_stay_under_categories(self):
        payload = builders.build_doordash_webhook(
            "dd-1", "custom", builders.Customer(), (builders.Item("Wrap", 1, 100),)
        )
        self.assertNotIn("items", payload["order"])
        self.assertEqual(payload["order"]["categories"][0]["items"][0]["name"], "Wrap")

    def test_custom_uber_order_has_matching_totals_and_a_current_date(self):
        order = builders.build_uber_order(
            "uber-1", "custom", builders.Customer("A"), (builders.Item("Wrap", 2, 650),), "CREATED"
        )
        charges = order["payment"]["charges"]
        self.assertEqual(charges["total"]["amount"], 1300)
        self.assertEqual(charges["sub_total"]["amount"], 1300)
        self.assertEqual(charges["tax"]["amount"], 0)
        self.assertFalse(order["placed_at"].startswith("2019"))

    def test_the_official_fixtures_are_never_changed(self):
        paths = (builders.UBER_WEBHOOK_FIXTURE, builders.UBER_GET_ORDER_FIXTURE, builders.DOORDASH_FIXTURE)
        before = [path.read_bytes() for path in paths]
        list(self.build_all())
        self.assertEqual([path.read_bytes() for path in paths], before)

    def test_invalid_options_are_rejected(self):
        cases = [
            [],
            {"provider": "swiggy"},
            {"provider": "doordash", "colour": "red"},
            {"provider": "doordash", "preset": "custom"},
            {"provider": "doordash", "order_id": "../x"},
            {"provider": "doordash", "deliveries": 3},
            {"provider": "doordash", "deliveries": True},
            {"provider": "uber_eats", "uber_state": "PREPARING"},
            {"provider": "doordash", "auth": "maybe"},
            {"provider": "doordash", "items": [{"name": "A", "quantity": 100, "unit_price_cents": 1}]},
            {"provider": "doordash", "items": [{"name": "A", "quantity": 1, "unit_price_cents": 100001}]},
            {"provider": "doordash", "items": [{"name": "A", "quantity": 1.5, "unit_price_cents": 1}]},
            {"provider": "doordash", "items": [{"name": "", "quantity": 1, "unit_price_cents": 1}]},
            {"provider": "doordash", "items": [{"name": "A", "quantity": 1, "unit_price_cents": 1}] * 21},
            {"provider": "doordash", "customer": {"first_name": 5}},
        ]
        for options in cases:
            with self.subTest(options=options):
                with self.assertRaises(builders.InvalidOptions):
                    builders.parse_options(options)


@demo_only
@override_settings(**DEMO_SETTINGS)
class SimulatorEndpointTests(SimulatorClientMixin, APITestCase):
    def setUp(self):
        staging.clear()

    def test_config_lists_the_options(self):
        body = self.client.get(reverse("demo-simulator-config")).json()
        self.assertTrue(body["enabled"])
        self.assertEqual(body["presets"], ["official", "random", "custom"])
        self.assertIn("CANCELED", body["uber_states"])

    def test_a_custom_uber_order_arrives_with_the_chosen_details(self):
        response = self.send(
            provider="uber_eats", preset="custom", customer=TEST_CUSTOMER,
            items=CUSTOM_ITEMS, uber_state="ACCEPTED",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["deliveries"][0]["status"], 200)
        order = Order.objects.get()
        self.assertEqual(order.customer_name, "Test Person")
        self.assertEqual(order.customer_phone, "+15550100")
        self.assertEqual(order.status, "accepted")
        self.assertEqual(order.total_cents, CUSTOM_TOTAL_CENTS)
        self.assertEqual([item["name"] for item in order.line_items], ["Test Wrap", "Test Tea"])

    def test_a_custom_doordash_order_arrives_and_is_confirmed(self):
        response = self.send(
            provider="doordash", preset="custom", customer=TEST_CUSTOMER, items=CUSTOM_ITEMS
        )
        delivery = response.json()["deliveries"][0]
        self.assertEqual(delivery["status"], 200)
        self.assertIn('"order_status":"success"', delivery["body"])
        self.assertEqual(Order.objects.get().total_cents, CUSTOM_TOTAL_CENTS)

    def test_invalid_auth_gives_401_and_saves_nothing(self):
        for provider in builders.PROVIDERS:
            with self.subTest(provider=provider):
                response = self.send(provider=provider, preset="random", auth="invalid")
                self.assertEqual(response.json()["deliveries"][0]["status"], 401)
        self.assertEqual(Order.objects.count(), 0)

    def test_reusing_an_order_id_updates_the_same_row(self):
        first = self.send(provider="doordash", preset="custom", customer=TEST_CUSTOMER, items=CUSTOM_ITEMS)
        order_id = first.json()["order_id"]
        self.send(
            provider="doordash", preset="custom", order_id=order_id,
            customer={**TEST_CUSTOMER, "first_name": "Changed"}, items=CUSTOM_ITEMS,
        )
        order = Order.objects.get()
        self.assertEqual(order.external_order_id, order_id)
        self.assertEqual(order.customer_name, "Changed Person")

    def test_the_last_order_id_is_remembered_per_provider(self):
        order_id = self.send(provider="uber_eats", preset="official").json()["order_id"]
        config = self.client.get(reverse("demo-simulator-config")).json()
        self.assertEqual(config["last_order_ids"], {"uber_eats": order_id})

    def test_secrets_are_never_returned(self):
        dd = self.send(provider="doordash", preset="official").json()["sent"]["headers"]
        uber = self.send(provider="uber_eats", preset="official").json()["sent"]["headers"]
        self.assertNotIn(settings.DOORDASH_WEBHOOK_AUTH_HEADER, json.dumps(dd))
        self.assertTrue(dd["Authorization"].endswith("0001"))
        self.assertIn("X-Uber-Signature", uber)
        self.assertNotIn(settings.UBER_CLIENT_SECRET, json.dumps(uber))

    def copy_curl(self, **options):
        return self.client.post(reverse("demo-simulator-curl"), options, format="json")

    @staticmethod
    def curl_parts(curl: str) -> list[str]:
        # The command follows the optional .env lines after a blank line.
        command = curl.split("\n\n")[-1]
        return shlex.split(command.replace(" \\\n  ", " "))

    def run_copied_curl(self, curl: str):
        parts = self.curl_parts(curl)
        body = parts[parts.index("--data-binary") + 1].encode()
        headers = dict(
            parts[index + 1].split(": ", 1) for index, part in enumerate(parts) if part == "-H"
        )
        signature = headers.get("X-Uber-Signature")
        meta = {"HTTP_X_UBER_SIGNATURE": signature} if signature else {
            "HTTP_AUTHORIZATION": settings.DOORDASH_WEBHOOK_AUTH_HEADER
        }
        return self.client.generic(
            "POST", reverse("webhook-orders"), data=body, content_type="application/json", **meta
        )

    def test_copying_a_curl_sends_nothing(self):
        with mock.patch.object(SimulatorSendView, "sender") as sender:
            response = self.copy_curl(provider="doordash", preset="random")
        self.assertEqual(response.status_code, 200)
        sender.assert_not_called()
        self.assertEqual(Order.objects.count(), 0)

    def test_each_copy_gets_a_new_order_id(self):
        first = self.copy_curl(provider="uber_eats", preset="random").json()["order_id"]
        second = self.copy_curl(provider="uber_eats", preset="random").json()["order_id"]
        self.assertNotEqual(first, second)
        self.assertEqual(self.client.get(reverse("demo-simulator-config")).json()["last_order_ids"], {})

    def test_running_a_copied_uber_curl_creates_the_chosen_order(self):
        copied = self.copy_curl(
            provider="uber_eats", preset="custom", customer=TEST_CUSTOMER, items=CUSTOM_ITEMS
        ).json()
        self.assertNotIn(settings.UBER_CLIENT_SECRET, copied["curl"])
        self.assertEqual(self.run_copied_curl(copied["curl"]).status_code, 200)
        order = Order.objects.get()
        self.assertEqual(order.external_order_id, copied["order_id"])
        self.assertEqual(order.customer_name, "Test Person")
        self.assertEqual(order.total_cents, CUSTOM_TOTAL_CENTS)

    def test_two_copied_curls_create_two_orders(self):
        for _ in range(2):
            curl = self.copy_curl(provider="doordash", preset="random").json()["curl"]
            self.assertEqual(self.run_copied_curl(curl).status_code, 200)
        self.assertEqual(Order.objects.count(), 2)

    def test_doordash_curl_reads_the_token_from_env(self):
        curl = self.copy_curl(provider="doordash", preset="official").json()["curl"]
        self.assertIn("set -a; source .env; set +a", curl)
        self.assertIn('-H "Authorization: $DOORDASH_WEBHOOK_AUTH_HEADER"', curl)
        self.assertNotIn(settings.DOORDASH_WEBHOOK_AUTH_HEADER, curl)

    def test_doordash_curl_for_invalid_auth_uses_a_wrong_token(self):
        curl = self.copy_curl(provider="doordash", preset="official", auth="invalid").json()["curl"]
        self.assertNotIn("source .env", curl)
        self.assertIn("Bearer not-the-configured-token", curl)
        self.assertNotIn(settings.DOORDASH_WEBHOOK_AUTH_HEADER[:-1], curl)

    def test_copying_with_invalid_options_returns_400(self):
        self.assertEqual(self.copy_curl(provider="swiggy").status_code, 400)

    def test_invalid_options_return_400(self):
        response = self.client.post(
            reverse("demo-simulator-send"), {"provider": "swiggy"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("provider", response.json()["detail"])


@demo_only
@override_settings(**DEMO_SETTINGS)
class SimulatorConcurrentDeliveryTests(SimulatorClientMixin, APITransactionTestCase):
    def test_two_deliveries_at_once_leave_one_row_and_two_200s(self):
        # The test client is not thread-safe, so its calls take turns here;
        # real overlapping requests are covered by the parallel curl checks.
        sender = client_sender(self.client, threading.Lock())
        response = self.send(sender=sender, provider="doordash", preset="random", deliveries=2)
        statuses = [delivery["status"] for delivery in response.json()["deliveries"]]
        self.assertEqual(statuses, [200, 200])
        self.assertEqual(Order.objects.count(), 1)


# The live server's static-file handler needs STATIC_URL, which the API never sets.
@demo_only
@override_settings(STATIC_URL="/static/", **DEMO_SETTINGS)
class SimulatorRealHttpTests(LiveServerTestCase):
    def test_a_custom_uber_order_travels_over_real_http(self):
        staging.clear()
        options = {
            "provider": "uber_eats", "preset": "custom",
            "customer": TEST_CUSTOMER, "items": CUSTOM_ITEMS,
        }
        request = urllib.request.Request(
            f"{self.live_server_url}/demo/api/send",
            data=json.dumps(options).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            body = json.loads(response.read())
        self.assertEqual(body["deliveries"][0]["status"], 200)
        self.assertEqual(Order.objects.get().total_cents, CUSTOM_TOTAL_CENTS)
