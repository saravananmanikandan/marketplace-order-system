#!/usr/bin/env bash
# Usage: scripts/seed_demo.sh
# Sends only the demo orders, so the README curl examples (the official
# samples) still add new orders after seeding. The list then shows 5 orders.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
load_env

send_uber_file "$ROOT/fixtures/demo/uber_webhook.json"
send_doordash_file "$ROOT/fixtures/demo/doordash_order_2.json"
send_doordash_file "$ROOT/fixtures/demo/doordash_order_3.json"
