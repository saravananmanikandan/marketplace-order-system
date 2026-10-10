from typing import Any

from django.conf import settings

from orders.providers.uber import FixtureOrderClient, load_order_file, require_resource_id

from . import staging

DEMO_ORDERS_DIR = settings.REPO_ROOT / "fixtures" / "demo" / "uber_orders"


class StagedOrderClient(FixtureOrderClient):
    def get_order(self, resource_id: str) -> dict[str, Any]:
        resource_id = require_resource_id(resource_id)
        staged = staging.staged_order(resource_id)
        if staged is not None:
            return staged
        demo_path = DEMO_ORDERS_DIR / f"{resource_id}.json"
        if demo_path.is_file():
            return load_order_file(demo_path)
        return super().get_order(resource_id)
