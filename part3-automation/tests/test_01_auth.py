import allure
import pytest

from support.assertions import assert_error, check

ENDPOINTS = [
    pytest.param("GET", "/v1/classes", None, id="GET classes"),
    pytest.param("GET", "/v1/plans", None, id="GET plans"),
    pytest.param("GET", "/v1/members/M-1001", None, id="GET member"),
    pytest.param("POST", "/v1/memberships", {"memberId": "M-1004", "planId": "CITY-ONE"}, id="POST memberships"),
    pytest.param("POST", "/v1/bookings", {"memberId": "M-1001", "classId": "C-2001"}, id="POST bookings"),
]


@allure.epic("Electrolyte API")
@allure.feature("Authentication")
@allure.severity(allure.severity_level.CRITICAL)
class TestAuthentication:
    @pytest.mark.parametrize("api_key", [None, "not-a-valid-key"], ids=["missing key", "invalid key"])
    @pytest.mark.parametrize("method,path,body", ENDPOINTS)
    def test_rejects_unauthenticated_requests(self, api, method, path, body, api_key):
        resp = api.request(method, path, json_body=body, api_key=api_key)
        assert_error(resp, 401, "unauthorized")
        check("anna@example.com" not in resp.text, "Response leaks member PII without authentication", resp)
