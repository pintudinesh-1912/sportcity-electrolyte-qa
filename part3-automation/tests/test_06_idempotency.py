"""Idempotent booking (AC5)."""

import allure

from support import known_bugs
from support.assertions import assert_schema, assert_status, check


@allure.epic("Electrolyte API")
@allure.feature("Idempotency (AC5)")
class TestIdempotentBooking:
    @allure.severity(allure.severity_level.BLOCKER)
    @known_bugs.apply("F2")
    def test_retry_with_same_key_returns_original_booking(self, api, idempotency_key):
        before = api.spots("C-2003")

        with allure.step("Original request"):
            first = api.book("M-1001", "C-2003", idempotency_key)
            assert_status(first, 201)
            original = assert_schema(first, "booking.json")

        with allure.step("Client retries the identical request with the same Idempotency-Key"):
            retry = api.book("M-1001", "C-2003", idempotency_key)
            assert_status(retry, (200, 201))
            replay = assert_schema(retry, "booking.json")

        check(replay["bookingId"] == original["bookingId"],
              f"Retry created {replay['bookingId']}; expected original {original['bookingId']}", retry)
        with allure.step("Only one spot consumed in total"):
            after = api.spots("C-2003")
            check(after == before - 1, f"spots {before} -> {after}; a retry must not consume a second spot")
