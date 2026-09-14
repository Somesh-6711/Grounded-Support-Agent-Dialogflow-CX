#!/usr/bin/env bash
# Verify the deployed service before you wire it into the agent. If any of
# these fail, fix them here rather than debugging inside the console.
set -euo pipefail

BASE="${1:-http://localhost:8080}"
pass=0; fail=0

check () {
  local label="$1" expected="$2" actual="$3"
  if [ "$actual" = "$expected" ]; then
    echo "  PASS  $label"
    pass=$((pass+1))
  else
    echo "  FAIL  $label (expected $expected, got $actual)"
    fail=$((fail+1))
  fi
}

code () { curl -s -o /dev/null -w '%{http_code}' "$@"; }

echo "Smoke testing $BASE"

check "health" 200 "$(code "$BASE/healthz")"

check "account lookup" 200 "$(code -X POST "$BASE/tools/account-status" \
  -H 'Content-Type: application/json' -d '{"account_id":"OPT-10045512"}')"

check "malformed account rejected" 400 "$(code -X POST "$BASE/tools/account-status" \
  -H 'Content-Type: application/json' -d '{"account_id":"nope"}')"

check "outage check" 200 "$(code -X POST "$BASE/tools/outage-check" \
  -H 'Content-Type: application/json' -d '{"zip_code":"11375"}')"

check "unconfirmed booking blocked" 409 "$(code -X POST "$BASE/tools/schedule-technician" \
  -H 'Content-Type: application/json' \
  -d '{"account_id":"OPT-10045512","preferred_date":"2026-09-14","window":"08:00-12:00","confirm":false}')"

check "cx webhook" 200 "$(code -X POST "$BASE/webhook" \
  -H 'Content-Type: application/json' \
  -d '{"fulfillmentInfo":{"tag":"lookup-account"},"sessionInfo":{"parameters":{"account_id":"OPT-30099001"}}}')"

echo
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
