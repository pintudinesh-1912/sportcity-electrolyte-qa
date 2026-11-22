"""Booking eligibility (AC4). State-changing tests assert deltas, so they do not depend on order."""

import allure
import pytest

from support import known_bugs
from support.assertions import assert_error, assert_schema, assert_status, check


@allure.epic("Electrolyte API")
@allure.feature("Bookings (AC4)")
class TestBookingEligibility:
    @allure.severity(allure.severity_level.BLOCKER)
    def test_active_member_can_book_and_a_spot_is_consumed(self, api):
        before = api.spots("C-2001")
        resp = api.book("M-1001", "C-2001")
        assert_status(resp, 201)
        body = assert_schema(resp, "booking.json")
        check((body["memberId"], body["classId"], body["className"]) == ("M-1001", "C-2001", "Spinning"),
              "booking does not echo member/class", resp)
        with allure.step("Exactly one spot consumed"):
            check(api.spots("C-2001") == before - 1, f"spots {before} -> {api.spots('C-2001')}, expected -1")

    @allure.severity(allure.severity_level.BLOCKER)
    @allure.title("{state} member {member_id} cannot book (422)")
    @pytest.mark.parametrize("member_id,state", [
        pytest.param("M-1002", "FROZEN", marks=known_bugs.known_bug("F1"), id="FROZEN"),
        pytest.param("M-1003", "EXPIRED", marks=known_bugs.known_bug("F1"), id="EXPIRED"),
    ])
    def test_inactive_member_booking_is_rejected(self, api, member_id, state):
        resp = api.book(member_id, "C-2001")
        body = assert_error(resp, 422)
        check("bookingId" not in body, "A bookingId was issued for a rejected booking", resp)

    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("member_id", ["M-1002", "M-1003"], ids=["FROZEN", "EXPIRED"])
    def test_rejected_booking_does_not_consume_a_spot(self, api, member_id):
        before = api.spots("C-2001")
        api.book(member_id, "C-2001")
        check(api.spots("C-2001") == before, "an inactive member's booking consumed a spot")

    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("class_id", ["C-2002", "C-2004"], ids=["Yoga (full)", "HIIT Express (full in PG)"])
    def test_full_class_returns_409(self, api, class_id):
        assert_error(api.book("M-1001", class_id), 409, "class_full")

    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("payload,status", [
        pytest.param({"memberId": "M-9999", "classId": "C-2003"}, 404, id="unknown member -> 404"),
        pytest.param({"memberId": "M-1001", "classId": "C-9999"}, 404, id="unknown class -> 404"),
    ])
    def test_booking_validation(self, api, payload, status):
        assert_error(api.request("POST", "/v1/bookings", json_body=payload), status)
