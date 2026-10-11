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

- Git
- Python 3.12 or newer (the pinned Django 6 needs it)
- Node.js 20.19 or newer, or 22.12 or newer, with npm
- `curl` and `openssl` (the curl examples and the scripts use them)

Check the versions:

```bash
git --version
python3 --version
node --version
npm --version
```

If `python3 --version` shows a version older than 3.12, install Python 3.12 first. Installing the packages fails on older versions.

The commands are for macOS and Linux (zsh or bash). On Windows, run them inside WSL (Windows Subsystem for Linux).

### Get the code

Open a terminal in the folder where you want the project, then run:

```bash
git clone https://github.com/saravananmanikandan/marketplace-order-system.git
cd marketplace-order-system
echo "cd \"$(pwd)\""
```

The `marketplace-order-system` folder is the **project folder**. Every command in this README starts there.

The last command prints the exact command that goes back to this folder on your computer. It looks like `cd "/home/alex/projects/marketplace-order-system"`, with your own path. Copy that printed line and keep it.

You use three terminals: one for the API, one for the Admin, and one for the demo orders and the tests. A new terminal usually starts in your home folder, not in the project folder. So in every new terminal, first paste the `cd` line you copied.

### Terminal 1: API (Django)

Run these steps in the project folder.

1. Make a virtual environment. It keeps the packages away from your system Python.

   ```bash
   python3 -m venv .venv
   ```

   On Debian or Ubuntu, if this says `ensurepip is not available`, install the `python3-venv` package for your Python version (for example `sudo apt install python3.12-venv`) and run it again.

2. Turn it on. Your prompt then starts with `(.venv)`.

   ```bash
   source .venv/bin/activate
   ```

3. Install the packages.

   ```bash
   pip install -r api/requirements.txt
   ```

4. Copy the example settings file.

   ```bash
   cp .env.example .env
   ```

5. Create the database tables, then start the API at `http://localhost:8000`.

   ```bash
   cd api
   python manage.py migrate
   python manage.py runserver
   ```

Leave this terminal open. The API runs until you press `Ctrl+C`. If it prints `Error: That port is already in use.`, see [Note about ports](#note-about-ports).

`.env` must be in the project folder, next to `.env.example`. It is never committed. You do not need to change anything in it: the example file has working demo values, including the secrets used by the curl examples below. The API refuses to start if a required variable is missing or empty.

To start the API again later, open a terminal, paste your `cd` line, and run:

```bash
source .venv/bin/activate
cd api
python manage.py runserver
```

### Terminal 2: Admin (React + Vite)

Open a second terminal and paste your `cd` line. Then run:

```bash
cd admin
npm install
npm run dev
```

`npm install` may print `npm warn allow-scripts` for `fsevents`. This is only a warning, and you can ignore it.

Open the address the terminal prints. It is usually `http://localhost:5173`. Vite forwards `/api` requests to `http://localhost:8000`. The Admin has no `.env` of its own. The proxy target comes from `API_PROXY_TARGET` in the project folder's `.env`, and defaults to `http://localhost:8000`.

To start the Admin again later, paste your `cd` line, then run `cd admin` and `npm run dev`.

For a production build, paste your `cd` line and run:

```bash
cd admin
npm run build
```

### Terminal 3: add the demo orders

Open a third terminal and paste your `cd` line. The API must be running in terminal 1. Then run:

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

`.env.example` sets `DEMO_ENABLED="true"`, which turns on the webhook simulator in the Admin and its endpoints in the API. To run without them, open `.env`, set `DEMO_ENABLED="false"` and delete the `UBER_ORDER_CLIENT` line. Then restart the API.

### Run the tests

In terminal 3, make sure you are in the project folder (paste your `cd` line if you are not sure), then run:

```bash
source .venv/bin/activate
cd api
python manage.py test
```

The last line should be `OK`. The tests use their own temporary database, so the API can keep running. Run `cd ..` afterwards to go back to the project folder.

### Note about ports

Run the API on port 8000, as shown above. The curl examples in this README and the scripts use `http://localhost:8000/api/webhooks/orders`.

If another program already uses port 8000, `runserver` prints `Error: That port is already in use.` Stop that program, or start the API on another port, for example `python manage.py runserver 8077`. If you use another port:

- The scripts send to `http://localhost:8000/api/webhooks/orders` unless you set `WEBHOOK_URL`. Without it they send to whatever is listening on port 8000, and print `HTTP 200` if that is another copy of this app.
- Change the port in the curl examples.
- Set `API_PROXY_TARGET` in `.env` (for example `API_PROXY_TARGET="http://localhost:8077"`) and restart the Admin.

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

All examples send to `http://localhost:8000/api/webhooks/orders`. Run the API first. The curl examples work from any folder. Each example is one command. Copy it as a whole.

### Uber Eats

Uber Eats sends only a short message with an order id. The API then fetches the full order (Get Order) using that id. Here that call is answered from the official Get Order sample in `/fixtures`, so it works with no Uber account.

Uber also signs every message. The signature is the lowercase hex HMAC-SHA256 of the exact body, made with the client secret, and it goes in the `X-Uber-Signature` header. The command below already has the signature for this exact body and the demo secret `dev-uber-client-secret-0001` (the value of `UBER_CLIENT_SECRET` in `.env.example`), so you can paste it as it is.

```bash
curl -i -X POST http://localhost:8000/api/webhooks/orders \
  -H 'Content-Type: application/json' \
  -H 'X-Uber-Signature: 5b3c379c3794573526de7ebecbf84530ed7c2b2e4dd4f4fbff0334a9f1bf0331' \
  --data-binary '{
  "event_type": "orders.notification",
  "event_id": "c4d2261e-2779-4eb6-beb0-cb41235c751e",
  "event_time": 1427343990,
  "meta": {
    "resource_id": "153dd7f1-339d-4619-940c-418943c14636",
    "status": "pos",
    "user_id": "89dd9741-66b5-4bb4-b216-a813f3b21b4f"
  },
  "resource_href": "https://api.uber.com/v2/eats/order/153dd7f1-339d-4619-940c-418943c14636"
}'
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

DoorDash sends the full order in the message, so no second call is needed. It does not sign the message. It sends the configured authentication token in the `Authorization` header (the value of `DOORDASH_WEBHOOK_AUTH_HEADER` in `.env.example` is already in the command). DoorDash's pages say the endpoint must be protected with an authentication token, but they do not name the header or its format. This project compares the whole `Authorization` header with `DOORDASH_WEBHOOK_AUTH_HEADER` from `.env`. OAuth is not supported.

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

You should see `HTTP/1.1 200 OK` and a JSON body with `merchant_supplied_id` (my internal order id) and `"order_status": "success"`. This is DoorDash's synchronous order confirmation. The order then appears in the Admin. To send another order, change `order.id`.

### If a request fails

| Code | What it means |
| --- | --- |
| 200 | Order saved (or updated). Also sent for an event that is valid but not an order, such as another Uber event type or a DoorDash event that is not `OrderCreate` with status `NEW`. Nothing is saved for those. Uber gets an empty body. DoorDash gets `{"ignored": "<event type>"}`. |
| 400 | The payload is not an order the API knows (no Uber `meta.resource_id`, no DoorDash `event` and `order` objects), or a value is missing or invalid. DoorDash gets `{"order_status": "fail", "failure_reason": "..."}`. |
| 401 | The Uber signature or the DoorDash `Authorization` value is missing or wrong. |
| 502 | The API could not fetch the full Uber order. Nothing was saved. |

---

## 4. Mapping table

This shows how each provider's fields become my one internal order. Money is stored as whole cents. The Note column marks extra keys I added on top of the ten required fields, and the documentation behind each choice.

| Internal field | Uber Eats source | DoorDash source | Note |
| --- | --- | --- | --- |
| `id` | Not from the provider. The database key (a whole number). | Same. | |
| `provider` | `uber`, chosen when the webhook has `meta.resource_id`. | `doordash`, chosen when the webhook has both an `event` and an `order` object. | Taken from the shape of the payload only. |
| `external_order_id` | `id` of the Get Order response. It must equal the webhook's `meta.resource_id`, or the webhook fails with 502. | `order.id` | |
| `status` | Get Order `current_state`: CREATED to `new`, ACCEPTED to `accepted`, DENIED to `cancelled`, CANCELED to `cancelled`, FINISHED to `completed`, UNKNOWN to `new`. Any other value is a 400. | `event.status`. Only `OrderCreate` with `NEW` is saved, and it becomes `new`. | The webhook's `meta.status` is the notification type, not the order state, and is never used. The reason for each state is in the status mapping below. A repeat only moves the status forward, except that `cancelled` always applies. |
| `customer.name` | `eater.first_name` and `eater.last_name`, joined with a space. | `consumer.first_name` and `consumer.last_name`, joined with a space. | |
| `customer.phone` | `eater.phone` (anonymized by Uber). | `consumer.phone` | DoorDash puts a general support number here unless masked phone numbers are enabled. |
| `customer.phone_code` | `eater.phone_code` | Not used. Always empty. | Extra key. Uber's phone number is anonymized, and the code is needed to reach the customer. |
| `line_items[].name` | `cart.items[].title` | `order.categories[].items[].name` | |
| `line_items[].quantity` | `cart.items[].quantity` | `order.categories[].items[].quantity` | |
| `line_items[].unit_price_cents` | `cart.items[].price.unit_price.amount` | `order.categories[].items[].price` | DoorDash: `price` is a unit price. The Order FAQ says it is the menu price of one item plus the prices of the modifiers selected in that item. |
| `line_items[].line_total_cents` | `cart.items[].price.total_price.amount` | Worked out: `price` times `quantity`. | I do not add modifier prices on either side, because both providers already include them in the item price. |
| `line_items[].notes` | `cart.items[].special_instructions` | `order.categories[].items[].special_instructions` | Extra key. Kitchens need allergy and special-request notes. It is an empty string when the field is missing or is not text. The official DoorDash sample has no item notes. |
| `total_cents` | `payment.charges.total.amount`. If `total` is missing: `sub_total` + `tax` + `total_fee`, in the same currency. | `order.subtotal` + `order.tax` | DoorDash has no total field. Its money fields are in cents, and `tax` is calculated on top of `subtotal`. The conflict log shows the documentation. Tips are left out. Totals are never added up from line items, because the official samples do not add up. |
| `currency` | `currency_code` of the total. | The `DEFAULT_CURRENCY` setting (`USD` in `.env.example`). | DoorDash: the Order model has no currency field and the official sample has none, so the setting is used. |
| `created_at` | `placed_at` when it is a time with a timezone offset. Otherwise the time I received the webhook. | The time I received the webhook. | DoorDash has no order time, only a pickup estimate. It is set once and not changed when the same order arrives again. |
| `raw_payload` | `{"webhook": ..., "order": ...}`: the webhook and the Get Order response, as received. | `{"event": ..., "order": ...}`, as received. | |
| `next_status` | Worked out by the API from `status`. Not stored. | Same. | Extra key. It tells the Admin which status button to show. It is `null` for `completed` and `cancelled`. |

### Status mapping

Both providers are mapped into one internal status. The order status comes from Get Order for Uber and from `event.status` for DoorDash. The webhook's `meta.status` is not used, because it only describes the notification.

| Provider | Provider value | Internal status | Note |
| --- | --- | --- | --- |
| Uber Eats | `current_state` CREATED | `new` | |
| Uber Eats | `current_state` ACCEPTED | `accepted` | |
| Uber Eats | `current_state` DENIED | `cancelled` | Uber's Order Integration guide (Denying Orders) says denied orders are "immediately canceled and the customer is notified". |
| Uber Eats | `current_state` CANCELED | `cancelled` | |
| Uber Eats | `current_state` FINISHED | `completed` | It is the only end state that is not a cancel or a deny. Get Order links to an "Order State" guide for the meaning of each state, but that link returns 404. |
| Uber Eats | `current_state` UNKNOWN | `new` | It is not an end state, so the order stays open and moves on with the next notification. |
| Uber Eats | missing or any other value | none | 400, and nothing is saved. |
| DoorDash | `event.status` NEW, with `event.type` `OrderCreate` | `new` | Every incoming DoorDash order has status NEW. |
| DoorDash | any other event type or status | none | 200 with `{"ignored": "<event type>"}`, and nothing is saved. |

The internal statuses, in order, are `new`, `accepted`, `preparing`, `ready` and `completed`, plus `cancelled`.

- When the same order arrives again, its status only moves forward. A `cancelled` from a provider always applies, and nothing moves an order out of `cancelled`.
- `preparing` and `ready` are set only by the status button in the Admin. They are never sent to Uber or DoorDash.
- `next_status` is the next step in that order. It is `null` for `completed` and `cancelled`.

### Sample files

The official examples are saved in `/fixtures`, and the original published text is kept in `fixtures/as-published/`. The published samples are not valid JSON in places: the Uber webhook sample has a stray `...`, the Get Order sample has four trailing commas, and the DoorDash sample is missing a comma after `"tax": 300`. The fixtures fix only these errors and even out the indentation. Nothing else is changed (`diff -w` shows every change).

- Uber Eats webhook: `fixtures/uber_webhook.json`
- Uber Eats Get Order response: `fixtures/uber_get_order.json`
- DoorDash order (the sample order inside the `event` envelope from the Order Integration page): `fixtures/doordash_order.json`

`fixtures/demo/` holds extra orders for the seed script and the simulator.

<details open>
<summary>My internal order (what <code>GET /api/orders/&lt;id&gt;</code> returns)</summary>

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

The line items add up to 900 but the total is 1399. That is how the official sample is written (the total includes fees), which is why I never compute the total from the items.

</details>

---

## 5. Conflict log

| Working note | Outcome | Reason / evidence |
| --- | --- | --- |
| Uber may include the full cart in the webhook; verify whether a Get Order call is still required. | Rejected. | The Uber webhook only sends an order notification. It does not carry the order. I must call the Get Order endpoint to get the full order. The `meta.resource_id` in the webhook is the order id to use in that call. Docs: [Get Order](https://developer.uber.com/docs/eats/references/api/v2/get-eats-order-orderid), [Orders notification webhook](https://developer.uber.com/docs/eats/references/api/webhooks.orders-notification) |
| DoorDash Marketplace line items may use a top-level items[]. | Rejected. | The DoorDash order has no top-level `items`. Items sit inside categories, at `order.categories[].items[]`. Each item has `name`, `price` and `quantity`, and may have `extras` with `options`. Docs: [Create webhook subscription](https://developer.doordash.com/en-US/docs/marketplace/overview/getting_started/create_webhook_subscription_getting_started/) |
| Verify which DoorDash monetary field should become total_cents and whether tax is included. | Changed. Verified. | The DoorDash Order model has no total field. Its money fields are `subtotal` and `tax` (both integers), plus the tip fields and `tax_amount_remitted_by_doordash`. **Units:** the Order model gives `subtotal` and `tax` only the type integer, with no unit. Other DoorDash pages state the unit. The Item-Level Tax Amount page says money is in "the same minor currency unit as other monetary fields (e.g., cents)". The Inventory/Pricing overview says prices are "in cents (e.g. $10.99 item will have base_price of 1099)". The Orders FAQ shows an item `price` of 510 as $5.10. **Tax is not inside the subtotal:** in the Split tax breakdown example, the items cost 1729 + 2879 = 4608, which is the `subtotal`. The tax is calculated on a `taxable_basis` of 4608, and its parts 277 + 46 = 323 are the `tax`. The Item-Level Tax Amount example shows the same thing: items 429 + 479 = 908 (`subtotal`), and item taxes 36 + 42 = 78 (`tax`). The Merchant Pick report also counts the order as "Subtotal + Tax" in its formula "Credit = Subtotal + Tax - Marketing Fees - Commissions ...". So `total_cents` is `subtotal + tax`. Tips are left out: `tip_amount` is the delivery tip and `merchant_tip_amount` is the tip for merchant staff. Docs: [Order model](https://developer.doordash.com/en-US/api/marketplace/#tag/Models/Order), [Split tax breakdown](https://developer.doordash.com/en-US/docs/marketplace/how_to/mpf_taxes), [Item-Level Tax Amount](https://developer.doordash.com/en-US/docs/marketplace/retail/orders/features/item_level_tax_amount), [Orders FAQ](https://developer.doordash.com/en-US/docs/marketplace/faq/order/), [Inventory/Pricing overview](https://developer.doordash.com/en-US/docs/marketplace/retail/inventory_pricing/overview/), [Merchant Pick report](https://developer.doordash.com/en-US/docs/reporting/overview/reports/marketplace_merchant_pick) |
| Verify Uber webhook signature generation and the X-Uber-Signature header. | Verified. | Uber sends the signature in the `X-Uber-Signature` header. It is a lowercase hexadecimal HMAC of the raw request body, using the client secret as the key and SHA256 as the hash. I compute the same value and compare it. Uber also sends an `X-Environment` header that says if the request comes from production or sandbox. The docs are not fully consistent: the header table calls the signature a "SHA256 hash", while the Webhook Security section describes an HMAC. I follow the Webhook Security section, because it gives the exact method and a Python example. Docs: [Orders notification webhook](https://developer.uber.com/docs/eats/references/api/webhooks.orders-notification) |
| Verify the exact Uber webhook response status/body. | Verified. | The docs say my endpoint must return HTTP 200 with an empty response body to confirm that the webhook was received. If Uber does not get a 200, it sends the event again, waiting 1 second, then 2, then 4, and so on, until 7 events in total have been sent. I return an empty 200 once the order is saved. If I cannot fetch the order from Get Order, I return 502 and save nothing, so Uber will retry. Docs: [Orders notification webhook](https://developer.uber.com/docs/eats/references/api/webhooks.orders-notification) |
| DoorDash Drive webhooks are optional. | Rejected. Not part of this task. | Drive is a separate DoorDash product. Its webhooks report events of a Drive delivery, for example when a Dasher picks up, drops off or the delivery is cancelled. Marketplace orders arrive through the Marketplace order webhook (`OrderCreate`), which is the only DoorDash webhook I build. So "optional" is the wrong frame: Drive webhooks do not apply here. Docs: [Receive orders from DoorDash](https://developer.doordash.com/en-US/docs/marketplace/how_to/order_integration/), [Drive webhooks](https://developer.doordash.com/en-US/docs/drive/reference/webhooks/) |
| Verify whether Uber webhook meta.resource_id corresponds to the Get Order id in the official examples. | Verified in the docs and in the webhook example. The Get Order example uses a different id. | The webhook docs say that for the Order API, `meta.resource_id` is equivalent to the `order_id`. The example webhook also shows this: the same id appears at the end of `resource_href` (`https://api.uber.com/v2/eats/order/153dd7f1-339d-4619-940c-418943c14636`), right after `/order/`, which is the Get Order path. So I use `meta.resource_id` as the order id when I call Get Order. The two official examples do not join up, though. The Get Order example is another order: its `id` is `f9f363d1-e1c2-4595-b477-c649845bc953`, not `153dd7f1-339d-4619-940c-418943c14636`. I did not edit either fixture. The local Get Order stand-in returns the official Get Order sample with its `id` set to the requested `resource_id`, and the API requires the fetched `id` to equal `resource_id`. If it differs, I return 502 and save nothing. Docs: [Orders notification webhook](https://developer.uber.com/docs/eats/references/api/webhooks.orders-notification) |
| Do not rely on a provider query parameter for normal provider detection. | Verified. | The official docs do not use a provider query parameter. Uber and DoorDash each post to the one webhook URL I give them, and nothing in the request says which provider it is except the message itself. The two messages look different, so I detect the provider from the shape of the body. An Uber message is one whose `meta` object has a `resource_id`. A DoorDash message is one that has both an `event` object and an `order` object. A message that matches neither shape (for example a DoorDash payload with no `event` or `order` object, or an Uber payload with no `meta.resource_id`) gets a 400. The fixtures have no `provider` field. Docs: [Orders notification webhook](https://developer.uber.com/docs/eats/references/api/webhooks.orders-notification), [Receive orders from DoorDash](https://developer.doordash.com/en-US/docs/marketplace/how_to/order_integration/) |
| Verify the documented location of DoorDash customer phone data. | Verified. | The customer phone is at `order.consumer.phone`, in the Order model of the API reference. The same `consumer` object has `id`, `email`, `first_name` and `last_name` (only the last name initial). By default this phone is the DoorDash support number, not the customer's. If the Masked Customer Phone Number feature is enabled for the store, it is a masked number that starts with `+` and the country code. DoorDash has no separate phone code or extension field. Docs: [Order model](https://developer.doordash.com/en-US/api/marketplace/#tag/Models/Order), [Implement masked customer phone number](https://developer.doordash.com/en-US/docs/marketplace/how_to/masked_cx_phone_number) |
| Normalize marketplace statuses into the internal status model where appropriate. | Verified. Done, and I added a few extra keys. | Uber and DoorDash use different status values, so I map both into one internal status. Uber Get Order has `current_state` with the values CREATED, ACCEPTED, DENIED, FINISHED, CANCELED and UNKNOWN. I map CREATED to new, ACCEPTED to accepted, DENIED to cancelled, CANCELED to cancelled, FINISHED to completed and UNKNOWN to new. DENIED becomes cancelled because the Order Integration guide says denied orders are "immediately canceled and the customer is notified". Get Order links to an "Order State" guide for the meaning of each state, but that link (`/docs/eats/guides/order-states`) returns 404. So FINISHED becomes completed because it is the only end state that is not a cancel or a deny, and UNKNOWN stays new because it is not an end state. The internal statuses are new, accepted, preparing, ready, completed and cancelled. Preparing and ready are set only by the admin button and are never sent to a provider. A missing or unrecognised Uber state is rejected with a 400. The webhook's `meta.status` only describes the notification (the docs list `pos`), not the order, so the order status comes from Get Order, not from the webhook. DoorDash sends every new order with the status NEW, so new orders start as new, and only an `OrderCreate` event with status NEW is saved. Status only moves forward, but a cancel from a provider always applies. Uber's separate cancel events are acknowledged and not used, so a cancel reaches the app only when Get Order returns CANCELED on a later notification. I added extra keys that the brief does not list, because the kitchen needs them: `line_items[].notes` (item special instructions, such as allergies), `customer.phone_code` (the code needed to use Uber's anonymized phone number) and `next_status` (tells the admin which status button to show). See the mapping table. Docs: [Get Order](https://developer.uber.com/docs/eats/references/api/v2/get-eats-order-orderid), [Uber Order Integration guide](https://developer.uber.com/docs/eats/guides/order_integration), [Receive orders from DoorDash](https://developer.doordash.com/en-US/docs/marketplace/how_to/order_integration/) |

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

| Order list | Order detail | Webhook simulator |
| --- | --- | --- |
| <img src="docs/screenshots/orders-list-mobile.png" alt="Order list on a phone" width="300"> | <img src="docs/screenshots/order-detail-mobile.png" alt="Order detail on a phone" width="300"> | <img src="docs/screenshots/webhook-simulator-mobile.png" alt="Webhook simulator on a phone" width="300"> |

---

## 7. Screen recording

_add recording_

---

## Developer Notes

- **Tech stack:** Django REST Framework, SQLite, React, JavaScript, Vite, and TanStack Query. I kept dependencies minimal and used plain CSS.
- **Order model:** I added kitchen instructions, Uber's customer phone code, and a calculated next status because they felt important for the kitchen workflow. The assignment defined the required fields but did not prohibit extending the internal model.
- **Order updates:** Added polling every 5 seconds to fetch the latest orders and update the table automatically. Requiring a manual refresh didn't feel right for a kitchen order dashboard.
- **Demo code:** Kept demo-related code in separate files and folders to make the main implementation easier to review and test.
- **Provider mapping:** Documented decisions around DoorDash totals, currency, timestamps, line items, and Uber status mapping. See the mapping table for details.
- **Duplicate webhooks:** Orders are identified by provider and external order ID. Repeated deliveries update existing orders instead of creating duplicates.
- **Testing and security:** Added 203 backend tests covering authentication, field mapping, duplicate orders, status transitions, and API failures. Tested the Admin manually on desktop and mobile.
- **Limitations:** The Uber Get Order client has not been tested against a live Uber account. Authentication, DoorDash OAuth, outbound status updates, and automated frontend tests are not included.
- **Next steps:** For production, I'd move webhook processing to background jobs, switch to PostgreSQL, add authentication, and migrate the Admin from JavaScript to TypeScript as it grows.
