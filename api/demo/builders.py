import json
import random
import re
import secrets
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from django.conf import settings

from orders.providers.uber import STATUS_MAP

FIXTURES_DIR = settings.REPO_ROOT / "fixtures"
UBER_WEBHOOK_FIXTURE = FIXTURES_DIR / "uber_webhook.json"
UBER_GET_ORDER_FIXTURE = FIXTURES_DIR / "uber_get_order.json"
DOORDASH_FIXTURE = FIXTURES_DIR / "doordash_order.json"

PROVIDER_UBER = "uber_eats"
PROVIDER_DOORDASH = "doordash"
PROVIDERS = (PROVIDER_UBER, PROVIDER_DOORDASH)
PRESET_OFFICIAL = "official"
PRESET_RANDOM = "random"
PRESET_CUSTOM = "custom"
PRESETS = (PRESET_OFFICIAL, PRESET_RANDOM, PRESET_CUSTOM)
UBER_STATES = tuple(STATUS_MAP)
DEFAULT_UBER_STATE = "CREATED"
AUTH_VALID = "valid"
AUTH_INVALID = "invalid"
NEW_ORDER_ID = "new"
ALLOWED_DELIVERIES = (1, 2)

MAX_ITEMS = 20
MAX_QUANTITY = 99
MAX_UNIT_PRICE_CENTS = 100_000
MAX_TEXT_LENGTH = 100
MAX_PHONE_LENGTH = 32
MAX_NOTES_LENGTH = 200
ORDER_ID_PATTERN = r"[A-Za-z0-9_-]{1,64}"
DOORDASH_ID_PREFIX = "dd-"
DOORDASH_ID_BYTES = 3
UBER_DISPLAY_ID_LENGTH = 5
CURRENCY_SYMBOLS = {"USD": "$"}

OPTION_KEYS = {
    "provider", "preset", "order_id", "customer", "items", "uber_state", "auth", "deliveries",
}
CUSTOMER_KEYS = {"first_name", "last_name", "phone"}
REQUIRED_ITEM_KEYS = {"name", "quantity", "unit_price_cents"}
ITEM_KEYS = REQUIRED_ITEM_KEYS | {"notes"}

RANDOM_FIRST_NAMES = ("Maya", "Jonas", "Priya", "Lucas", "Amara", "Diego", "Hana", "Omar")
RANDOM_LAST_INITIALS = ("R.", "K.", "S.", "M.", "T.", "L.", "N.", "B.")
RANDOM_MENU = (
    ("Breakfast Wrap", 1280),
    ("Chicken Burrito", 1150),
    ("Veggie Bowl", 1050),
    ("Iced Latte", 475),
    ("Blueberry Muffin", 350),
    ("Fries", 399),
)
RANDOM_MAX_ITEMS = 3
RANDOM_MAX_QUANTITY = 2


class InvalidOptions(Exception):
    """The simulator options are not acceptable."""


@dataclass(frozen=True)
class Customer:
    first_name: str = ""
    last_name: str = ""
    phone: str = ""


@dataclass(frozen=True)
class Item:
    name: str
    quantity: int
    unit_price_cents: int
    notes: str = ""

    @property
    def line_total_cents(self) -> int:
        return self.quantity * self.unit_price_cents


@dataclass(frozen=True)
class Options:
    provider: str
    preset: str
    order_id: str
    customer: Customer
    items: tuple[Item, ...]
    uber_state: str
    auth_valid: bool
    deliveries: int


def parse_options(data: Any) -> Options:
    if not isinstance(data, dict):
        raise InvalidOptions("The body must be a JSON object.")
    unknown = set(data) - OPTION_KEYS
    if unknown:
        raise InvalidOptions(f"Unknown option: {sorted(unknown)[0]}.")
    preset = _choice(data.get("preset", PRESET_OFFICIAL), PRESETS, "preset")
    items = _items(data.get("items", []))
    if preset == PRESET_CUSTOM and not items:
        raise InvalidOptions("A custom order needs at least one item.")
    return Options(
        provider=_choice(data.get("provider"), PROVIDERS, "provider"),
        preset=preset,
        order_id=_order_id(data.get("order_id", NEW_ORDER_ID)),
        customer=_customer(data.get("customer", {})),
        items=items,
        uber_state=_choice(data.get("uber_state", DEFAULT_UBER_STATE), UBER_STATES, "uber_state"),
        auth_valid=_choice(data.get("auth", AUTH_VALID), (AUTH_VALID, AUTH_INVALID), "auth")
        == AUTH_VALID,
        deliveries=_choice(data.get("deliveries", 1), ALLOWED_DELIVERIES, "deliveries"),
    )


def _choice(value: Any, allowed: tuple, field: str) -> Any:
    # bool is an int, so `True` would otherwise match the delivery count 1.
    if isinstance(value, bool) or value not in allowed:
        raise InvalidOptions(f"{field} must be one of: {', '.join(map(str, allowed))}.")
    return value


def _order_id(value: Any) -> str:
    if value == NEW_ORDER_ID:
        return value
    if not isinstance(value, str) or not re.fullmatch(ORDER_ID_PATTERN, value):
        raise InvalidOptions(
            "order_id must be \"new\" or 1 to 64 letters, digits, - and _."
        )
    return value


def _text(value: Any, field: str, max_length: int) -> str:
    if not isinstance(value, str) or len(value) > max_length:
        raise InvalidOptions(f"{field} must be text of at most {max_length} characters.")
    return value.strip()


def _notes(value: Any) -> str:
    # Notes are optional extras, so anything that is not text becomes empty,
    # and long text is cut at the cap instead of failing the whole order.
    return value.strip()[:MAX_NOTES_LENGTH] if isinstance(value, str) else ""


def _whole_number(value: Any, field: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise InvalidOptions(f"{field} must be a whole number from {minimum} to {maximum}.")
    return value


def _customer(value: Any) -> Customer:
    if not isinstance(value, dict) or set(value) - CUSTOMER_KEYS:
        raise InvalidOptions("customer must be an object with first_name, last_name and phone.")
    return Customer(
        first_name=_text(value.get("first_name", ""), "customer.first_name", MAX_TEXT_LENGTH),
        last_name=_text(value.get("last_name", ""), "customer.last_name", MAX_TEXT_LENGTH),
        phone=_text(value.get("phone", ""), "customer.phone", MAX_PHONE_LENGTH),
    )


def _items(value: Any) -> tuple[Item, ...]:
    if not isinstance(value, list) or len(value) > MAX_ITEMS:
        raise InvalidOptions(f"items must be a list of at most {MAX_ITEMS} items.")
    return tuple(_item(item) for item in value)


def _item(value: Any) -> Item:
    if not isinstance(value, dict) or not REQUIRED_ITEM_KEYS <= set(value) <= ITEM_KEYS:
        raise InvalidOptions(
            "Each item needs name, quantity and unit_price_cents, and may have notes."
        )
    name = _text(value["name"], "item name", MAX_TEXT_LENGTH)
    if not name:
        raise InvalidOptions("Each item needs a name.")
    return Item(
        name=name,
        quantity=_whole_number(value["quantity"], "item quantity", 1, MAX_QUANTITY),
        unit_price_cents=_whole_number(
            value["unit_price_cents"], "item unit_price_cents", 0, MAX_UNIT_PRICE_CENTS
        ),
        notes=_notes(value.get("notes")),
    )


def new_order_id(provider: str) -> str:
    if provider == PROVIDER_UBER:
        return str(uuid.uuid4())
    return DOORDASH_ID_PREFIX + secrets.token_hex(DOORDASH_ID_BYTES)


def order_content(options: Options) -> tuple[Customer, tuple[Item, ...]]:
    if options.preset == PRESET_RANDOM:
        return _random_customer(), _random_items()
    return options.customer, options.items


def _random_customer() -> Customer:
    return Customer(
        first_name=random.choice(RANDOM_FIRST_NAMES),
        last_name=random.choice(RANDOM_LAST_INITIALS),
        phone="+1555" + "".join(random.choices("0123456789", k=7)),
    )


def _random_items() -> tuple[Item, ...]:
    dishes = random.sample(RANDOM_MENU, random.randint(1, RANDOM_MAX_ITEMS))
    return tuple(
        Item(name=name, quantity=random.randint(1, RANDOM_MAX_QUANTITY), unit_price_cents=price)
        for name, price in dishes
    )


def _load(path) -> dict[str, Any]:
    # Read from disk on every call, so a built payload can never share
    # objects with (or change) the official sample.
    return json.loads(path.read_text())


def build_uber_notification(order_id: str, preset: str) -> dict[str, Any]:
    notification = _load(UBER_WEBHOOK_FIXTURE)
    notification["meta"]["resource_id"] = order_id
    notification["resource_href"] = notification["resource_href"].rsplit("/", 1)[0] + "/" + order_id
    if preset != PRESET_OFFICIAL:
        notification["event_id"] = str(uuid.uuid4())
        notification["event_time"] = int(time.time())
    return notification


def build_uber_order(
    order_id: str,
    preset: str,
    customer: Customer,
    items: tuple[Item, ...],
    uber_state: str,
) -> dict[str, Any]:
    order = _load(UBER_GET_ORDER_FIXTURE)
    order["id"] = order_id
    order["display_id"] = order_id[-UBER_DISPLAY_ID_LENGTH:]
    if preset == PRESET_OFFICIAL:
        # Same as the official sample reused by the core: the 2019 date is dropped.
        order.pop("placed_at", None)
        return order
    charges = order["payment"]["charges"]
    currency = charges["total"]["currency_code"]
    template = order["cart"]["items"][0]
    order["current_state"] = uber_state
    order["eater"] = _uber_eater(order["eater"], customer)
    order["cart"]["items"] = [
        _uber_item(template, number, item, currency) for number, item in enumerate(items, 1)
    ]
    total = sum(item.line_total_cents for item in items)
    charges["total"] = _money(total, currency)
    charges["sub_total"] = _money(total, currency)
    charges["tax"] = _money(0, currency)
    order["placed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return order


def _uber_eater(eater: dict[str, Any], customer: Customer) -> dict[str, Any]:
    changed = {**eater, "first_name": customer.first_name, "phone": customer.phone}
    if customer.last_name:
        changed["last_name"] = customer.last_name
    return changed


def _uber_item(template: dict[str, Any], number: int, item: Item, currency: str) -> dict[str, Any]:
    built = json.loads(json.dumps(template))
    unit = _money(item.unit_price_cents, currency)
    line = _money(item.line_total_cents, currency)
    built.update(
        id=f"item-{number}",
        instance_id=f"item-{number}",
        title=item.name,
        quantity=item.quantity,
        selected_modifier_groups=[],
    )
    built["price"].update(
        unit_price=unit,
        total_price=line,
        base_unit_price=unit,
        base_non_loyalty_unit_price=unit,
        base_total_price=line,
    )
    if item.notes:
        built["special_instructions"] = item.notes
    return built


def _money(amount: int, currency: str) -> dict[str, Any]:
    symbol = CURRENCY_SYMBOLS.get(currency, f"{currency} ")
    return {
        "amount": amount,
        "currency_code": currency,
        "formatted_amount": f"{symbol}{amount / 100:.2f}",
    }


def _doordash_item(template: dict[str, Any], number: int, item: Item) -> dict[str, Any]:
    built = {
        **template,
        "extras": [],
        "merchant_supplied_id": f"item-{number}",
        "name": item.name,
        "price": item.unit_price_cents,
        "quantity": item.quantity,
    }
    if item.notes:
        built["special_instructions"] = item.notes
    return built


def build_doordash_webhook(
    order_id: str, preset: str, customer: Customer, items: tuple[Item, ...]
) -> dict[str, Any]:
    payload = _load(DOORDASH_FIXTURE)
    order = payload["order"]
    order["id"] = order_id
    if preset == PRESET_OFFICIAL:
        return payload
    order["consumer"].update(
        first_name=customer.first_name, last_name=customer.last_name, phone=customer.phone
    )
    template = order["categories"][0]["items"][0]
    order["categories"][0]["items"] = [
        _doordash_item(template, number, item) for number, item in enumerate(items, 1)
    ]
    order["subtotal"] = sum(item.line_total_cents for item in items)
    order["tax"] = 0
    return payload
