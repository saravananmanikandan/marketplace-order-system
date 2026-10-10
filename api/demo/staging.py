import copy
import threading
from collections import OrderedDict
from typing import Any

MAX_STAGED_ORDERS = 100

# Process memory only: staged orders are lost when the server restarts.
_lock = threading.Lock()
_orders: OrderedDict[str, dict[str, Any]] = OrderedDict()
_last_order_ids: dict[str, str] = {}


def stage_order(order_id: str, order: dict[str, Any]) -> None:
    with _lock:
        _orders[order_id] = copy.deepcopy(order)
        _orders.move_to_end(order_id)
        while len(_orders) > MAX_STAGED_ORDERS:
            _orders.popitem(last=False)


def staged_order(order_id: str) -> dict[str, Any] | None:
    with _lock:
        order = _orders.get(order_id)
        return copy.deepcopy(order) if order is not None else None


def remember_last_order_id(provider: str, order_id: str) -> None:
    with _lock:
        _last_order_ids[provider] = order_id


def last_order_ids() -> dict[str, str]:
    with _lock:
        return dict(_last_order_ids)


def clear() -> None:
    with _lock:
        _orders.clear()
        _last_order_ids.clear()
