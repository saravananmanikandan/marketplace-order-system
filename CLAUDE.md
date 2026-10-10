# Order ingestion service

Marketplace orders from Uber Eats and DoorDash arrive through one webhook endpoint, are normalized into a single internal order model, and are managed in a React admin.

## Layout

- `api/` Django and Django REST Framework, app `orders`, SQLite; `api/demo/` is the demo-only app
- `admin/` React and Vite admin interface; `admin/src/demo/` is the demo-only UI
- `fixtures/` official provider sample payloads, `fixtures/demo/` demo variants
- `scripts/` helpers that send the sample webhooks to a running server
- `docs/` design decisions and documentation verification notes

## Commands

Run from the repository root with the virtual environment active.

```
python3 -m venv .venv && source .venv/bin/activate
pip install -r api/requirements.txt
cp .env.example .env
cd api && python manage.py migrate && python manage.py runserver
cd api && python manage.py test
cd admin && npm install && npm run dev
```

Configuration lives in `.env` at the repository root. `.env.example` lists every variable. `.env` is never committed.

## Sources of truth

The official provider documentation is authoritative. When it disagrees with anything in this file or in a brief, the documentation wins and the difference is recorded in `docs/verification-notes.md`.

- https://developer.uber.com/docs/eats/references/api/webhooks.orders-notification
- https://developer.uber.com/docs/eats/references/api/v2/get-eats-order-orderid
- https://developer.doordash.com/en-US/docs/marketplace/how_to/order_integration/
- https://developer.doordash.com/en-US/docs/marketplace/reference/sample_order
- https://developer.doordash.com/en-US/docs/marketplace/how_to/create_webhook_subscription

Read only fields that appear in the official documentation or sample payloads. Where the documentation is silent, record the decision in `docs/decisions.md`.

## Code conventions

- Small functions with names that carry the meaning. Comments explain why, never what. No commented-out code, TODO markers or banner comments.
- No magic values. Secrets, header names, fixture paths, status maps, default currency and page size live in settings or a constants module.
- No duplicated logic.
- Python: type hints on functions. Use `hmac` and `hashlib` from the standard library, and `hmac.compare_digest` for every secret comparison.
- Money is integer cents in the backend. Formatting as currency happens only in the frontend.
- Frontend: function components and hooks, a single `api` module for all requests, plain CSS, no component library.
- Dependencies stay minimal. Backend: Django, djangorestframework, python-dotenv. Frontend: react, react-dom, react-router-dom, @tanstack/react-query, vite.
- Validate every value from a webhook at the boundary. Invalid input is a 400 (or 502 for a failed upstream call), never a 500 or a stored default.
- Never edit official provider samples except to make them valid JSON. Keep the original text beside the corrected file.
- Every documented provider behaviour the code relies on is cited in docs/verification-notes.md with the page and section.

## Architecture

- A `Provider` interface in `providers/base.py` defines `matches(payload) -> bool`, `authenticate(raw_body, headers) -> bool` and `build_order(payload) -> OrderData`. `UberProvider` and `DoorDashProvider` implement it. `OrderData` is a plain dataclass holding the internal order fields.
- Enabled providers are listed in settings as dotted paths and loaded by `registry.py`. The ingest service iterates over them, so a new provider is one new class and one settings entry. The view and the ingest service do not change.
- Uber's order lookup is behind an `OrderClient` interface with one method, `get_order(resource_id)`. `FixtureOrderClient` is the default. `HttpOrderClient` calls `GET {UBER_API_BASE}/v2/eats/order/{resource_id}` with `Authorization: Bearer {UBER_ACCESS_TOKEN}` and a 5 second timeout using only `urllib.request`; network errors, non-2xx responses, invalid JSON and a returned `id` that differs from `resource_id` are lookup failures (502, nothing saved). The class in use is the dotted path in `UBER_ORDER_CLIENT`, so switching is configuration only. The local stand-in for Get Order is demo-only and lives in the demo app (`GET /demo/mock/uber/v2/eats/order/<id>`).
- Providers receive secrets and clients from settings. Nothing provider-specific is hardcoded in views, the ingest service or the frontend.
- Each provider owns its status mapping into the shared vocabulary in `constants.py`.
- Orders are persisted in exactly one place, the ingest service.
- The webhook view is a plain `APIView`. Read the raw body before anything else, because signatures are computed over the raw bytes.

## Provider reference

### Uber Eats

Webhook:
- POST with JSON containing `event_type` (`orders.notification`), `event_id`, `event_time`, `meta` (`resource_id`, `status`, `user_id`) and `resource_href`. It does not contain the cart, customer or totals. `meta.status` is the notification type (the docs list `pos`), not the order state, so it is never mapped to an order status. `meta.resource_id` is documented as equivalent to the order id.
- Header `X-Uber-Signature` holds the lowercase hex HMAC-SHA256 of the raw request body, keyed with the client secret.
- Respond HTTP 200 with an empty body. Without a 200, Uber resends with exponential backoff until 7 events have been sent. Delivery is not guaranteed to be in order, which is why ingestion is idempotent and status only moves forward.
- After acknowledging, the integration must call accept or deny within 11.5 minutes or the order auto-cancels. That is an outbound call, so it is not implemented and is recorded in the going-live list.

The full order is then fetched with Get Order using `meta.resource_id`. In production this call needs an OAuth 2.0 bearer token with the `eats.order` or `eats.store.orders.read` scope. Fields used:
- `id`, `display_id`, `current_state` (CREATED, ACCEPTED, DENIED, FINISHED, CANCELED, UNKNOWN)
- `placed_at`, optional, ISO 8601 with offset. When it is missing, malformed or has no offset, `created_at` is the time the webhook was received and the bad value is logged.
- `eater`: `first_name`, `last_name` (the initial, only sometimes present), `phone` (anonymized) and `phone_code`
- `cart.items[]`: `title`, `quantity`, `price.unit_price`, `price.total_price`. Prices include selected options. Modifiers are under `selected_modifier_groups` and stay in `raw_payload`.
- `payment.charges.total`: the order total, used directly as `total_cents`. In regions where Uber remits tax, it excludes that tax. `total` is optional, so when it is missing `sub_total + tax` is used, and an order with neither `total` nor `sub_total` is a 400.

Money objects are `{amount, currency_code, formatted_amount}`. `amount` is documented as an integer in the smallest currency denomination, and currency comes from `currency_code` on the total. The sample's cart item prices do not add up to `payment.charges.sub_total`, so totals are never computed from items.

The official webhook example and Get Order example use different UUIDs even though the documentation says `meta.resource_id` is the order id. The official fixtures are not edited to hide this. The webhook is rejected with 400 before any lookup when `event_type` does not start with `orders.` or when `meta.resource_id` does not match `^[A-Za-z0-9_-]+$` or is longer than 128 characters. `FixtureOrderClient` applies the same id check and returns a copy of the official Get Order fixture with `id` set to the `resource_id`, `display_id` set to its last 5 characters and the sample's 2019 `placed_at` removed, so the copy is stamped with the received time. `external_order_id` is the `id` of the fetched order, and the mismatch is recorded in `docs/verification-notes.md`.

When sending the Uber fixture with curl, use `--data-binary @file`. Plain `-d @file` strips newlines, changes the body and breaks the signature.

### DoorDash Marketplace

Webhook:
- POST with `{ "event": { "type", "status" }, "order": { ... } }`. The full order is in the webhook and no second call is needed. Order-create events have status `NEW`.
- `order` fields used: `id`, `consumer` (`first_name`, `last_name`, `phone`, `email`, `id`), `categories[].items[]` (`name`, `price`, `quantity`, `extras[]`), `subtotal`, `tax`. Items are nested under categories. Modifiers are under `extras[].options[]` and stay in `raw_payload`. `tip_amount` is the delivery tip and is only sent for self-delivery orders. `merchant_tip_amount` is the tip for merchant staff. Neither is part of the total.
- `subtotal` and `tax` are documented as integers without a stated unit. The sample values (2000 and 300) read as cents, so they are treated as cents, and this is recorded as an assumption. The sample's item prices are 0 while `subtotal` is 2000, so totals are never computed from items.
- There is no total field. `total_cents` is `subtotal + tax`. The sample has no currency, so currency comes from settings. The only timestamp is `estimated_pickup_time`, which is a pickup estimate, so `created_at` is the time the webhook was received.
- A 200 is a synchronous order confirmation, and its body is the confirmation payload: `{"merchant_supplied_id": "<internal order id>", "order_status": "success"}`. Invalid orders get 400 with `{"order_status": "fail", "failure_reason": "<message>"}`, because any non-2xx is treated as a failed order. Only `OrderCreate` with status `NEW` is ingested. Other events get 200 with `{"ignored": "<event type>"}`.

Authentication: the order webhook carries the same authentication header as the menu status webhook. The Marketplace pages say only that the endpoint must be HTTPS and protected with an "authentication token" (an "Auth Token" field in the portal); they name no authentication types. Supporting evidence only: the Drive (classic) webhooks guide lists two types, "Basic Auth" (the exact contents of the HTTP `Authorization` header) and "OAuth" (client ID, client secret, token URL and optional scope), and the Developer Portal webhook form is reported to offer the same two (it needs a login and was not re-checked).

Implementation supports the static header mode. `DOORDASH_WEBHOOK_AUTH_HEADER` holds the full expected `Authorization` value, and the incoming header is compared to it with `hmac.compare_digest`. OAuth mode is not implemented and is recorded in `docs/verification-notes.md`.

DoorDash Drive webhooks belong to a separate delivery product and are not handled.

### Fixtures

- Official samples contain invalid JSON in places (trailing commas, stray `...`, missing commas). Fixtures are cleaned to valid JSON and otherwise unchanged. The published text is kept in `fixtures/as-published/`, and every change is listed in `docs/verification-notes.md`.
- No fixture contains a `provider` field. Provider detection uses the payload shape only: Uber when `meta` contains `resource_id`, DoorDash when both `event` and `order` objects exist, otherwise 400.

## Demo-only code

The webhook simulator and the Uber Get Order mock exist only to ease the reviewer's demo. They are kept apart so the assignment code can be read on its own.

1. Demo code lives only in `api/demo/`, `admin/src/demo/` and `fixtures/demo/` (plus `scripts/seed_demo.sh`). Nothing else holds demo logic.
2. Dependencies go one way: the demo imports from the core, the core never imports from the demo. `grep -rn "demo" api/orders` returns nothing, and in `admin/src` outside `admin/src/demo` the only match is the single lazy import in `App.jsx`.
3. The core's only touchpoints are the `DEMO_ENABLED` block in `api/config/settings.py`, the conditional include in `api/config/urls.py`, the lazy `DemoLauncher` import in the top bar slot of `admin/src/App.jsx`, the `/demo/api` entry in the `admin/vite.config.js` proxy, and the demo lines in `.env.example`.
4. The demo is off in code by default (`DEMO_ENABLED` false). `.env.example` turns it on for the reviewer's `cp .env.example .env` setup, with a comment on how to turn it off.
5. Deleting `api/demo/`, `admin/src/demo/` and the touchpoints must leave a working core: the backend tests and the admin build pass. Check this in a temporary copy, never in the working tree.

## Testing

All backend tests live in `api/orders/tests.py` and run with `python manage.py test`. The one exception is the demo app: its tests live in `api/demo/tests.py` and are skipped unless `DEMO_ENABLED` is true. Webhook tests post raw bytes, for example `self.client.generic("POST", url, data=body_bytes, content_type="application/json", ...)`, because re-serializing the body changes the bytes and invalidates the Uber signature. New behaviour ships with tests.

## Git conventions

Commits follow Conventional Commits: `type(scope): subject`.

- Types: `feat`, `fix`, `test`, `docs`, `chore`, `refactor`.
- Scopes: `api`, `admin`, `fixtures`, `docs`, `repo`.
- Subject in imperative mood, lowercase, no trailing period, under 72 characters. Add a body only when the reason is not obvious from the diff.
- One commit per logical part of the application. Tests are committed with the code they cover.
- Stage files by explicit path and review the staged diff before committing.
- `.gitignore` covers `.venv/`, `node_modules/`, `db.sqlite3`, `.env`, `__pycache__/` and `dist/`.

## Out of scope

User authentication and login, live provider accounts and outbound calls to either provider, other marketplaces, message brokers, component libraries, production deployment, bulk dummy data.