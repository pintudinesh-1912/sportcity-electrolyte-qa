"""Generate the Electrolyte Postman v2.1 collection + environment.

The collection JSON is the Part 1 deliverable. It is generated from this script so
that schemas, expected Perfect Gym truth and shared assertions are defined once and
stay consistent across requests. Re-run after editing:

    python3 part1-test-design/build_collection.py
"""

from __future__ import annotations

import json
from pathlib import Path

OUT_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# Expected "truth" — taken from the Perfect Gym screens supplied in the kit
# (PG is the source of truth). In a real environment these would be read from
# PG's API or a seeded fixture, not hard-coded.
# ---------------------------------------------------------------------------
PG_CLASSES = {
    # id: (name, start_time in Europe/Amsterdam with correct DST offset, capacity, free spots)
    "C-2001": ("Spinning", "2027-06-21T18:00:00+02:00", 20, 15),
    "C-2002": ("Yoga", "2027-06-22T09:00:00+02:00", 15, 0),
    "C-2003": ("BodyPump", "2027-06-23T19:30:00+02:00", 25, 15),
    "C-2004": ("HIIT Express", "2027-06-24T07:00:00+02:00", 20, 0),
    "C-2005": ("Pilates", "2027-11-15T18:00:00+01:00", 12, 9),  # winter time -> +01:00
}
PG_MEMBERS = {
    "M-1001": ("Anna de Vries", "anna@example.com", {"plan": "City Plus", "status": "ACTIVE"}),
    "M-1002": ("Tom Bakker", "tom@example.com", {"plan": "City One", "status": "FROZEN"}),
    "M-1003": ("Lisa Jansen", "lisa@example.com", {"plan": "City One", "status": "EXPIRED"}),
    "M-1004": ("Sara Visser", "sara@example.com", None),
}

# ---------------------------------------------------------------------------
# JSON schemas (derived from openapi.yaml, tightened with `required`)
# ---------------------------------------------------------------------------
ERROR = {
    "type": "object",
    "required": ["error"],
    "properties": {
        "error": {
            "type": "object",
            "required": ["code", "message"],
            "properties": {"code": {"type": "string", "minLength": 1}, "message": {"type": "string"}},
        }
    },
}
MEMBER = {
    "type": "object",
    "required": ["id", "name", "email", "membership"],
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "email": {"type": "string"},
        "membership": {
            "type": ["object", "null"],
            "required": ["plan", "status"],
            "properties": {
                "plan": {"type": "string"},
                "status": {"enum": ["ACTIVE", "FROZEN", "EXPIRED"]},
            },
        },
    },
}
PLAN = {
    "type": "object",
    "required": ["id", "name", "coverage", "category", "currency", "monthlyPrice"],
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "coverage": {"type": "string"},
        "category": {"enum": ["standard", "discounted"]},
        "currency": {"const": "EUR"},
        "monthlyPrice": {"type": "number", "exclusiveMinimum": 0},
    },
}
PLANS = {"type": "object", "required": ["data"], "properties": {"data": {"type": "array", "items": PLAN}}}
CLASS = {
    "type": "object",
    "required": ["id", "name", "start_time", "capacity", "spots_available"],
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "start_time": {"type": "string"},
        "capacity": {"type": "integer", "minimum": 0},
        "spots_available": {"type": "integer", "minimum": 0},
    },
}
CLASSES = {"type": "object", "required": ["data"], "properties": {"data": {"type": "array", "items": CLASS}}}
MEMBERSHIP = {
    "type": "object",
    "required": ["membershipId", "memberId", "plan", "currency", "monthlyPrice", "status"],
    "properties": {
        "membershipId": {"type": "string"},
        "memberId": {"type": "string"},
        "plan": {"type": "string"},
        "currency": {"const": "EUR"},
        "monthlyPrice": {"type": "number", "exclusiveMinimum": 0},
        "status": {"type": "string"},
    },
}
BOOKING = {
    "type": "object",
    "required": ["bookingId", "memberId", "classId", "className", "status"],
    "properties": {
        "bookingId": {"type": "string"},
        "memberId": {"type": "string"},
        "classId": {"type": "string"},
        "className": {"type": "string"},
        "status": {"const": "CONFIRMED"},
    },
}


# ---------------------------------------------------------------------------
# JS snippet helpers
# ---------------------------------------------------------------------------
def js(obj) -> str:
    return json.dumps(obj, separators=(",", ":"))


def status_is(code: int, label: str = "") -> str:
    return f'pm.test("Status is {code}{label}", () => pm.response.to.have.status({code}));\n'


def schema(name: str, sch: dict) -> str:
    return (
        f"const schema = {js(sch)};\n"
        f'pm.test("Body matches {name} schema", () => pm.response.to.have.jsonSchema(schema));\n'
    )


def error_body(code: str | None = None) -> str:
    s = f"const errSchema = {js(ERROR)};\n"
    s += 'pm.test("Body is an Error object {error:{code,message}}", () => pm.response.to.have.jsonSchema(errSchema));\n'
    if code:
        s += (
            f'pm.test("error.code is \\"{code}\\"", () => '
            f'pm.expect(pm.response.json().error.code).to.eql("{code}"));\n'
        )
    return s


TWO_DP = (
    "const twoDp = (n) => typeof n === 'number' && Number.isFinite(n) && Math.round(n * 100) / 100 === n;\n"
)

# Prepended to every test script. `check()` wraps `pm.test()`: when an assertion fails it
# appends the full request/response to the failure message, so the evidence travels with
# the failed test into every reporter (htmlextra Failures tab, CLI, JUnit). Inlined per
# script rather than shared via globals so it also works when imported into Bruno.
API_DETAILS_PRELUDE = r"""// ---- API details on failure (generated) ----
const __MAX_BODY = 4000;
const __mask = (k, v) => /api-key|authorization/i.test(k) ? "***" : v;
const __pretty = (txt) => {
  if (txt === undefined || txt === null || txt === "") return "(empty)";
  let out = String(txt);
  try { out = JSON.stringify(JSON.parse(out), null, 2); } catch (e) { /* not JSON, keep raw */ }
  return out.length > __MAX_BODY ? out.slice(0, __MAX_BODY) + `\n... (truncated, ${out.length} chars)` : out;
};
const __apiDetails = () => {
  const r = pm.request;
  const url = pm.variables.replaceIn(r.url.toString());
  const query = r.url.query ? r.url.query.all().filter(q => !q.disabled).map(q => `${q.key}=${pm.variables.replaceIn(q.value || "")}`) : [];
  const pathVars = r.url.variables ? r.url.variables.all().map(v => `${v.key}=${v.value}`) : [];
  const reqHeaders = r.headers.all().filter(h => !h.disabled).map(h => `${h.key}: ${__mask(h.key, pm.variables.replaceIn(h.value))}`);
  const reqBody = r.body && r.body.mode === "raw" ? pm.variables.replaceIn(r.body.raw) : "";
  const resHeaders = pm.response.headers.all().map(h => `${h.key}: ${h.value}`);
  return [
    "",
    "──────── API details ────────",
    `Request : ${r.method} ${url}`,
    `Query params : ${query.length ? query.join("&") : "(none)"}`,
    `Path params  : ${pathVars.length ? pathVars.join(", ") : "(none)"}`,
    "Request headers:", ...reqHeaders.map(h => "  " + h),
    "Request body:", __pretty(reqBody),
    `Response : ${pm.response.code} ${pm.response.status} (${pm.response.responseTime} ms, ${pm.response.responseSize || 0} B)`,
    "Response headers:", ...resHeaders.map(h => "  " + h),
    "Response body:", __pretty(pm.response.text()),
    "─────────────────────────────",
  ].join("\n");
};
const check = (name, fn) => pm.test(name, function () {
  try { fn(); }
  catch (err) { err.message = `${err.message}\n${__apiDetails()}`; throw err; }
});
// ---- end prelude ----
"""


def with_prelude(tests: str) -> str:
    return API_DETAILS_PRELUDE + tests.replace("pm.test(", "check(")


HEADERS = [
    {"key": "X-Api-Key", "value": "{{apiKey}}"},
    {"key": "Content-Type", "value": "application/json"},
]


def req(
    name: str,
    method: str,
    path: str,
    tests: str,
    *,
    priority: str,
    risk: str,
    body: str | dict | None = None,
    headers: list[dict] | None = None,
    prerequest: str | None = None,
) -> dict:
    hdrs = HEADERS if headers is None else headers
    url_path = path.lstrip("/").split("/")
    item: dict = {
        "name": f"[{priority}] {name}",
        "request": {
            "method": method,
            "header": hdrs,
            "url": {"raw": "{{baseUrl}}" + path, "host": ["{{baseUrl}}"], "path": url_path},
            "description": f"**Priority:** {priority}\n\n**Risk:** {risk}",
        },
        "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": with_prelude(tests).splitlines()}}],
    }
    if body is not None:
        raw = body if isinstance(body, str) else json.dumps(body, indent=2)
        item["request"]["body"] = {"mode": "raw", "raw": raw, "options": {"raw": {"language": "json"}}}
    if prerequest:
        item["event"].insert(
            0, {"listen": "prerequest", "script": {"type": "text/javascript", "exec": prerequest.splitlines()}}
        )
    return item


def folder(name: str, description: str, items: list[dict]) -> dict:
    return {"name": name, "description": description, "item": items}


NO_AUTH = [{"key": "Content-Type", "value": "application/json"}]
BAD_AUTH = [{"key": "X-Api-Key", "value": "not-a-valid-key"}, {"key": "Content-Type", "value": "application/json"}]

# ---------------------------------------------------------------------------
# 00 — Auth & contract
# ---------------------------------------------------------------------------
auth_items = [
    req("GET /v1/classes without API key -> 401", "GET", "/v1/classes",
        status_is(401) + error_body("unauthorized"), headers=NO_AUTH, priority="P1",
        risk="Unauthenticated access to member-facing data."),
    req("GET /v1/plans with invalid API key -> 401", "GET", "/v1/plans",
        status_is(401) + error_body("unauthorized"), headers=BAD_AUTH, priority="P1",
        risk="A wrong key must be rejected, not just a missing one."),
    req("GET /v1/members/{id} without API key -> 401", "GET", "/v1/members/M-1001",
        status_is(401) + error_body("unauthorized") +
        'pm.test("No personal data leaked", () => pm.expect(pm.response.text()).to.not.include("anna@example.com"));\n',
        headers=NO_AUTH, priority="P0", risk="PII exposure (name, email) without authentication."),
    req("POST /v1/memberships without API key -> 401", "POST", "/v1/memberships",
        status_is(401) + error_body("unauthorized"), headers=NO_AUTH,
        body={"memberId": "M-1004", "planId": "CITY-ONE"}, priority="P1",
        risk="Unauthenticated purchases create financial records."),
    req("POST /v1/bookings without API key -> 401", "POST", "/v1/bookings",
        status_is(401) + error_body("unauthorized"), headers=NO_AUTH,
        body={"memberId": "M-1001", "classId": "C-2001"}, priority="P1",
        risk="Unauthenticated bookings would consume real class capacity."),
    req("Unknown route -> 404 Error body", "GET", "/v1/does-not-exist",
        status_is(404) + error_body(), priority="P2",
        risk="Consistent error contract for clients."),
]

# ---------------------------------------------------------------------------
# 01 — Members (AC1)
# ---------------------------------------------------------------------------
member_items = []
for mid, (name, email, ms) in PG_MEMBERS.items():
    state = ms["status"] if ms else "no membership (prospect)"
    t = status_is(200) + schema("Member", MEMBER)
    t += f"const body = pm.response.json();\n"
    t += f'pm.test("id, name and email match Perfect Gym", () => {{\n'
    t += f'  pm.expect(body.id).to.eql("{mid}");\n  pm.expect(body.name).to.eql("{name}");\n  pm.expect(body.email).to.eql("{email}");\n}});\n'
    if ms:
        t += f'pm.test("Membership status is {ms["status"]} (current PG state)", () => pm.expect(body.membership && body.membership.status).to.eql("{ms["status"]}"));\n'
        t += f'pm.test("Membership plan is {ms["plan"]}", () => pm.expect(body.membership.plan).to.eql("{ms["plan"]}"));\n'
    else:
        t += 'pm.test("membership is null for a prospect", () => pm.expect(body.membership).to.eql(null));\n'
    member_items.append(req(
        f"GET member {mid} -> {state}", "GET", f"/v1/members/{mid}", t, priority="P0",
        risk="Status drives booking eligibility and what the member sees in the app; "
             "a stale or mis-mapped status lets frozen/expired members book or blocks paying members."))

member_items.append(req(
    "GET unknown member M-9999 -> 404 Error body", "GET", "/v1/members/M-9999",
    status_is(404, " (member does not exist)") + error_body(), priority="P0",
    risk="AC1 explicitly requires 404 + Error body. A 200/null forces clients to special-case "
         "and can render an empty profile instead of an error."))

# ---------------------------------------------------------------------------
# 02 — Plans (AC2)
# ---------------------------------------------------------------------------
plans_tests = status_is(200) + schema("Plans list", PLANS) + TWO_DP + """const plans = pm.response.json().data;
const byId = Object.fromEntries(plans.map(p => [p.id, p]));
pm.test("All three plans are offered", () => pm.expect(Object.keys(byId)).to.have.members(["CITY-ONE", "CITY-PLUS", "CITY-STUDENT"]));
pm.test("Every price is EUR with at most 2 decimals", () => plans.forEach(p => {
  pm.expect(p.currency, p.id).to.eql("EUR");
  pm.expect(twoDp(p.monthlyPrice), `${p.id} price ${p.monthlyPrice}`).to.be.true;
}));
pm.test("City One and City Plus are 'standard', City Student is 'discounted'", () => {
  pm.expect(byId["CITY-ONE"].category).to.eql("standard");
  pm.expect(byId["CITY-PLUS"].category).to.eql("standard");
  pm.expect(byId["CITY-STUDENT"].category).to.eql("discounted");
});
pm.test("Tier rule: City Plus is priced HIGHER than City One", () =>
  pm.expect(byId["CITY-PLUS"].monthlyPrice, "City Plus price").to.be.above(byId["CITY-ONE"].monthlyPrice));
pm.test("Discounted City Student is cheaper than both standard plans", () => {
  pm.expect(byId["CITY-STUDENT"].monthlyPrice).to.be.below(byId["CITY-ONE"].monthlyPrice);
  pm.expect(byId["CITY-STUDENT"].monthlyPrice).to.be.below(byId["CITY-PLUS"].monthlyPrice);
});
// Remember catalogue prices so the purchase tests can check they agree.
plans.forEach(p => pm.collectionVariables.set(`price_${p.id}`, p.monthlyPrice));
"""
plans_items = [req("GET /v1/plans -> prices, currency and tier rule", "GET", "/v1/plans", plans_tests,
                   priority="P0", risk="Revenue and customer trust: a prospect is quoted these prices; "
                                       "an inverted tier means under-charging every City Plus member.")]

# ---------------------------------------------------------------------------
# 03 — Classes (AC3)
# ---------------------------------------------------------------------------
classes_tests = status_is(200) + schema("Classes list", CLASSES) + f"""const expected = {js({k: {"name": v[0], "start": v[1], "capacity": v[2], "free": v[3]} for k, v in PG_CLASSES.items()})};
const classes = pm.response.json().data;
const byId = Object.fromEntries(classes.map(c => [c.id, c]));
pm.test("All scheduled classes are listed", () => pm.expect(Object.keys(byId)).to.include.members(Object.keys(expected)));
pm.test("start_time is ISO 8601 with an explicit offset", () => classes.forEach(c =>
  pm.expect(c.start_time, c.id).to.match(/^\\d{{4}}-\\d{{2}}-\\d{{2}}T\\d{{2}}:\\d{{2}}:\\d{{2}}(\\.\\d+)?(Z|[+-]\\d{{2}}:\\d{{2}})$/)));
Object.entries(expected).forEach(([id, e]) => {{
  const c = byId[id] || {{}};
  pm.test(`${{id}} ${{e.name}}: start_time is ${{e.start}} (Europe/Amsterdam, DST-aware)`, () => pm.expect(c.start_time).to.eql(e.start));
  pm.test(`${{id}} ${{e.name}}: same instant as the PG schedule`, () => pm.expect(Date.parse(c.start_time)).to.eql(Date.parse(e.start)));
  pm.test(`${{id}} ${{e.name}}: capacity is ${{e.capacity}}`, () => pm.expect(c.capacity).to.eql(e.capacity));
  pm.test(`${{id}} ${{e.name}}: spots_available is ${{e.free}} (true PG remaining capacity)`, () => pm.expect(c.spots_available).to.eql(e.free));
}});
pm.test("0 <= spots_available <= capacity for every class", () => classes.forEach(c => {{
  pm.expect(c.spots_available, c.id).to.be.at.least(0);
  pm.expect(c.spots_available, c.id).to.be.at.most(c.capacity);
}}));
// Baseline spots for the booking tests.
classes.forEach(c => pm.collectionVariables.set(`spots_${{c.id}}`, c.spots_available));
"""
classes_items = [req("GET /v1/classes -> schedule, timezone and availability", "GET", "/v1/classes", classes_tests,
                     priority="P0", risk="Wrong times mean members miss classes; inflated spots cause "
                                         "failed bookings and customer-care load (see T2/T6).")]

# ---------------------------------------------------------------------------
# 04 — Memberships (AC2)
# ---------------------------------------------------------------------------
def purchase_tests(plan_id: str, extra: str = "") -> str:
    return status_is(201) + schema("Membership", MEMBERSHIP) + TWO_DP + f"""const m = pm.response.json();
pm.test("memberId echoes the request", () => pm.expect(m.memberId).to.eql("M-1004"));
pm.test("Price is EUR with at most 2 decimals", () => {{
  pm.expect(m.currency).to.eql("EUR");
  pm.expect(twoDp(m.monthlyPrice), String(m.monthlyPrice)).to.be.true;
}});
pm.test("Price matches the GET /v1/plans catalogue price", () =>
  pm.expect(m.monthlyPrice).to.eql(Number(pm.collectionVariables.get("price_{plan_id}"))));
pm.test("Membership is ACTIVE after purchase", () => pm.expect(m.status).to.eql("ACTIVE"));
pm.collectionVariables.set("purchased_{plan_id}", m.monthlyPrice);
""" + extra


membership_items = [
    req("Purchase City One for prospect M-1004 -> 201", "POST", "/v1/memberships",
        purchase_tests("CITY-ONE"), body={"memberId": "M-1004", "planId": "CITY-ONE"}, priority="P0",
        risk="Core revenue path; the price returned here is what the member is charged."),
    req("Purchase City Plus for M-1004 -> 201, priced above City One", "POST", "/v1/memberships",
        purchase_tests("CITY-PLUS", """pm.test("Tier rule: purchased City Plus price > City One price", () =>
  pm.expect(m.monthlyPrice).to.be.above(Number(pm.collectionVariables.get("purchased_CITY-ONE"))));
"""), body={"memberId": "M-1004", "planId": "CITY-PLUS"}, priority="P0",
        risk="Tier rule enforced at the point of sale, not only in the catalogue."),
    req("Purchase City Student for M-1004 -> 201, discounted", "POST", "/v1/memberships",
        purchase_tests("CITY-STUDENT", """pm.test("Discounted plan is cheaper than both standard plans", () => {
  pm.expect(m.monthlyPrice).to.be.below(Number(pm.collectionVariables.get("price_CITY-ONE")));
  pm.expect(m.monthlyPrice).to.be.below(Number(pm.collectionVariables.get("price_CITY-PLUS")));
});
"""), body={"memberId": "M-1004", "planId": "CITY-STUDENT"}, priority="P1",
        risk="Discount category must stay below standard pricing."),
    req("Member profile reflects the new membership", "GET", "/v1/members/M-1004",
        status_is(200) + """const body = pm.response.json();
pm.test("membership is no longer null after a successful purchase", () => pm.expect(body.membership).to.not.eql(null));
pm.test("membership status is ACTIVE", () => pm.expect(body.membership && body.membership.status).to.eql("ACTIVE"));
""", priority="P1",
        risk="End-to-end flow (sign up -> activate -> book): if PG/profile is not updated the new member "
             "cannot book. Note: spec does not define multiple purchases; this checks the profile shows *a* membership."),
    req("Unknown planId -> 400 Error body", "POST", "/v1/memberships",
        status_is(400) + error_body(), body={"memberId": "M-1004", "planId": "CITY-GOLD"}, priority="P1",
        risk="planId is an enum in the contract; anything else must be rejected."),
    req("Missing planId -> 400 Error body", "POST", "/v1/memberships",
        status_is(400) + error_body() +
        'pm.test("Error message does not leak internals (\\"undefined\\")", () => pm.expect(pm.response.json().error.message).to.not.include("undefined"));\n',
        body={"memberId": "M-1004"}, priority="P2", risk="Required field validation and clean error messages."),
    req("Missing memberId -> 400 Error body", "POST", "/v1/memberships",
        status_is(400, " (validation error, not 404)") + error_body(),
        body={"planId": "CITY-ONE"}, priority="P2", risk="Required field validation."),
    req("Unknown member -> 404 Error body", "POST", "/v1/memberships",
        status_is(404) + error_body(), body={"memberId": "M-9999", "planId": "CITY-ONE"}, priority="P1",
        risk="No memberships for members that do not exist in PG."),
    req("Malformed JSON body -> 400 Error body", "POST", "/v1/memberships",
        status_is(400) + error_body(), body='{"memberId": "M-1004", "planId": ', priority="P2",
        risk="Robustness: unparseable input must be a client error, not a misleading 404."),
]

# ---------------------------------------------------------------------------
# 05 — Bookings (AC4)
# ---------------------------------------------------------------------------
def spots_after(class_id: str, delta: int, why: str) -> dict:
    return req(
        f"{class_id} spots_available changed by {delta} ({why})", "GET", "/v1/classes",
        status_is(200) + f"""const c = pm.response.json().data.find(x => x.id === "{class_id}");
const before = Number(pm.collectionVariables.get("spots_{class_id}"));
pm.test("{class_id} spots_available is baseline {'+' if delta >= 0 else ''}{delta} ({why})", () => pm.expect(c.spots_available).to.eql(before + ({delta})));
""", priority="P0", risk="Availability shown to members must match what was really booked in PG.")


def rejected_booking(member: str, state: str) -> dict:
    return req(
        f"{state} member {member} books C-2001 -> 422", "POST", "/v1/bookings",
        status_is(422, f" (PG rejects {state} membership)") + error_body() + """pm.test("No bookingId returned for a rejected booking", () => pm.expect(pm.response.json()).to.not.have.property("bookingId"));
""", body={"memberId": member, "classId": "C-2001"}, priority="P0",
        risk=f"AC4: only ACTIVE members may book. A false 201 tells a {state} member they are booked when PG "
             "holds no booking: they turn up to a class with no reservation (and spots are not reserved).")


booking_items = [
    req("ACTIVE member M-1001 books Spinning C-2001 -> 201 CONFIRMED", "POST", "/v1/bookings",
        status_is(201) + schema("Booking", BOOKING) + """const b = pm.response.json();
pm.test("Booking echoes member and class", () => {
  pm.expect(b.memberId).to.eql("M-1001");
  pm.expect(b.classId).to.eql("C-2001");
  pm.expect(b.className).to.eql("Spinning");
});
pm.collectionVariables.set("booking_C2001", b.bookingId);
""", body={"memberId": "M-1001", "classId": "C-2001"}, priority="P0", risk="Primary happy path of the release."),
    spots_after("C-2001", -1, "one confirmed booking"),
    rejected_booking("M-1002", "FROZEN"),
    rejected_booking("M-1003", "EXPIRED"),
    spots_after("C-2001", -1, "rejected bookings must not consume spots"),
    req("Book full class Yoga C-2002 -> 409 class_full", "POST", "/v1/bookings",
        status_is(409) + error_body("class_full"), body={"memberId": "M-1001", "classId": "C-2002"},
        priority="P0", risk="Overbooking a full class."),
    req("Book HIIT Express C-2004 (full in PG) -> 409 class_full", "POST", "/v1/bookings",
        status_is(409) + error_body("class_full"), body={"memberId": "M-1001", "classId": "C-2004"},
        priority="P1", risk="T2: PG capacity is 20/20; booking must be refused consistently with the class list."),
    req("Unknown member -> 404 Error body", "POST", "/v1/bookings",
        status_is(404) + error_body(), body={"memberId": "M-9999", "classId": "C-2003"}, priority="P1",
        risk="No bookings for non-existent members."),
    req("Unknown class -> 404 Error body", "POST", "/v1/bookings",
        status_is(404) + error_body(), body={"memberId": "M-1001", "classId": "C-9999"}, priority="P1",
        risk="No bookings for non-existent classes."),
    req("Missing classId -> 400 Error body", "POST", "/v1/bookings",
        status_is(400, " (validation error, not 404)") + error_body(), body={"memberId": "M-1001"},
        priority="P2", risk="Required field validation and accurate error semantics."),
]

# ---------------------------------------------------------------------------
# 06 — Idempotency (AC5)
# ---------------------------------------------------------------------------
idem_pre = """// Fresh key per collection run so reruns do not collide.
pm.collectionVariables.set("idemKey", "idem-" + pm.variables.replaceIn("{{$guid}}"));
"""
IDEM_HEADERS = HEADERS + [{"key": "Idempotency-Key", "value": "{{idemKey}}"}]
idem_items = [
    req("First booking with Idempotency-Key: M-1001 -> BodyPump C-2003", "POST", "/v1/bookings",
        status_is(201) + schema("Booking", BOOKING) + """pm.collectionVariables.set("idem_bookingId", pm.response.json().bookingId);
""", body={"memberId": "M-1001", "classId": "C-2003"}, headers=IDEM_HEADERS, prerequest=idem_pre,
        priority="P0", risk="Baseline for the retry tests."),
    req("Retry same request + same Idempotency-Key -> original booking returned", "POST", "/v1/bookings",
        """pm.test("Status is 200 or 201 (replay of the original)", () => pm.expect(pm.response.code).to.be.oneOf([200, 201]));
const b = pm.response.json();
pm.test("Same bookingId as the original request (no duplicate created)", () =>
  pm.expect(b.bookingId).to.eql(pm.collectionVariables.get("idem_bookingId")));
""", body={"memberId": "M-1001", "classId": "C-2003"}, headers=IDEM_HEADERS, priority="P0",
        risk="AC5: flaky mobile networks retry; duplicates double-consume capacity and double-book members."),
    spots_after("C-2003", -1, "one booking despite the retry"),
    req("Same Idempotency-Key with a different body -> rejected, no new booking", "POST", "/v1/bookings",
        """pm.test("Key reuse with a different payload is rejected (409/422)", () => pm.expect(pm.response.code).to.be.oneOf([409, 422]));
pm.test("No new bookingId issued under a reused key", () => {
  const b = pm.response.json();
  if (b.bookingId) pm.expect(b.bookingId).to.eql(pm.collectionVariables.get("idem_bookingId"));
});
""", body={"memberId": "M-1001", "classId": "C-2005"}, headers=IDEM_HEADERS, priority="P2",
        risk="Contract is silent; industry convention (e.g. Stripe, IETF draft) rejects key reuse with a "
             "different payload. Raise as a spec question if it fails."),
    req("Retry without Idempotency-Key (M-1001 re-books C-2001) -> no duplicate", "POST", "/v1/bookings",
        """pm.test("Duplicate booking of the same member+class is not CONFIRMED again", () =>
  pm.expect(pm.response.code, "a second 201 means a duplicate booking").to.not.eql(201));
""", body={"memberId": "M-1001", "classId": "C-2001"}, priority="P1",
        risk="AC5 says retries must not duplicate; the contract only mandates key-based dedupe. "
             "Clients that omit the header still double-book. Product question: should member+class be unique?"),
]

# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------
COLLECTION_DESC = """Electrolyte API test suite for the SportCity QA assessment (Part 1).

**Run order matters.** Folders run top to bottom against a **freshly started** mock
(restart it to reset seeded data): read-only checks first, then purchases, bookings
and idempotency. Later requests read baselines saved by earlier ones
(plan prices, spots per class).

**Priority legend**
- **P0** money, booking eligibility, or data the member sees directly. Release blocker if failing.
- **P1** contract, validation and consistency. Should fix before release.
- **P2** robustness and error-contract polish. Fix when convenient.

**Source of truth.** Expected values for members, schedules and capacity come from
the Perfect Gym screens in the kit (PG is the CRM of record).

Assertions encode the *intended* behaviour from `openapi.yaml` and the acceptance
criteria, so failing tests are findings, not test bugs.

**Evidence on failure.** Every assertion runs through a `check()` wrapper. When one
fails, the full API exchange is appended to its failure message: method + URL, query and
path params, request headers (API key masked), request body, status, timing, response
headers and response body (truncated at 4000 chars). This shows in the Newman CLI, the
htmlextra *Failures* tab and the JUnit XML. Passing requests keep the standard htmlextra
request/response view.

Run with Newman: `./part1-test-design/run-newman.sh`
"""

COMMON_TESTS = """// Runs after every request.
pm.test("[common] Responds within 1000 ms", () => pm.expect(pm.response.responseTime).to.be.below(1000));
pm.test("[common] Content-Type is application/json", () => pm.expect(pm.response.headers.get("Content-Type") || "").to.include("application/json"));
"""

collection = {
    "info": {
        "name": "SportCity Electrolyte API tests",
        "description": COLLECTION_DESC,
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    },
    # Wrapped in a block so its prelude constants cannot clash with request-level scripts.
    "event": [{"listen": "test", "script": {"type": "text/javascript",
                                            "exec": ("{\n" + with_prelude(COMMON_TESTS) + "}").splitlines()}}],
    "variable": [],
    "item": [
        folder("00 Auth and contract", "Authentication and error contract for every endpoint.", auth_items),
        folder("01 Members (AC1)", "Profile details and current PG membership status; 404 for unknown members.", member_items),
        folder("02 Plans (AC2)", "Catalogue prices: EUR, 2 decimals, tier rule.", plans_items),
        folder("03 Classes (AC3)", "Schedule in Europe/Amsterdam (DST-aware) and true PG availability.", classes_items),
        folder("04 Memberships (AC2)", "Purchase flow for prospect M-1004 plus validation.", membership_items),
        folder("05 Bookings (AC4)", "Eligibility (ACTIVE only), capacity and validation.", booking_items),
        folder("06 Idempotency (AC5)", "Retries must not create duplicate bookings.", idem_items),
    ],
}

environment = {
    "name": "Electrolyte local mock",
    "values": [
        {"key": "baseUrl", "value": "http://localhost:3000", "type": "default", "enabled": True},
        {"key": "apiKey", "value": "sportcity-test-key", "type": "secret", "enabled": True},
    ],
}

if __name__ == "__main__":
    (OUT_DIR / "Electrolyte.postman_collection.json").write_text(json.dumps(collection, indent=2) + "\n")
    (OUT_DIR / "local.postman_environment.json").write_text(json.dumps(environment, indent=2) + "\n")
    n = sum(len(f["item"]) for f in collection["item"])
    print(f"Wrote collection with {n} requests in {len(collection['item'])} folders")
