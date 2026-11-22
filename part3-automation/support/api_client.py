"""Thin HTTP client for Electrolyte that records every exchange as an Allure step."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import allure
import requests

SENSITIVE_HEADERS = {"x-api-key", "authorization"}


@dataclass(frozen=True)
class Snapshot:
    """Parsed data keyed by id, plus the response it came from (so failures can show the exchange)."""

    resp: requests.Response
    by_id: dict[str, dict]

    def __getitem__(self, key: str) -> dict:
        return self.by_id[key]

    def __contains__(self, key: str) -> bool:
        return key in self.by_id

    def values(self):
        return self.by_id.values()


def _pretty(text: str | bytes | None) -> str:
    if not text:
        return "(empty)"
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    try:
        return json.dumps(json.loads(text), indent=2, ensure_ascii=False)
    except ValueError:
        return text


def _headers(headers: dict[str, str]) -> str:
    return "\n".join(f"  {k}: {'***' if k.lower() in SENSITIVE_HEADERS else v}" for k, v in headers.items())


def describe(resp: requests.Response) -> str:
    """Human-readable dump of a request/response pair (used for attachments and failure messages)."""
    req = resp.request
    return "\n".join([
        f"Request : {req.method} {req.url}",
        "Request headers:", _headers(dict(req.headers)),
        "Request body:", _pretty(req.body),
        f"Response: {resp.status_code} {resp.reason} ({resp.elapsed.total_seconds() * 1000:.0f} ms)",
        "Response headers:", _headers(dict(resp.headers)),
        "Response body:", _pretty(resp.text),
    ])


class ApiClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        raw_body: str | None = None,
        headers: dict[str, str] | None = None,
        api_key: str | None = "default",
    ) -> requests.Response:
        """Send a request. `api_key=None` omits the auth header; any other string overrides it."""
        hdrs = {"Accept": "application/json", "Content-Type": "application/json"}
        key = self.api_key if api_key == "default" else api_key
        if key is not None:
            hdrs["X-Api-Key"] = key
        hdrs.update(headers or {})

        with allure.step(f"{method} {path}"):
            resp = self.session.request(
                method, f"{self.base_url}{path}", headers=hdrs,
                json=json_body if raw_body is None else None,
                data=raw_body, timeout=self.timeout,
            )
            allure.attach(describe(resp), name=f"{method} {path} -> {resp.status_code}",
                          attachment_type=allure.attachment_type.TEXT)
        return resp

    # Convenience wrappers for the in-scope endpoints -------------------------------------------
    def get_member(self, member_id: str, **kw) -> requests.Response:
        return self.request("GET", f"/v1/members/{member_id}", **kw)

    def list_plans(self, **kw) -> requests.Response:
        return self.request("GET", "/v1/plans", **kw)

    def list_classes(self, **kw) -> requests.Response:
        return self.request("GET", "/v1/classes", **kw)

    def purchase(self, member_id: str, plan_id: str, **kw) -> requests.Response:
        return self.request("POST", "/v1/memberships", json_body={"memberId": member_id, "planId": plan_id}, **kw)

    def book(self, member_id: str, class_id: str, idempotency_key: str | None = None, **kw) -> requests.Response:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        return self.request("POST", "/v1/bookings", json_body={"memberId": member_id, "classId": class_id},
                            headers=headers, **kw)

    def spots(self, class_id: str) -> int:
        resp = self.list_classes()
        resp.raise_for_status()
        return next(c["spots_available"] for c in resp.json()["data"] if c["id"] == class_id)
