import allure
import pytest

from conftest import PG_TRUTH
from support.api_client import Snapshot
from support import known_bugs
from support.assertions import assert_error, assert_schema, assert_status, check, has_two_decimals_max


@pytest.fixture(scope="module")
def catalogue(api) -> Snapshot:
    resp = api.list_plans()
    assert_status(resp, 200)
    body = assert_schema(resp, "plan_list.json")
    return Snapshot(resp, {p["id"]: p for p in body["data"]})


@allure.epic("Electrolyte API")
@allure.feature("Plans and pricing (AC2)")
class TestPlanCatalogue:
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("Plan {plan_id}: listed, EUR, max 2 decimals, correct category")
    @pytest.mark.parametrize("plan_id", list(PG_TRUTH["plans"]))
    def test_plan_is_listed_with_valid_price(self, catalogue, pg_truth, plan_id):
        check(plan_id in catalogue, f"{plan_id} missing from catalogue {list(catalogue.by_id)}", catalogue.resp)
        plan = catalogue[plan_id]
        check(plan["currency"] == "EUR", f"currency {plan['currency']}", catalogue.resp)
        check(has_two_decimals_max(plan["monthlyPrice"]), f"price {plan['monthlyPrice']} has >2 decimals", catalogue.resp)
        check(plan["category"] == pg_truth["plans"][plan_id]["category"], f"category {plan['category']}", catalogue.resp)

    @allure.severity(allure.severity_level.BLOCKER)
    @known_bugs.apply("F3")
    def test_tier_rule_city_plus_priced_above_city_one(self, catalogue):
        one, plus = catalogue["CITY-ONE"]["monthlyPrice"], catalogue["CITY-PLUS"]["monthlyPrice"]
        check(plus > one, f"City Plus €{plus} must be priced above City One €{one}", catalogue.resp)

    @allure.severity(allure.severity_level.NORMAL)
    def test_discounted_plan_is_cheapest(self, catalogue):
        student = catalogue["CITY-STUDENT"]["monthlyPrice"]
        standard = [p["monthlyPrice"] for p in catalogue.values() if p["category"] == "standard"]
        check(all(student < s for s in standard), f"City Student €{student} not below standard {standard}", catalogue.resp)


@allure.epic("Electrolyte API")
@allure.feature("Plans and pricing (AC2)")
class TestMembershipPurchase:
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("Purchase {plan_id}: 201, price equals catalogue price")
    @pytest.mark.parametrize("plan_id", list(PG_TRUTH["plans"]))
    def test_purchase_returns_catalogue_price(self, api, catalogue, plan_id):
        resp = api.purchase("M-1004", plan_id)
        assert_status(resp, 201)
        body = assert_schema(resp, "membership.json")
        with allure.step("Price matches catalogue, EUR, max 2 decimals"):
            check(body["monthlyPrice"] == catalogue[plan_id]["monthlyPrice"],
                  f"charged €{body['monthlyPrice']} but catalogue says €{catalogue[plan_id]['monthlyPrice']}", resp)
            check(has_two_decimals_max(body["monthlyPrice"]), "more than 2 decimals", resp)
        check(body["memberId"] == "M-1004" and body["status"] == "ACTIVE", "unexpected memberId/status", resp)

    @allure.severity(allure.severity_level.CRITICAL)
    @known_bugs.apply("F6")
    def test_profile_shows_membership_after_purchase(self, api):
        assert_status(api.purchase("M-1004", "CITY-ONE"), 201)
        resp = api.get_member("M-1004")
        body = assert_schema(resp, "member.json")
        check(body["membership"] is not None and body["membership"]["status"] == "ACTIVE",
              f"Profile membership is {body['membership']} after a successful purchase", resp)

    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("payload,status", [
        pytest.param({"memberId": "M-1004", "planId": "CITY-GOLD"}, 400, id="unknown plan -> 400"),
        pytest.param({"memberId": "M-9999", "planId": "CITY-ONE"}, 404, id="unknown member -> 404"),
    ])
    def test_purchase_validation(self, api, payload, status):
        resp = api.request("POST", "/v1/memberships", json_body=payload)
        assert_error(resp, status)
