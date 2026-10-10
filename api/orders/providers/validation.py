import re
from typing import Any

from .. import constants
from .base import InvalidOrderPayload


def require_object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InvalidOrderPayload(f"{field} must be an object.")
    return value


def optional_object(value: Any, field: str) -> dict[str, Any]:
    return {} if value is None else require_object(value, field)


def require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise InvalidOrderPayload(f"{field} must be a list.")
    return value


def require_text(value: Any, field: str, max_length: int | None = None) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidOrderPayload(f"{field} must be a non-empty string.")
    return check_length(value, field, max_length)


def optional_text(value: Any, field: str, max_length: int | None = None) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise InvalidOrderPayload(f"{field} must be a string.")
    return check_length(value, field, max_length)


def check_length(value: str, field: str, max_length: int | None) -> str:
    if max_length is not None and len(value) > max_length:
        raise InvalidOrderPayload(f"{field} must be at most {max_length} characters.")
    return value


def require_integer(value: Any, field: str, minimum: int) -> int:
    # bool is a subclass of int, so it is excluded explicitly.
    is_integer = isinstance(value, int) and not isinstance(value, bool)
    if not is_integer or not minimum <= value < constants.MAX_AMOUNT:
        raise InvalidOrderPayload(
            f"{field} must be a whole number from {minimum} up to {constants.MAX_AMOUNT - 1}."
        )
    return value


def require_money(value: Any, field: str) -> int:
    return require_integer(value, field, minimum=0)


def require_quantity(value: Any, field: str) -> int:
    return require_integer(value, field, minimum=constants.MIN_QUANTITY)


def require_currency(value: Any, field: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(constants.CURRENCY_CODE_PATTERN, value):
        raise InvalidOrderPayload(f"{field} must be a three-letter uppercase currency code.")
    return value


def customer_name(person: dict[str, Any], field: str) -> str:
    parts = [
        optional_text(person.get("first_name"), f"{field}.first_name"),
        optional_text(person.get("last_name"), f"{field}.last_name"),
    ]
    name = " ".join(part for part in parts if part)
    return check_length(name, f"{field} name", constants.MAX_CUSTOMER_NAME_LENGTH)


def customer_phone(person: dict[str, Any], field: str) -> str:
    return optional_text(
        person.get("phone"), f"{field}.phone", constants.MAX_CUSTOMER_PHONE_LENGTH
    )
