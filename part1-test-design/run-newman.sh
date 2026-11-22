#!/usr/bin/env bash
# Run the Electrolyte collection with Newman and write HTML (htmlextra) + JUnit reports.
#
# Usage:
#   ./part1-test-design/run-newman.sh                 # against BASE_URL (default http://localhost:3000)
#   BASE_URL=http://host:3000 ./part1-test-design/run-newman.sh
#   MOCK_DIR=/path/to/mock-server ./part1-test-design/run-newman.sh --restart
#        --restart: (re)start the mock first so seeded data is fresh. The collection
#        mutates state (purchases, bookings), so results are only meaningful on a fresh mock.
#
# Exit code is non-zero when assertions fail. That is expected while known bugs are open.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
BASE_URL="${BASE_URL:-http://localhost:3000}"
REPORT_DIR="$HERE/reports"
mkdir -p "$REPORT_DIR"

if [[ "${1:-}" == "--restart" ]]; then
  : "${MOCK_DIR:?Set MOCK_DIR to the kit mock-server directory}"
  pkill -f "node server.js" 2>/dev/null || true
  (cd "$MOCK_DIR" && exec nohup node server.js) < /dev/null > "$REPORT_DIR/mock-server.log" 2>&1 &
  for _ in $(seq 1 40); do
    curl -s -o /dev/null "$BASE_URL" && break
    sleep 0.25
  done
fi

npx --yes -p newman@6 -p newman-reporter-htmlextra@1 newman run \
  "$HERE/Electrolyte.postman_collection.json" \
  -e "$HERE/local.postman_environment.json" \
  --env-var "baseUrl=$BASE_URL" \
  --reporters cli,htmlextra,junit \
  --reporter-htmlextra-export "$REPORT_DIR/newman-report.html" \
  --reporter-htmlextra-title "SportCity Electrolyte API: Newman run" \
  --reporter-htmlextra-browserTitle "Electrolyte Newman" \
  --reporter-htmlextra-showEnvironmentData \
  --reporter-junit-export "$REPORT_DIR/newman-junit.xml"
