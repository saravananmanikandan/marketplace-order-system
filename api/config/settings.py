import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent

load_dotenv(REPO_ROOT / ".env")

MIN_DOORDASH_AUTH_HEADER_LENGTH = 16
SQLITE_LOCK_TIMEOUT_SECONDS = 20


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(
            f"Missing required environment variable {name}. "
            "Copy .env.example to .env at the repository root and set it."
        )
    return value


def require_positive_int(name: str) -> int:
    raw_value = require_env(name)
    try:
        value = int(raw_value)
    except ValueError:
        value = 0
    if value < 1:
        raise ImproperlyConfigured(
            f"{name} must be a positive whole number, but it is {raw_value!r}."
        )
    return value


def resolve_repo_path(raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else REPO_ROOT / path


SECRET_KEY = require_env("DJANGO_SECRET_KEY")
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "orders",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        # IMMEDIATE takes the write lock when a transaction starts, so two
        # read-then-write transactions queue instead of failing with
        # "database is locked".
        "OPTIONS": {"transaction_mode": "IMMEDIATE", "timeout": SQLITE_LOCK_TIMEOUT_SECONDS},
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "UTC"

UBER_CLIENT_SECRET = require_env("UBER_CLIENT_SECRET")

DOORDASH_WEBHOOK_AUTH_HEADER = require_env("DOORDASH_WEBHOOK_AUTH_HEADER")
if len(DOORDASH_WEBHOOK_AUTH_HEADER) < MIN_DOORDASH_AUTH_HEADER_LENGTH:
    raise ImproperlyConfigured(
        "DOORDASH_WEBHOOK_AUTH_HEADER must be at least "
        f"{MIN_DOORDASH_AUTH_HEADER_LENGTH} characters."
    )

UBER_GET_ORDER_FIXTURE = resolve_repo_path(require_env("UBER_GET_ORDER_FIXTURE"))
UBER_DEMO_ORDERS_DIR = REPO_ROOT / "fixtures" / "demo" / "uber_orders"
DEFAULT_CURRENCY = require_env("DEFAULT_CURRENCY")
PAGE_SIZE = require_positive_int("PAGE_SIZE")

WEBHOOK_PROVIDERS = [
    "orders.providers.uber.UberProvider",
    "orders.providers.doordash.DoorDashProvider",
]
UBER_ORDER_CLIENT = os.environ.get(
    "UBER_ORDER_CLIENT", "orders.providers.uber.FixtureOrderClient"
).strip()
UBER_API_BASE = os.environ.get("UBER_API_BASE", "").strip()
UBER_ACCESS_TOKEN = os.environ.get("UBER_ACCESS_TOKEN", "").strip()
UBER_API_TIMEOUT_SECONDS = 5
MOCK_UBER_ENABLED = os.environ.get("MOCK_UBER_ENABLED", "false").lower() == "true"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}
