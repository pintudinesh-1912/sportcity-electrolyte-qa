# Part 3: Electrolyte API automation (pytest + Allure)

A small suite automating the highest-risk Part 1 cases: 47 test cases from 18 test functions across auth, members, pricing, schedule and timezone, booking eligibility and idempotency.

## Run it

Requires Python 3.11+ and Node.js (for the mock). The Allure CLI is optional and only needed to build the HTML report.

```bash
cd part3-automation
python3 -m venv .venv && source .venv/bin/activate      # or reuse the repo's ../.venv
pip install -r requirements.txt

# Recommended: the suite starts its own mock on a free port (fresh seed) and stops it afterwards
MOCK_DIR=/path/to/SportCity-QA-candidate-kit/mock-server ./run-tests.sh

# Or target an already-running API (must be freshly seeded)
BASE_URL=http://localhost:3000 ./run-tests.sh

# Any extra args go to pytest
./run-tests.sh -k idempotency -v
```

`run-tests.sh` runs pytest, then builds `allure-report/index.html`, a single self-contained file you can open directly. If Java is not on your PATH it falls back to Homebrew's `openjdk`.

| Variable | Default | Purpose |
|---|---|---|
| `BASE_URL` | `http://localhost:3000` | API under test (ignored when `MOCK_DIR` is set) |
| `API_KEY` | `sportcity-test-key` | `X-Api-Key` header |
| `HTTP_TIMEOUT` | `5` | Per-request timeout (s) |
| `MOCK_DIR` | (unset) | Kit `mock-server/` dir. When set, the suite manages its own mock |

## Expected result today

`40 passed, 7 xfailed`. Each xfail is an open finding from the Part 2 report (F1, F2, F3, F4, F6, F7), marked `xfail(strict=True)`:

- while the bug is open, the test reports **XFAIL** (shown under *Known product bugs* in Allure);
- when the bug is fixed, the test **XPASSes and strict mode turns the run red**, so the marker is removed and the test becomes a regression guard;
- `pytest --runxfail` runs them as ordinary tests to see the real failures.

## Design

```
conftest.py          session setup/teardown: config from env, suite-managed mock, API client,
                     seed snapshot, Allure environment + categories
data/pg_truth.json   expected state transcribed from the Perfect Gym screens (source of truth)
schemas/*.json       JSON Schema 2020-12 per contract object (from openapi.yaml, plus `required`),
                     linked with $ref and validated with jsonschema + referencing
support/
  api_client.py      requests wrapper; every call becomes an Allure step with the request/response attached
  assertions.py      assert_status / assert_schema / assert_error / check: failures embed the full exchange
  known_bugs.py      finding registry -> xfail(strict) + Allure issue link
tests/               one module per area, numbered to match the Part 1 collection
```

- **Value assertions, not just status codes.** Profiles are compared field by field with PG. Prices are checked as EUR with at most 2 decimals, against the catalogue and the tier rule. Times are checked for the same instant as PG and the correct Amsterdam offset for that date (CEST `+02:00` in June, CET `+01:00` in November, computed with `zoneinfo`, not hard-coded). Spots are checked against PG capacity.
- **Parameterisation:** member, plan and class cases are driven from `pg_truth.json`. Known bugs are applied per parameter where only some cases fail (for example only C-2004 for availability).
- **State and order.** The API has no delete endpoint, so tests cannot clean up after themselves. Instead, the session gets an isolated mock that is discarded at teardown. Booking tests assert **deltas** (spots before and after). Availability-vs-PG checks use a class snapshot taken at session start, before anything is booked.
- **Evidence on failure:** every failure message ends with the full API exchange (method, URL, headers with the key masked, bodies, status and timing), and every request is also attached to its Allure step.

## Not automated (yet)

- A full validation and error-contract matrix (400 vs 404 for missing fields and malformed JSON, findings F8 and F9). This is covered in the Part 1 collection.
- Mobile rendering (F5, client side). This needs UI or contract tests on the app.
- Concurrency: parallel bookings for the last spot, and idempotency under concurrent retries.
- In CI: run against a deployed Electrolyte with PG truth read from PG's API instead of a JSON file, and publish the Allure results per build.
