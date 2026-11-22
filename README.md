# SportCity QA assessment: Electrolyte API

Black-box testing of **Electrolyte**, the integration layer between the SportCity apps and Perfect Gym (PG, the source of truth), for the sign-up → membership → class-booking flow.

**Verdict: NO-GO.** 9 findings, 3 of them critical. See [`part2-findings/findings-report.pdf`](part2-findings/findings-report.pdf).

## What's here

| Part | Deliverable | Where |
|---|---|---|
| 1. Test design | Postman v2.1 collection: 37 requests, 213 assertions, priority + risk per request | [`part1-test-design/`](part1-test-design/) |
| 1. Report | Newman htmlextra and JUnit reports from the latest run | `part1-test-design/reports/` |
| 2. Findings | Findings report (2 pages + appendix) with go/no-go and top-3 fixes | [`part2-findings/findings-report.pdf`](part2-findings/findings-report.pdf) |
| 2. Evidence | Raw curl request/response per task, and PG/DataDog/app screens | `part2-findings/evidence/` |
| 3. Automation | pytest suite with an Allure report: 47 cases, 40 pass and 7 are expected failures for known bugs | [`part3-automation/`](part3-automation/) |
| Reference | The kit's `openapi.yaml` and `test-data.md` | `reference/` |

## Findings at a glance

| ID | Finding | Severity | Layer |
|---|---|---|---|
| F1 | FROZEN/EXPIRED members get `201 CONFIRMED`, although PG rejected the booking (422) | Critical | Electrolyte |
| F2 | Retry with the same `Idempotency-Key` creates a duplicate booking | Critical | Electrolyte |
| F3 | City Plus (€34.99) priced below City One (€39.99) | Critical | Perfect Gym config |
| F4 | HIIT Express shows 4 spots; PG is full (20/20) | High | Electrolyte |
| F5 | App shows Spinning at 16:00; the API correctly returns 18:00+02:00 | High | Client |
| F6 | Purchased membership not reflected in the member profile | High | Electrolyte / PG |
| F7 | Unknown member returns `200 null` instead of 404 | Medium | Electrolyte |
| F8 | Duplicate booking possible without a key; repeat purchases allowed | Medium | Electrolyte |
| F9 | Validation errors returned as 404, not 400; "undefined" leaks into a message | Low | Electrolyte |

**Top 3 to fix:** F1, F3 and F2. The reasoning is in the report.

## Run everything

Prerequisites: Node.js 16+ (mock and Newman via `npx`), Python 3.11+, and optionally the Allure CLI (needs Java) and Chrome (for the PDF).

```bash
export MOCK_DIR=/path/to/SportCity-QA-candidate-kit/mock-server

# Python deps (uv, or: python3 -m venv .venv && .venv/bin/pip install -r part3-automation/requirements.txt)
uv sync

# Part 1: run the collection on a fresh mock -> part1-test-design/reports/newman-report.html
./part1-test-design/run-newman.sh --restart

# Part 2: regenerate the evidence and rebuild the PDF
./part2-findings/capture-evidence.sh --restart
uv run --group report python part2-findings/build_report.py

# Part 3: pytest with a suite-managed mock -> part3-automation/allure-report/index.html
./part3-automation/run-tests.sh
```

The collection and the evidence script change data on the server (purchases, bookings). Run them with `--restart` so they start from fresh seed data. The pytest suite starts its own isolated mock on a free port.

**Bruno:** import `part1-test-design/Electrolyte.postman_collection.json` via *Import → Postman Collection* for hand exploration. Newman is the reference runner, because the schema assertions use `pm.response.to.have.jsonSchema`.

## Approach

1. **Spec first.** `openapi.yaml` and the acceptance criteria define the expected behaviour. The PG screens define the expected *data*. Every assertion encodes intended behaviour, so failing tests are findings.
2. **Risk-based priority.** P0 covers money, booking eligibility and data members see. P1 covers contract, validation and consistency. P2 covers robustness.
3. **Layer attribution by triangulation.** API response vs PG (truth) vs DataDog (what Electrolyte did) vs the app screen. For example, T6's API time is correct and only the new class renders wrong, so the fault is in the client. In T4, the trace shows PG returning 422 while Electrolyte returns 201, so the fault is in Electrolyte.
4. **Reproducible evidence.** Collections and scripts regenerate every report from a fresh mock. Failed assertions in Newman and pytest carry the full request and response.

## Assumptions and open questions

- PG screens are taken as current truth. In a real environment, expected data would come from PG's API, not transcribed JSON.
- F3 is attributed to PG configuration because the API mirrors PG exactly. Whether Electrolyte should also guard the tier rule is a product decision.
- F6: from the outside I cannot tell whether the purchase reaches PG. It needs triage with PG access.
- F8: the contract only mandates key-based de-duplication. Whether the same member + class should be unique is a product question.
- The API exposes no class end time or duration, so the app's "16:00–16:45" range cannot be checked against the contract.

## Not done / next steps

- UI or contract tests for the mobile app (F5) and consumer-driven contract tests between the app and Electrolyte.
- Concurrency: last-spot races and parallel idempotent retries.
- Wire both suites into CI against a deployed environment and publish Newman and Allure per build.
- Confirm the Bruno round-trip of the collection's scripts.

## AI usage and time

**Tools:** Claude Code (Anthropic) was used as a pair-tester throughout:
- planning the approach;
- exploring the API with curl;
- generating the Postman collection from a Python script;
- drafting the findings report;
- writing the pytest suite.

I reviewed every finding against the raw evidence, made the prioritisation and release decisions, and directed the changes (for example, request/response details on every failed assertion, and Allure and Newman reporting). The mock server was treated as a black box: its source was never read.

**Time spent (approximate):**

| Part | Time |
|---|---|
| Setup and planning | _fill in_ |
| Part 1: test design | _fill in_ |
| Part 2: findings | _fill in_ |
| Part 3: automation | _fill in_ |
| Packaging | _fill in_ |
