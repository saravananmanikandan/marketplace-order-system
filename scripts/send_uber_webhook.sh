#!/usr/bin/env bash
# Usage: scripts/send_uber_webhook.sh [webhook-file]
# Signs the file with the Uber client secret from .env and posts it as raw bytes.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a
source "$ROOT/.env"
set +a

WEBHOOK_FILE="${1:-$ROOT/fixtures/uber_webhook.json}"
WEBHOOK_URL="${WEBHOOK_URL:-http://localhost:8000/api/webhooks/orders}"

SIGNATURE="$(openssl dgst -sha256 -hmac "$UBER_CLIENT_SECRET" "$WEBHOOK_FILE" | awk '{print $NF}')"

curl --silent --show-error --output /dev/null --write-out "Uber webhook: HTTP %{http_code}\n" \
  --request POST "$WEBHOOK_URL" \
  --header "Content-Type: application/json" \
  --header "X-Uber-Signature: $SIGNATURE" \
  --data-binary @"$WEBHOOK_FILE"
