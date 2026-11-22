"""Session setup/teardown and shared fixtures.

Configuration (environment variables):
  BASE_URL      Target API (default http://localhost:3000). Ignored when MOCK_DIR is set.
  API_KEY       X-Api-Key value (default sportcity-test-key).
  HTTP_TIMEOUT  Per-request timeout in seconds (default 5).
  MOCK_DIR      Path to the kit's mock-server/. When set, the suite starts its OWN mock on a
                free port for the session (fresh seeded data) and stops it at teardown.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import time
import uuid
from pathlib import Path

import pytest
import requests

from support.api_client import ApiClient, Snapshot

ROOT = Path(__file__).resolve().parent
PG_TRUTH = json.loads((ROOT / "data" / "pg_truth.json").read_text())


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_until_up(url: str, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            requests.get(url, timeout=1)
            return
        except requests.ConnectionError:
            time.sleep(0.1)
    raise RuntimeError(f"API at {url} did not come up within {timeout}s")


@pytest.fixture(scope="session")
def base_url(request):
    mock_dir = os.getenv("MOCK_DIR")
    if not mock_dir:
        url = os.getenv("BASE_URL", "http://localhost:3000").rstrip("/")
        try:
            _wait_until_up(url, timeout=3)
        except RuntimeError as exc:
            pytest.exit(f"{exc}. Start the API or set MOCK_DIR to let the suite start one.", returncode=3)
        yield url
        return

    port = _free_port()
    log = open(ROOT / ".mock-server.log", "w")
    proc = subprocess.Popen(["node", "server.js"], cwd=mock_dir, env={**os.environ, "PORT": str(port)},
                            stdout=log, stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{port}"
    try:
        _wait_until_up(url)
        yield url
    finally:  # teardown: stop the session's mock; its in-memory state goes with it
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        log.close()


@pytest.fixture(scope="session")
def api(base_url) -> ApiClient:
    return ApiClient(base_url, os.getenv("API_KEY", "sportcity-test-key"),
                     timeout=float(os.getenv("HTTP_TIMEOUT", "5")))


@pytest.fixture(scope="session")
def pg_truth() -> dict:
    return PG_TRUTH


@pytest.fixture(scope="session")
def seeded_classes(api) -> Snapshot:
    """Class list captured once at session start, before any test books anything.

    Lets the availability-vs-PG checks compare against the seed regardless of test order.
    """
    resp = api.list_classes()
    resp.raise_for_status()
    return Snapshot(resp, {c["id"]: c for c in resp.json()["data"]})


@pytest.fixture
def idempotency_key() -> str:
    return f"pytest-{uuid.uuid4()}"


@pytest.fixture(scope="session", autouse=True)
def _allure_metadata(request, base_url, seeded_classes):
    """Write Allure environment + categories so the report shows target and bug triage."""
    alluredir = getattr(request.config.option, "allure_report_dir", None)
    if not alluredir:
        return
    out = Path(alluredir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "environment.properties").write_text(
        f"Base.URL={base_url}\nAPI.Version=2.0.0 (openapi.yaml)\n"
        f"Mock.Mode={'suite-managed (fresh seed)' if os.getenv('MOCK_DIR') else 'external'}\n"
        f"Source.of.truth=Perfect Gym screens (data/pg_truth.json)\n"
    )
    (out / "categories.json").write_text(json.dumps([
        {"name": "Fixed? Remove the known_bug marker", "matchedStatuses": ["failed"], "messageRegex": r".*XPASS.*"},
        {"name": "Known product bugs (open findings)", "matchedStatuses": ["skipped"], "messageRegex": r".*XFAIL.*"},
        {"name": "New product defects", "matchedStatuses": ["failed"]},
        {"name": "Test / environment errors", "matchedStatuses": ["broken"]},
    ], indent=2))
