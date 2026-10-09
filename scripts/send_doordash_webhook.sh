#!/usr/bin/env bash
# Usage: scripts/send_doordash_webhook.sh [order_id]
# With no argument, sends fixtures/doordash_order.json exactly as it is. With an
# id, sends a temporary copy whose order.id is that id.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
load_env

OFFICIAL_WEBHOOK="$ROOT/fixtures/doordash_order.json"

if [[ $# -eq 0 ]]; then
  send_doordash_file "$OFFICIAL_WEBHOOK"
  exit
fi

make_temp_file
python3 - "$OFFICIAL_WEBHOOK" "$1" > "$TEMP_FILE" <<'PY'
import json
import sys

path, order_id = sys.argv[1:3]
payload = json.load(open(path))
payload["order"]["id"] = order_id
print(json.dumps(payload, indent=2))
PY
send_doordash_file "$TEMP_FILE"
