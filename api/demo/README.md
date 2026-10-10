# Demo app

Demo-only tools. Not part of the assignment requirements. Delete this folder to remove them.

- Loaded only when `DEMO_ENABLED` is true (see `config/settings.py` and `config/urls.py`).
- `GET /demo/mock/uber/v2/eats/order/<id>` is a local stand-in for Uber's Get Order endpoint. It needs `Authorization: Bearer <UBER_ACCESS_TOKEN>`.
- `StagedOrderClient` serves a staged order for an id, then a file in `fixtures/demo/uber_orders/`, then the official Get Order sample with `id` set to the requested id.
- Staged orders are kept in process memory only (the 100 most recent). They are lost when the server restarts.

## Webhook simulator

- `GET /demo/api/config` lists the providers, presets, Uber states, limits and the last order id sent per provider.
- `POST /demo/api/send` builds a webhook from the official fixtures, signs or authorizes it like the provider would, and sends it with real HTTP to this project's own `/api/webhooks/orders`. The reply shows each delivery's status and body, and what was sent (the Uber signature is shown; the client secret never is, and the DoorDash token is masked).
- Uber orders are staged in memory before the notification is sent, so `StagedOrderClient` (or the mock behind `HttpOrderClient`) can return them.
- `POST /demo/api/curl` takes the same options but sends nothing: it returns a ready-to-run curl command for one delivery, with a new order id each time (unless an id is given), so pasting it adds a new order. Uber orders are staged at that moment so the core can fetch them when the command runs. The body is quoted byte for byte, so the Uber signature matches; DoorDash commands read the token from `.env` with `$DOORDASH_WEBHOOK_AUTH_HEADER`, so the token never appears in the page.
- `deliveries: 2` sends two identical requests at the same moment from two threads. The server must handle requests in parallel; `python manage.py runserver` is threaded by default.
