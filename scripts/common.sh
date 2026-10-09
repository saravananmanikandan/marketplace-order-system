# Shared helpers for the webhook scripts. Source this file; do not run it.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEBHOOK_URL="${WEBHOOK_URL:-http://localhost:8000/api/webhooks/orders}"
RESOURCE_ID_PATTERN='^[A-Za-z0-9_-]+$'

load_env() {
  if [[ ! -f "$ROOT/.env" ]]; then
    echo "Missing $ROOT/.env. Copy .env.example to .env first." >&2
    exit 1
  fi
  set -a
  source "$ROOT/.env"
  set +a
}

post_webhook() {
  local label="$1" body_file="$2"
  shift 2
  local status
  if ! status="$(curl --silent --output /dev/null --write-out '%{http_code}' \
    --request POST "$WEBHOOK_URL" \
    --header "Content-Type: application/json" "$@" \
    --data-binary @"$body_file" 2>/dev/null)"; then
    echo "$label: could not reach $WEBHOOK_URL. Is the backend running?" >&2
    return 1
  fi
  echo "$label: HTTP $status"
  [[ "$status" == 2* ]]
}

send_uber_file() {
  local signature
  signature="$(openssl dgst -sha256 -hmac "$UBER_CLIENT_SECRET" "$1" | awk '{print $NF}')"
  post_webhook "Uber webhook" "$1" --header "X-Uber-Signature: $signature"
}

send_doordash_file() {
  post_webhook "DoorDash webhook" "$1" --header "Authorization: $DOORDASH_WEBHOOK_AUTH_HEADER"
}

make_temp_file() {
  TEMP_FILE="$(mktemp)"
  trap 'rm -f "$TEMP_FILE"' EXIT
}
