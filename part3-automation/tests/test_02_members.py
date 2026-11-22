import allure
import pytest

from conftest import PG_TRUTH
from support import known_bugs
from support.assertions import assert_error, assert_schema, assert_status, check


@allure.epic("Electrolyte API")
@allure.feature("Members (AC1)")
class TestMemberProfile:
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("Member {member_id} profile matches Perfect Gym")
    @pytest.mark.parametrize("member_id", list(PG_TRUTH["members"]))
    def test_profile_matches_perfect_gym(self, api, pg_truth, member_id):
        expected = pg_truth["members"][member_id]
        resp = api.get_member(member_id)

        assert_status(resp, 200)
        body = assert_schema(resp, "member.json")
        with allure.step("Identity fields match PG"):
            actual = {k: body[k] for k in ("id", "name", "email")}
            check(actual == {"id": member_id, "name": expected["name"], "email": expected["email"]},
                  f"Identity mismatch: {actual}", resp)
        with allure.step(f"Membership is {expected['membership']}"):
            check(body["membership"] == expected["membership"],
                  f"Membership {body['membership']} != PG {expected['membership']}", resp)

    @allure.severity(allure.severity_level.NORMAL)
    @known_bugs.apply("F7")
    def test_unknown_member_returns_404_with_error_body(self, api):
        resp = api.get_member("M-9999")
        assert_error(resp, 404)
