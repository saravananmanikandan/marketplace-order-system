#!/usr/bin/env bash
# Usage: scripts/seed_demo.sh
# Sends the official samples and the demo variants, so the list shows 4 orders.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
load_env

send_uber_file "$ROOT/fixtures/uber_webhook.json"
send_doordash_file "$ROOT/fixtures/doordash_order.json"
send_uber_file "$ROOT/fixtures/demo/uber_webhook.json"
send_doordash_file "$ROOT/fixtures/demo/doordash_order_2.json"
