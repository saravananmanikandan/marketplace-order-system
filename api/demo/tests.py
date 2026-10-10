import importlib
import json
from unittest import skipUnless

from django.conf import settings
from django.test import LiveServerTestCase, SimpleTestCase, override_settings
from django.urls import clear_url_caches, reverse
from rest_framework.test import APITestCase

from orders.models import Order
from orders.providers.base import InvalidOrderPayload
from orders.providers.uber import HttpOrderClient
from orders.tests import (
    OFFICIAL_UBER_RESOURCE_ID,
    WEBHOOK_SETTINGS,
    WebhookClientMixin,
    fixture_bytes,
    uber_webhook_for,
)

from . import staging
from .clients import DEMO_ORDERS_DIR, StagedOrderClient

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
            response = self.client.get("/demo/mock/uber/v2/eats/order/abc-1")
        self.assertEqual(response.status_code, 404)
