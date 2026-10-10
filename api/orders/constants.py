from django.db.models import Case, F, IntegerField, Value, When
from django.db.models.functions import Lower

PROVIDER_UBER = "uber"
PROVIDER_DOORDASH = "doordash"
PROVIDER_CHOICES = [
    (PROVIDER_UBER, "Uber Eats"),
    (PROVIDER_DOORDASH, "DoorDash"),
]

STATUS_NEW = "new"
STATUS_ACCEPTED = "accepted"
STATUS_PREPARING = "preparing"
STATUS_READY = "ready"
STATUS_COMPLETED = "completed"
STATUS_CANCELLED = "cancelled"

STATUS_PROGRESSION = (
    STATUS_NEW,
    STATUS_ACCEPTED,
    STATUS_PREPARING,
    STATUS_READY,
    STATUS_COMPLETED,
)
STATUS_ORDER = STATUS_PROGRESSION + (STATUS_CANCELLED,)
STATUS_CHOICES = [(status, status) for status in STATUS_ORDER]
TERMINAL_STATUSES = frozenset({STATUS_COMPLETED, STATUS_CANCELLED})
EXPECTED_STATUS_FIELD = "expected_status"

UBER_SIGNATURE_HEADER = "X-Uber-Signature"
AUTHORIZATION_HEADER = "Authorization"

PAGE_FIELD = "page"
DEFAULT_ORDERING = "-created_at"
DESCENDING_PREFIX = "-"
STATUS_RANK = Case(
    *[When(status=status, then=Value(rank)) for rank, status in enumerate(STATUS_ORDER)],
    output_field=IntegerField(),
)
# The only values `ordering` may take (each optionally prefixed with "-").
ORDERING_EXPRESSIONS = {
    "provider": F("provider"),
    "external_order_id": F("external_order_id"),
    "customer_name": Lower("customer_name"),
    "status": STATUS_RANK,
    "total_cents": F("total_cents"),
    "created_at": F("created_at"),
}

MAX_CUSTOMER_NAME_LENGTH = 255
MAX_CUSTOMER_PHONE_LENGTH = 64
MAX_CUSTOMER_PHONE_CODE_LENGTH = 32
MAX_EXTERNAL_ID_LENGTH = 255
CURRENCY_CODE_LENGTH = 3
CURRENCY_CODE_PATTERN = r"[A-Z]{3}"
MAX_AMOUNT = 10**12
MIN_QUANTITY = 1

UBER_RESOURCE_ID_PATTERN = r"^[A-Za-z0-9_-]+$"
UBER_RESOURCE_ID_MAX_LENGTH = 128
UBER_ORDER_NOTIFICATION_EVENT = "orders.notification"
UBER_DISPLAY_ID_LENGTH = 5
UBER_GET_ORDER_PATH = "/v2/eats/order/{order_id}"
JSON_CONTENT_TYPE = "application/json"
BEARER_PREFIX = "Bearer "
