# Marketplace order ingestion

Orders from Uber Eats and DoorDash arrive at one webhook endpoint, are saved in one
internal order model, and are managed in a small React admin.

- `api/` Django REST Framework API (SQLite)
- `admin/` React and Vite admin
- `fixtures/` sample provider payloads (`fixtures/demo/` has extra demo orders)
- `scripts/` helpers that send the sample webhooks
- `docs/` design decisions and documentation checks

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

## Send the sample webhooks

With the backend running, use the scripts. They read `.env` and sign or authorize the
request for you.

```
scripts/send_uber_webhook.sh
scripts/send_doordash_webhook.sh
```

Each prints `HTTP 200` on success. Running one again does not create a second order.

To do the same by hand, run these from the repository root. They use the development
values from `.env.example`. Change them if you changed `.env`.

Uber Eats (the signature is the HMAC-SHA256 of the file bytes, so use `--data-binary`):

```
curl -i -X POST http://localhost:8000/api/webhooks/orders \
  -H "Content-Type: application/json" \
  -H "X-Uber-Signature: $(openssl dgst -sha256 -hmac 'dev-uber-client-secret-0001' fixtures/uber_webhook.json | awk '{print $NF}')" \
  --data-binary @fixtures/uber_webhook.json
```

DoorDash:

```
curl -i -X POST http://localhost:8000/api/webhooks/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-doordash-token-0001" \
  --data-binary @fixtures/doordash_order.json
```

### More demo orders

The scripts accept another file as their first argument:

```
scripts/send_doordash_webhook.sh fixtures/demo/doordash_order_2.json
scripts/send_doordash_webhook.sh fixtures/demo/doordash_order_3.json
```

The Uber lookup is served from a fixture file. To ingest the Uber demo order, start the
backend with the demo lookup file, then send the demo webhook:

```
UBER_GET_ORDER_FIXTURE=fixtures/demo/uber_get_order.json python manage.py runserver
scripts/send_uber_webhook.sh fixtures/demo/uber_webhook.json
```

## Read the API

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
