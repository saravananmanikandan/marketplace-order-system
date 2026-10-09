#!/usr/bin/env bash
# Usage: scripts/send_uber_webhook.sh [resource_id]
# With no argument, sends fixtures/uber_webhook.json exactly as it is. With an
# id, signs and sends a temporary copy that carries that id.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
load_env

OFFICIAL_WEBHOOK="$ROOT/fixtures/uber_webhook.json"

if [[ $# -eq 0 ]]; then
  send_uber_file "$OFFICIAL_WEBHOOK"
  exit
fi

RESOURCE_ID="$1"
if [[ ! "$RESOURCE_ID" =~ $RESOURCE_ID_PATTERN ]]; then
  echo "resource_id may only contain letters, digits, - and _." >&2
  exit 1
fi

make_temp_file
python3 - "$OFFICIAL_WEBHOOK" "$RESOURCE_ID" > "$TEMP_FILE" <<'PY'
import json
import sys

path, resource_id = sys.argv[1:3]
payload = json.load(open(path))
payload["meta"]["resource_id"] = resource_id
payload["resource_href"] = payload["resource_href"].rsplit("/", 1)[0] + "/" + resource_id
print(json.dumps(payload, indent=2))
PY
send_uber_file "$TEMP_FILE"
