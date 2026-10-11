# Marketplace order ingestion

Orders from Uber Eats and DoorDash arrive at one webhook endpoint, are saved in one
internal order model, and are managed in a small React admin.

- `api/` Django REST Framework API (SQLite)
- `admin/` React and Vite admin
- `fixtures/` sample provider payloads (`fixtures/demo/` has extra demo orders)
- `scripts/` helpers that send the sample webhooks
- `docs/` documentation checks

## Prerequisites

- Python 3.12 or newer (Django 6 needs it)
- Node.js 20.19 or newer (or 22.12 or newer), with npm
- openssl (used to sign the Uber webhook)
- curl

## Setup

Run these from the repository root.

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r api/requirements.txt
cp .env.example .env
```

`.env` holds the configuration and is never committed. `.env.example` lists every
variable with a development value. The app refuses to start if a required one is missing.

## Run the backend

```
source .venv/bin/activate
cd api
python manage.py migrate
python manage.py runserver
```

The API is now at http://localhost:8000.

## Run the frontend

In a second terminal:

```
cd admin
npm install
npm run dev
```

Open http://localhost:5173. Vite forwards `/api` requests to port 8000.

Click a column header to sort by it; click it again to reverse. On narrow screens, use the
"Sort by" menu instead. The sort is kept in the address (`ordering`), so reload and Back keep it.

The admin polls the API every 5 seconds. Server-sent events or WebSockets would be the next step if volume required it.

## Send the sample webhooks

With the backend running, use the scripts. They read `.env` and sign or authorize the
request for you.

```
scripts/send_uber_webhook.sh
scripts/send_doordash_webhook.sh
```

Each prints `HTTP 200` on success. Running one again does not create a second order.

To send them by hand, run these from the repository root. Each block is complete: it
loads `.env`, holds the whole JSON body, and sends it. You can paste a block into a new
terminal as it is.

Uber Eats. The signature is the HMAC-SHA256 of the exact body, made with your client
secret:

```
set -a; source .env; set +a

BODY=$(cat <<'EOF'
{
  "event_type": "orders.notification",
  "event_id": "c4d2261e-2779-4eb6-beb0-cb41235c751e",
  "event_time": 1427343990,
  "meta": {
    "resource_id": "153dd7f1-339d-4619-940c-418943c14636",
    "status": "pos",
    "user_id": "89dd9741-66b5-4bb4-b216-a813f3b21b4f"
  },
  "resource_href": "https://api.uber.com/v2/eats/order/153dd7f1-339d-4619-940c-418943c14636"
}
EOF
)

SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$UBER_CLIENT_SECRET" | awk '{print $NF}')

curl -i -X POST http://localhost:8000/api/webhooks/orders \
  -H "Content-Type: application/json" \
  -H "X-Uber-Signature: $SIG" \
  --data-binary "$BODY"
```

To send another order, change `meta.resource_id` and the end of `resource_href` to the same
new id (letters, digits, `-` and `_`). Or use the script: `scripts/send_uber_webhook.sh my-uber-order-1`.

DoorDash:

```
set -a; source .env; set +a

curl -i -X POST http://localhost:8000/api/webhooks/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: $DOORDASH_WEBHOOK_AUTH_HEADER" \
  --data-binary @- <<'EOF'
{
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
}
EOF
```

DoorDash answers `200` with the order confirmation, for example `{"merchant_supplied_id": "2", "order_status": "success"}`. The id is the internal order id.

To send another order, change `order.id`. Or use the script: `scripts/send_doordash_webhook.sh my-doordash-order-1`.

### More orders

Load the demo set (5 orders in total) in one go:

```
scripts/seed_demo.sh
```

Send one more order by giving the script a new id. Uber ids may use letters, digits, `-`
and `_`:

```
scripts/send_uber_webhook.sh my-uber-order-1
scripts/send_doordash_webhook.sh my-doordash-order-1
```

If the backend is not running, the scripts say so and exit with an error.

## Read the API

`ordering` can be `provider`, `external_order_id`, `customer_name`, `status` (workflow order), `total_cents` or `created_at`. Put `-` in front for descending. Anything else means `-created_at`.

```
curl "http://localhost:8000/api/orders"
curl "http://localhost:8000/api/orders?provider=uber&status=new&search=larry&ordering=created_at&page=1"
curl "http://localhost:8000/api/orders/1"
curl -X PATCH "http://localhost:8000/api/orders/1/status"
```

## Run the tests

```
source .venv/bin/activate
cd api
python manage.py test
```

## Build the frontend

```
cd admin
npm run build
```

## Developer Notes

Where the provider documentation is silent, the choice is recorded here.

- DoorDash has no total field. `total_cents` is `subtotal + tax`, and both are read as cents because the sample values (2000 and 300) look like cents.
- The DoorDash sample has no currency, so `DEFAULT_CURRENCY` is used.
- DoorDash has no creation time (only a pickup estimate), so `created_at` is the time the webhook was received. Uber orders use `placed_at` when it has a timezone offset, and the received time otherwise.
- A DoorDash item `price` is treated as a unit price, so the line total is `price * quantity`.
