# Nomni: Marketplace Order System

A full-stack app that turns Uber Eats and DoorDash orders into one kitchen ticket system. It has a backend API (Django) and a web admin (React + Vite).

Orders from both providers arrive at one webhook URL. The API works out which provider sent the order, checks it is real, and saves it in one common format.

---

## Contents

1. [Run it](#1-run-it)
2. [Use the webhook simulator](#2-use-the-webhook-simulator)
3. [Curl examples](#3-curl-examples)
4. [Mapping table](#4-mapping-table)
5. [Conflict log](#5-conflict-log)
6. [Screenshots](#6-screenshots)
7. [Screen recording](#7-screen-recording)
8. [Developer Notes](#developer-notes)

---

## 1. Run it

### What you need

- Python 3.12 or newer (the pinned Django 6 needs it)
- Node.js 20.19 or newer, or 22.12 or newer, with npm
- `curl` and `openssl` (the curl examples and the scripts use them)

```bash
python3 --version
node --version
npm --version
```

Open two terminals. Run the API in the first one and the Admin in the second one. Run every command from the repository root unless it says otherwise.

### API (Django)

```bash
# 1. Make a virtual environment (keeps packages away from your system Python)
python3 -m venv .venv

# 2. Turn it on
source .venv/bin/activate

# 3. Install the packages
pip install -r api/requirements.txt

# 4. Copy the example settings file to the repository root
cp .env.example .env

# 5. Create the database tables
cd api
python manage.py migrate

# 6. Start the API at http://localhost:8000
python manage.py runserver
```

`.env` must be in the repository root, next to `.env.example`. It is never committed. You do not need to change anything in it: the example file has working demo values, including the secrets used by the curl examples below. The API refuses to start if a required variable is missing or empty.

### Admin (React + Vite)

In the second terminal:

```bash
cd admin
npm install
npm run dev
```

Open the address the terminal prints. It is usually `http://localhost:5173`. Vite forwards `/api` requests to `http://localhost:8000`. The Admin has no `.env` of its own. The proxy target comes from `API_PROXY_TARGET` in the root `.env`, and defaults to `http://localhost:8000`.

For a production build, run this from the repository root:

```bash
cd admin && npm run build
```

### Add the demo orders

With the API running, run this from the repository root in a third terminal (or in the Admin terminal after it has started):

```bash
scripts/seed_demo.sh
```

It sends four orders: the official Uber Eats sample, the official DoorDash sample, one Uber Eats demo order and one DoorDash demo order. Each line prints `HTTP 200` when it works. Run it again and you still have four orders, because the same order updates in place.

To send a single order, give the script an id. An Uber id may use letters, digits, `-` and `_`.

```bash
scripts/send_uber_webhook.sh my-uber-order-1
```

```bash
scripts/send_doordash_webhook.sh my-doordash-order-1
```

Without an id, each script sends the official sample.

### Demo tools

`.env.example` sets `DEMO_ENABLED="true"`, which turns on the webhook simulator in the Admin and its endpoints in the API. Set it to `"false"` and delete the `UBER_ORDER_CLIENT` line to run without them (restart the API).

### Run the tests

```bash
source .venv/bin/activate
cd api
python manage.py test
```

### Note about ports

Run the API on port 8000, as shown above. The curl examples in this README and the scripts use `http://localhost:8000/api/webhooks/orders`.

If you use another port:

- The scripts send to `http://localhost:8000/api/webhooks/orders` unless you set `WEBHOOK_URL`. Without it they send to whatever is listening on port 8000, and print `HTTP 200` if that is another copy of this app.
- Change the port in the curl examples.
- Set `API_PROXY_TARGET` in `.env` and restart the Admin.

Example with the scripts on port 8077:

```bash
WEBHOOK_URL=http://localhost:8077/api/webhooks/orders scripts/seed_demo.sh
```

---

## 2. Use the webhook simulator

The simulator is a small demo tool inside the Admin. It sends mock Uber Eats and DoorDash webhooks to your own API, so you do not need a real provider account. It is available while `DEMO_ENABLED` is `"true"`.

1. Start the API and the Admin (see above).
2. Open the Admin and click **Webhook simulator** in the top bar.
3. Pick a provider: **Uber Eats** or **DoorDash**.
4. Pick a **Preset**: **Official sample** (the provider's official example), **Random order** (a quick test) or **Custom** (your own customer and items).
5. For **Custom**, fill in the first name, last name, phone, and at least one item (name, quantity, price). An item can also have a note, for example "no onions, nut allergy".
6. For Uber Eats, pick an **Uber order state** (CREATED, ACCEPTED, DENIED, CANCELED, FINISHED or UNKNOWN). The Official sample keeps its own state, so the choice is disabled for it.
7. Choose the **Order id**:
   - **New order** makes a new order.
   - **Reuse last order id** sends the same order again, so you can see it update instead of duplicate.
8. Choose **Authentication**. **Valid signature or token** should work. **Invalid signature or token** is there to check that a bad request is rejected.
9. Tick **Send twice at the same moment** to test two identical webhooks arriving together. Only one order should be saved.
10. Click **Send**. The result shows below the form: the status code (for example `200`), and **What was sent**.
11. Click **Copy curl command** to get the same webhook as a curl command, without sending it. Each copy gets a new order id, so running it adds a new order. Choose **Reuse last order id** if you want it to update the last order.

---

## 3. Curl examples

You can also use the simulator's **Copy curl command** button. It builds a correct command for you.

All examples send to `http://localhost:8000/api/webhooks/orders`. Run the API first, and run the examples from the repository root. Each example is one command. Copy it as a whole.

### Uber Eats

Uber Eats sends only a short message with an order id. The API then fetches the full order (Get Order) using that id. Here that call is answered from the official Get Order sample in `/fixtures`, so it works with no Uber account.

Uber also signs every message. The signature is the lowercase hex HMAC-SHA256 of the exact body, made with the client secret, and it goes in the `X-Uber-Signature` header. The command below already has the signature for this exact body and the demo secret `dev-uber-client-secret-0001` (the value of `UBER_CLIENT_SECRET` in `.env.example`), so you can paste it as it is.

```bash
curl -i -X POST http://localhost:8000/api/webhooks/orders \
  -H 'Content-Type: application/json' \
  -H 'X-Uber-Signature: 46494768329fedbf30b8eeae38d3082571e894625fc59724a59fc82e38c55279' \
  --data-binary '{"event_type":"orders.notification","event_id":"9707aa33-c1bf-4bc8-ac4f-c05fcf61613c","event_time":1791704285,"meta":{"resource_id":"sim-uber-1","status":"pos","user_id":"89dd9741-66b5-4bb4-b216-000000000000"},"resource_href":"https://api.uber.com/v2/eats/order/sim-uber-1"}'
```

You should see `HTTP/1.1 200 OK` with an empty body (`Content-Length: 0`). The order then appears in the Admin. Send the same command again and the same order updates; no second order is made.

Any change to the body, or a different `UBER_CLIENT_SECRET`, makes this signature wrong and the API answers 401. To send a different order, use the simulator's **Copy curl command** button or this script. Both sign the body for you.

```bash
scripts/send_uber_webhook.sh my-uber-order-1
```

To sign a body by hand, put the exact body in `BODY` and the secret in `UBER_CLIENT_SECRET`, then run:

```bash
printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$UBER_CLIENT_SECRET"
```

The body must reach the server byte for byte as it was signed. Use `--data-binary`, because `-d @file` removes newlines and breaks the signature.

### DoorDash

DoorDash sends the full order in the message, so no second call is needed. It does not sign the message. It sends the configured authentication token in the `Authorization` header (the value of `DOORDASH_WEBHOOK_AUTH_HEADER` in `.env.example` is already in the command). DoorDash's pages say the endpoint must be protected with an authentication token, but they do not name the header or its format. This project compares the whole `Authorization` header with `DOORDASH_WEBHOOK_AUTH_HEADER` from `.env`.

```bash
curl -i -X POST http://localhost:8000/api/webhooks/orders \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer dev-doordash-token-0001' \
  --data-binary '{
  "event": {
    "type": "OrderCreate",
    "status": "NEW"
  },
  "order": {
    "categories": [
      {
        "items": [
          {
            "extras": [
              {
                "merchant_supplied_id": "INDIVIDUAL_SAUCES",
                "name": "Signature Sauces",
                "options": [
                  {
                    "extra": [
                      {
                        "merchant_supplied_id": "BREAKFAST_CONDIMENTS",
                        "name": "Breakfast Condiments",
                        "options": [
                          {
                            "merchant_supplied_id": "ADD_SALT",
                            "name": "Salt",
                            "price": 0,
                            "quantity": 1
                          }
                        ]
                      }
                    ],
                    "merchant_supplied_id": "ADD_KETCHUP_INDIVIDUAL",
                    "name": "KETCHUP",
                    "price": 0,
                    "quantity": 1
                  }
                ]
              }
            ],
            "merchant_supplied_id": "26d3fce0-efd2-46d3-832c-ced5bc956401",
            "name": "Burrito Scram-Bowl",
            "price": 0,
            "quantity": 1
          }
        ],
        "merchant_supplied_id": "Entree",
        "name": "Entree"
      }
    ],
    "consumer": {
      "email": "support@doordash.com",
      "first_name": "Kelley",
      "id": 0,
      "last_name": "W.",
      "phone": "+18559731040"
    },
    "id": "abc12345",
    "order_special_instructions": "",
    "store": {
      "merchant_supplied_id": "abc12345",
      "provider_type": "eatsa"
    },
    "estimated_pickup_time": "2019-08-24T14:15:22Z",
    "is_pickup": true,
    "subtotal": 2000,
    "tax": 300,
    "is_tax_remitted_by_doordash": true,
    "tax_amount_remitted_by_doordash": 0,
    "commission_type": "regular",
    "delivery_short_code": "string",
    "fulfillment_type": "dx_delivery",
    "merchant_tip_amount": 0,
    "experience": "DOORDASH",
    "is_plastic_ware_option_selected": true,
    "tip_amount": 0
  }
}'
```

You should see `HTTP/1.1 200 OK` and a JSON body with `merchant_supplied_id` (our internal order id) and `"order_status": "success"`. This is DoorDash's synchronous order confirmation. The order then appears in the Admin. To send another order, change `order.id`.

### If a request fails

| Code | What it means |
| --- | --- |
| 200 | Order saved (or updated). Also sent for an event that is valid but not an order, such as another Uber event type or a DoorDash event that is not `OrderCreate` with status `NEW`. Nothing is saved for those. Uber gets an empty body. DoorDash gets `{"ignored": "<event type>"}`. |
| 400 | The payload is not an order the API knows (no Uber `meta.resource_id`, no DoorDash `event` and `order` objects), or a value is missing or invalid. DoorDash gets `{"order_status": "fail", "failure_reason": "..."}`. |
| 401 | The Uber signature or the DoorDash `Authorization` value is missing or wrong. |
| 502 | The API could not fetch the full Uber order. Nothing was saved. |

---

## 4. Mapping table

This shows how each provider's fields become our one internal order. Money is stored as whole cents. The Note column marks extra keys we added on top of the ten required fields, and choices we made where the official documentation is silent.

| Internal field | Uber Eats source | DoorDash source | Note |
| --- | --- | --- | --- |
| `id` | Not from the provider. The database key (a whole number). | Same. | |
| `provider` | `uber`, chosen when the webhook has `meta.resource_id`. | `doordash`, chosen when the webhook has both an `event` and an `order` object. | Taken from the shape of the payload only. |
| `external_order_id` | `id` of the Get Order response. It must equal the webhook's `meta.resource_id`, or the webhook fails with 502. | `order.id` | |
| `status` | Get Order `current_state`: CREATED to `new`, ACCEPTED to `accepted`, DENIED to `cancelled`, CANCELED to `cancelled`, FINISHED to `completed`, UNKNOWN to `new`. Any other value is a 400. | `event.status`. Only `OrderCreate` with `NEW` is saved, and it becomes `new`. | The webhook's `meta.status` is the notification type, not the order state, and is never used. DENIED, FINISHED and UNKNOWN are our choices, because the docs list the values without explaining them. A repeat only moves the status forward, except that `cancelled` always applies. |
| `customer.name` | `eater.first_name` and `eater.last_name`, joined with a space. | `consumer.first_name` and `consumer.last_name`, joined with a space. | |
| `customer.phone` | `eater.phone` (anonymized by Uber). | `consumer.phone` | DoorDash puts a general support number here unless masked phone numbers are enabled. |
| `customer.phone_code` | `eater.phone_code` | Not used. Always empty. | Extra key. Uber's phone number is anonymized, and the code is needed to reach the customer. |
| `line_items[].name` | `cart.items[].title` | `order.categories[].items[].name` | |
| `line_items[].quantity` | `cart.items[].quantity` | `order.categories[].items[].quantity` | |
| `line_items[].unit_price_cents` | `cart.items[].price.unit_price.amount` | `order.categories[].items[].price` | DoorDash: our decision to treat `price` as a unit price. The docs do not say, and the sample has quantity 1 and price 0. |
| `line_items[].line_total_cents` | `cart.items[].price.total_price.amount` | Worked out: `price` times `quantity`. | Modifier prices are not added by us on either side. |
| `line_items[].notes` | `cart.items[].special_instructions` | `order.categories[].items[].special_instructions` | Extra key. Kitchens need allergy and special-request notes. It is an empty string when the field is missing or is not text. The official DoorDash sample has no item notes. |
| `total_cents` | `payment.charges.total.amount`. If `total` is missing: `sub_total` + `tax` + `total_fee`, in the same currency. | `order.subtotal` + `order.tax` | DoorDash: our decision, because the sample has no total field. We treat both values as cents, which is an assumption (the docs give only the type). Tips and fees are left out. Totals are never added up from line items, because the official samples do not add up. |
| `currency` | `currency_code` of the total. | The `DEFAULT_CURRENCY` setting (`USD` in `.env.example`). | DoorDash: our decision, because the sample has no currency. |
| `created_at` | `placed_at` when it is a time with a timezone offset. Otherwise the time we received the webhook. | The time we received the webhook. | Our decision for DoorDash, which has only a pickup estimate. It is set once and not changed when the same order arrives again. |
| `raw_payload` | `{"webhook": ..., "order": ...}`: the webhook and the Get Order response, as received. | `{"event": ..., "order": ...}`, as received. | |
| `next_status` | Worked out by the API from `status`. Not stored. | Same. | Extra key. It tells the Admin which status button to show. It is `null` for `completed` and `cancelled`. |

### Sample files

The official examples are saved in `/fixtures`, and the original published text is kept in `fixtures/as-published/`. The published samples are not valid JSON in places, so the fixtures only have those errors fixed. Nothing else is changed.

- Uber Eats webhook: `fixtures/uber_webhook.json`
- Uber Eats Get Order response: `fixtures/uber_get_order.json`
- DoorDash order (the sample order inside the `event` envelope from the Order Integration page): `fixtures/doordash_order.json`

`fixtures/demo/` holds extra orders for the seed script and the simulator.

<details open>
<summary>Our internal order (what <code>GET /api/orders/&lt;id&gt;</code> returns)</summary>

This is the real response for the official Uber Eats sample. `raw_payload` is shortened here.

```json
{
  "id": 2,
  "provider": "uber",
  "external_order_id": "153dd7f1-339d-4619-940c-418943c14636",
  "status": "new",
  "next_status": "accepted",
  "customer": {
    "name": "Larry",
    "phone": "+1 555-555-5555",
    "phone_code": "555 55 555"
  },
  "total_cents": 1399,
  "currency": "USD",
  "created_at": "2026-10-11T07:55:45.985288Z",
  "line_items": [
    { "name": "Fresh-baked muffin", "quantity": 1, "unit_price_cents": 350, "line_total_cents": 350, "notes": "" },
    { "name": "Coffee", "quantity": 1, "unit_price_cents": 300, "line_total_cents": 300, "notes": "make it iced please" },
    { "name": "Strawberry Donut", "quantity": 1, "unit_price_cents": 250, "line_total_cents": 250, "notes": "" }
  ],
  "raw_payload": { "webhook": "...", "order": "..." }
}
```

The line items add up to 900 but the total is 1399. That is how the official sample is written (the total includes fees), which is why we never compute the total from the items.

</details>

---

## 5. Conflict log

Each row is a working note from the brief, written exactly as in the brief. The official documentation wins. Pages are named by their titles.

| Working note | Outcome | Reason / evidence |
| --- | --- | --- |
| Uber may include the full cart in the webhook; verify whether a Get Order call is still required. | Rejected. A Get Order call is required. | Overruled by the Uber webhook page (Orders: Notifications, "Webhook Event Structure"). The event has only `event_id`, `event_time`, `meta` (`user_id`, `resource_id`, `status`) and `resource_href`, with no cart. `resource_href` is the Get Order address. The official webhook fixture has no cart, and the API calls Get Order with `meta.resource_id`. If that call fails the reply is 502 and nothing is saved. |
| DoorDash Marketplace line items may use a top-level items[]. | Rejected. Items are under `categories[].items[]`. | Overruled by the DoorDash sample order page, where each item sits inside a category. The fixture has no top-level `items`. |
| Verify which DoorDash monetary field should become total_cents and whether tax is included. | Changed. `total_cents` is `subtotal` + `tax`, so tax is included. | The sample order page lists `subtotal` and `tax` and has no total field. The docs do not say whether `tax` is already inside `subtotal`, so this is our decision. Both are read as cents, which is an assumption: the Order FAQ shows an item price of 510 as $5.10, but the docs give no unit for `subtotal` and `tax`. Tips and fees are left out. |
| Verify Uber webhook signature generation and the X-Uber-Signature header. | Verified. | Uber Orders: Notifications ("Webhook Security"): `X-Uber-Signature` is the lowercase hex HMAC-SHA256 of the request body, with the client secret as the key. The header table on the same page calls it a "SHA256 hash", but a plain hash would not use the secret, so we implemented the HMAC. The API reads the raw body bytes before parsing, and compares in constant time. Missing, empty, wrong, uppercase and re-serialised-body signatures all get 401. |
| Verify the exact Uber webhook response status/body. | Verified. | Uber Orders: Notifications ("Order Notification"): reply `HTTP 200` with an empty body. The API does this (tested: 200, 0 bytes). Without a 200, Uber resends the event up to 7 times. The Webhooks Guide ("Retry logic") describes the retries differently: it lists only 500, 502, 503, 504, timeouts and network errors, with the first retry at 10 seconds. Our replies work with both. |
| DoorDash Drive webhooks are optional. | Changed: Drive is a separate API. | The DoorDash Drive webhook guide covers delivery updates from the Drive API, not Marketplace orders. We do not handle Drive payloads. |
| Verify whether Uber webhook meta.resource_id corresponds to the Get Order id in the official examples. | Rejected for the official examples. | The Uber webhook page says `resource_id` is equivalent to the `order_id`. The two official examples disagree: the webhook uses `153dd7f1-339d-4619-940c-418943c14636` and the Get Order example has the id `f9f363d1-e1c2-4595-b477-c649845bc953`. We did not edit the fixtures. The local Get Order answer is the official sample with its `id` set to the requested `resource_id`, and the API requires the fetched `id` to equal `resource_id` (otherwise 502, nothing saved). |
| Do not rely on a provider query parameter for normal provider detection. | Verified. | This is a rule from the brief, not from a provider page. The provider is detected from the payload shape only: Uber when `meta` has `resource_id`, DoorDash when `event` and `order` are both objects, otherwise 400. A `?provider=` parameter or a `provider` field in the body changes nothing (tested). No fixture has a `provider` field. |
| Verify the documented location of DoorDash customer phone data. | Verified. | The DoorDash sample order page has it at `consumer.phone`. The DoorDash Order FAQ says that by default this holds a general DoorDash Support number, and an order-specific number appears only when masked customer phone numbers are enabled. |
| Normalize marketplace statuses into the internal status model where appropriate. | Verified and applied, with our own mapping. | Uber Get Order lists `current_state` as CREATED, ACCEPTED, DENIED, FINISHED, CANCELED or UNKNOWN, with no meaning for each. DoorDash Order Integration says every incoming order has status NEW. The full map is in the mapping table. The webhook's `meta.status` is never mapped. Internal statuses are `new`, `accepted`, `preparing`, `ready`, `completed` and `cancelled`. `preparing` and `ready` are set only from the Admin and are never sent to a provider. |

### Other conflicts found

- **Official samples are not valid JSON.** The Uber webhook sample has a stray `...`, the Get Order sample has four trailing commas, and the DoorDash sample is missing a comma after `"tax": 300`. The fixtures fix only these. Every change is listed in `docs/verification-notes.md`.
- **Uber item prices do not match the totals.** The three items in the Get Order sample add up to 900, `sub_total` is 650 and `total` is 1399.
- **DoorDash sample prices do not match the totals.** The item `price` is 0 while `subtotal` is 2000.
- **DoorDash authentication.** The Marketplace pages ask for an authentication token and name no header or format. We support one static `Authorization` value. OAuth is not implemented.

Every documented provider behaviour the code relies on is cited with page and section in `docs/verification-notes.md`.

---

## 6. Screenshots

### Desktop (1280 px)

Order list with the status pills, search, provider filter and sort by time:

![Order list on desktop](docs/screenshots/orders-list-desktop.png)

Order detail with the total, items, customer, progress and the forward status button. The raw data is inside the closed **Debug data** section:

![Order detail on desktop](docs/screenshots/order-detail-desktop.png)

The webhook simulator:

![Webhook simulator](docs/screenshots/webhook-simulator.png)

### Phone (390 px)

| Order list | Order detail |
| --- | --- |
| <img src="docs/screenshots/orders-list-mobile.jpg" alt="Order list on a phone" width="360"> | <img src="docs/screenshots/order-detail-mobile.jpg" alt="Order detail on a phone" width="360"> |

---

## 7. Screen recording

_add recording_

---

## Developer Notes

Where the provider documentation is silent, the choice is recorded here.

- DoorDash has no total field. `total_cents` is `subtotal + tax`, and both are read as cents because the Order FAQ example (price 510 is $5.10) and the sample values (2000 and 300) read that way. This is an assumption.
- The DoorDash sample has no currency, so `DEFAULT_CURRENCY` is used.
- DoorDash has no creation time (only a pickup estimate), so `created_at` is the time the webhook was received. Uber orders use `placed_at` when it has a timezone offset, and the received time otherwise.
- A DoorDash item `price` is treated as a unit price, so the line total is `price * quantity`.
- Uber `UNKNOWN` maps to `new`, `DENIED` to `cancelled` and `FINISHED` to `completed`.
- Only a DoorDash `OrderCreate` event with status `NEW` is saved. Any other event inside the envelope gets `200` with `{"ignored": "<event type>"}`.
- Other Uber event types that carry `meta.resource_id` get an empty `200` and nothing is saved. An Uber `orders.cancel` event does not change an existing order.
- The Uber `resource_id` may only contain letters, digits, `-` and `_` (up to 128 characters), so an id can never build a path outside the fixture folders. DoorDash order ids are only trimmed and length checked.
- Uber Get Order runs inside the webhook request, with a 5 second timeout. A production version would answer first and fetch in a background job.
- Uber's accept or deny call is not implemented (outbound calls are out of scope). A real Uber order would auto-cancel after 11.5 minutes.
- The read endpoints and the status endpoint have no login, because login is out of scope.
