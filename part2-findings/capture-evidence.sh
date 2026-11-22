#!/usr/bin/env bash
# Capture raw request/response evidence for Part 2 tasks T1-T6.
# Each task writes evidence/Tn-*.txt containing the exact curl command and the full
# HTTP response (status line, headers, body). Run against a FRESHLY started mock:
#
#   MOCK_DIR=/path/to/mock-server ./part2-findings/capture-evidence.sh --restart
#   BASE_URL=http://host:3000 ./part2-findings/capture-evidence.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/evidence"
BASE_URL="${BASE_URL:-http://localhost:3000}"
API_KEY="${API_KEY:-sportcity-test-key}"
mkdir -p "$OUT"
rm -f "$OUT"/T*.txt

if [[ "${1:-}" == "--restart" ]]; then
  : "${MOCK_DIR:?Set MOCK_DIR to the kit mock-server directory}"
  pkill -f "node server.js" 2>/dev/null || true
  (cd "$MOCK_DIR" && exec nohup node server.js) < /dev/null > "$OUT/mock-server.log" 2>&1 &
  for _ in $(seq 1 40); do curl -s -o /dev/null "$BASE_URL" && break; sleep 0.25; done
fi

# call <file> <METHOD> <path> [json-body] [extra curl args...]
call() {
  local file="$OUT/$1" method="$2" path="$3" body="${4:-}"; shift 4 || shift $#
  local args=(-s -i -X "$method" -H "X-Api-Key: $API_KEY" -H "Content-Type: application/json" "$@")
  [[ -n "$body" ]] && args+=(-d "$body")
  {
    printf "\$ curl -X %s %s%s -H 'X-Api-Key: %s' -H 'Content-Type: application/json'" "$method" "$BASE_URL" "$path" "$API_KEY"
    for a in "$@"; do printf ' %q' "$a"; done
    [[ -n "$body" ]] && printf " -d '%s'" "$body"
    printf '\n\n'
    curl "${args[@]}" "$BASE_URL$path" | tr -d '\r'
    printf '\n\n'
  } >> "$file"
}
spots() { # spots <file> <classId> <label>
  local n
  n=$(curl -s -H "X-Api-Key: $API_KEY" "$BASE_URL/v1/classes" |
      python3 -I -c "import json,sys; print(next(c['spots_available'] for c in json.load(sys.stdin)['data'] if c['id']=='$2'))")
  printf '# spots_available for %s %s: %s\n\n' "$2" "$3" "$n" >> "$OUT/$1"
}

# T1: member profiles
for m in M-1001 M-1002 M-1003 M-1004 M-9999; do call T1-members.txt GET "/v1/members/$m"; done

# T2: HIIT Express availability vs booking
call T2-hiit-availability.txt GET /v1/classes
call T2-hiit-availability.txt POST /v1/bookings '{"memberId":"M-1001","classId":"C-2004"}'

# T3: plan prices (catalogue and point of sale)
call T3-pricing.txt GET /v1/plans
for p in CITY-ONE CITY-PLUS CITY-STUDENT; do
  call T3-pricing.txt POST /v1/memberships "{\"memberId\":\"M-1004\",\"planId\":\"$p\"}"
done
call T3-pricing.txt GET /v1/members/M-1004   # profile after purchase

# T4: Spinning bookings for ACTIVE / FROZEN / EXPIRED members
spots T4-spinning-bookings.txt C-2001 "before any booking"
for m in M-1001 M-1002 M-1003; do
  call T4-spinning-bookings.txt POST /v1/bookings "{\"memberId\":\"$m\",\"classId\":\"C-2001\"}"
  spots T4-spinning-bookings.txt C-2001 "after booking by $m"
done

# T5: BodyPump booking retried with the same Idempotency-Key
KEY="t5-$(date +%s)"
spots T5-idempotency.txt C-2003 "before booking"
call T5-idempotency.txt POST /v1/bookings '{"memberId":"M-1001","classId":"C-2003"}' -H "Idempotency-Key: $KEY"
call T5-idempotency.txt POST /v1/bookings '{"memberId":"M-1001","classId":"C-2003"}' -H "Idempotency-Key: $KEY"
spots T5-idempotency.txt C-2003 "after original + retry (expected: before - 1)"

# T6: Spinning start_time as served to the app
call T6-spinning-time.txt GET /v1/classes

echo "Evidence written to $OUT:"; ls -1 "$OUT"
