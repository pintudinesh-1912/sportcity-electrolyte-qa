"""Assertion helpers. Failures embed the full HTTP exchange so the evidence travels with the failure."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import allure
import pytest
import requests
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from support.api_client import describe

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"


@lru_cache(maxsize=1)
def _registry() -> Registry:
    resources = [(p.name, Resource.from_contents(json.loads(p.read_text()))) for p in SCHEMA_DIR.glob("*.json")]
    return Registry().with_resources(resources)


@lru_cache(maxsize=None)
def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / name).read_text())
    return Draft202012Validator(schema, registry=_registry())


def _fail(message: str, resp: requests.Response | None) -> None:
    details = f"\n\n──── API details ────\n{describe(resp)}" if resp is not None else ""
    pytest.fail(message + details, pytrace=False)


def check(condition: bool, message: str, resp: requests.Response | None = None) -> None:
    """Assert with the API exchange appended to the failure message."""
    if not condition:
        _fail(message, resp)


def assert_status(resp: requests.Response, expected: int | tuple[int, ...]) -> None:
    allowed = expected if isinstance(expected, tuple) else (expected,)
    with allure.step(f"HTTP status is {' or '.join(map(str, allowed))}"):
        check(resp.status_code in allowed, f"Expected HTTP {allowed}, got {resp.status_code}", resp)


def assert_schema(resp: requests.Response, schema_name: str) -> dict:
    with allure.step(f"Body matches {schema_name}"):
        try:
            body = resp.json()
        except ValueError:
            _fail("Response body is not valid JSON", resp)
        errors = sorted(_validator(schema_name).iter_errors(body), key=lambda e: list(e.path))
        check(not errors, f"Schema {schema_name} violations:\n" +
              "\n".join(f"  - at {'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors), resp)
        return body


def assert_error(resp: requests.Response, status: int, code: str | None = None) -> dict:
    assert_status(resp, status)
    body = assert_schema(resp, "error.json")
    if code:
        with allure.step(f"error.code is '{code}'"):
            check(body["error"]["code"] == code, f"Expected error.code '{code}', got '{body['error']['code']}'", resp)
    return body


def has_two_decimals_max(value: float) -> bool:
    return isinstance(value, (int, float)) and round(value, 2) == value
