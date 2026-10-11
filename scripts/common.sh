# Shared helpers for the webhook scripts. Source this file; do not run it.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_API_URL="http://localhost:8000"
WEBHOOK_PATH="/api/webhooks/orders"
REQUEST_TIMEOUT_SECONDS=10
RESOURCE_ID_PATTERN='^[A-Za-z0-9_-]+$'
ENV_LINE_PATTERN='^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)=(.*)$'

strip_quotes() {
  local value="$1"
  value="${value%"${value##*[![:space:]]}"}"
  if [[ "$value" =~ ^\"(.*)\"$ || "$value" =~ ^\'(.*)\'$ ]]; then
    value="${BASH_REMATCH[1]}"
  fi
  printf '%s' "$value"
}

# .env is read as NAME=value lines, never run as shell code, so a pasted
# command in it cannot start anything. A variable already set in the shell wins.
load_env() {
  if [[ ! -f "$ROOT/.env" ]]; then
    echo "Missing $ROOT/.env. Copy .env.example to .env first." >&2
    exit 1
  fi
  local line name
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ $ENV_LINE_PATTERN ]] || continue
    name="${BASH_REMATCH[1]}"
    [[ -n "${!name+set}" ]] && continue
    export "$name=$(strip_quotes "${BASH_REMATCH[2]}")"
  done < "$ROOT/.env"
  # The Admin finds the API through API_PROXY_TARGET, so the scripts follow
  # the same setting and a new port is changed in one place.
  local api_url="${API_PROXY_TARGET:-$DEFAULT_API_URL}"
  WEBHOOK_URL="${WEBHOOK_URL:-${api_url%/}$WEBHOOK_PATH}"
  if [[ "$WEBHOOK_URL" =~ [[:space:]] ]]; then
    echo "The webhook address \"$WEBHOOK_URL\" contains a space." \
      "In .env, write only NAME=value on each line, with no command after it." >&2
    exit 1
  fi
}

post_webhook() {
  local label="$1" body_file="$2"
  shift 2
  local status
  if ! status="$(curl --silent --output /dev/null --write-out '%{http_code}' \
    --max-time "$REQUEST_TIMEOUT_SECONDS" \
    --request POST "$WEBHOOK_URL" \
    --header "Content-Type: application/json" "$@" \
    --data-binary @"$body_file" 2>/dev/null)"; then
    echo "$label: could not reach $WEBHOOK_URL, or it did not answer within" \
      "$REQUEST_TIMEOUT_SECONDS seconds. Is the API running there? Check API_PROXY_TARGET in .env." >&2
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
