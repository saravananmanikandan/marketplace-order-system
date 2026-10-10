# Demo app

Demo-only tools. Not part of the assignment requirements. Delete this folder to remove them.

- Loaded only when `DEMO_ENABLED` is true (see `config/settings.py` and `config/urls.py`).
- `GET /demo/mock/uber/v2/eats/order/<id>` is a local stand-in for Uber's Get Order endpoint. It needs `Authorization: Bearer <UBER_ACCESS_TOKEN>`.
- `StagedOrderClient` serves a staged order for an id, then a file in `fixtures/demo/uber_orders/`, then the official Get Order sample with `id` set to the requested id.
- Staged orders are kept in process memory only (the 100 most recent). They are lost when the server restarts.
