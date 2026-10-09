#!/usr/bin/env bash
# Usage: scripts/send_doordash_webhook.sh [webhook-file]
# Posts the file with the Authorization value from .env.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a
source "$ROOT/.env"
set +a

WEBHOOK_FILE="${1:-$ROOT/fixtures/doordash_order.json}"
WEBHOOK_URL="${WEBHOOK_URL:-http://localhost:8000/api/webhooks/orders}"

curl --silent --show-error --output /dev/null --write-out "DoorDash webhook: HTTP %{http_code}\n" \
  --request POST "$WEBHOOK_URL" \
  --header "Content-Type: application/json" \
  --header "Authorization: $DOORDASH_WEBHOOK_AUTH_HEADER" \
  --data-binary @"$WEBHOOK_FILE"
