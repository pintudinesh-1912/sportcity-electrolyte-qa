from datetime import datetime
from zoneinfo import ZoneInfo

import allure
import pytest

from conftest import PG_TRUTH
from support import known_bugs
from support.assertions import assert_schema, assert_status, check

AMSTERDAM = ZoneInfo("Europe/Amsterdam")


def _class_params():
    for class_id, c in PG_TRUTH["classes"].items():
        marks = known_bugs.known_bug("F4") if class_id == "C-2004" else []
        yield pytest.param(class_id, id=f"{class_id} {c['name']}", marks=marks)


@allure.epic("Electrolyte API")
@allure.feature("Class schedule (AC3)")
class TestClassList:
    @allure.severity(allure.severity_level.CRITICAL)
    def test_class_list_matches_schema(self, api):
        resp = api.list_classes()
        assert_status(resp, 200)
        body = assert_schema(resp, "class_list.json")
        check({c["id"] for c in body["data"]} >= set(PG_TRUTH["classes"]), "scheduled classes missing", resp)

    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("{class_id}: start_time is PG local time with the correct Amsterdam offset")
    @pytest.mark.parametrize("class_id", list(PG_TRUTH["classes"]))
    def test_start_time_is_amsterdam_local_with_dst_offset(self, seeded_classes, pg_truth, class_id):
        actual = datetime.fromisoformat(seeded_classes[class_id]["start_time"])
        expected = datetime.fromisoformat(pg_truth["classes"][class_id]["start_time"])
        with allure.step("Same instant as the PG schedule"):
            check(actual == expected, f"{actual.isoformat()} != PG {expected.isoformat()}", seeded_classes.resp)
        with allure.step("Offset is the Europe/Amsterdam offset for that date (CEST +02:00 / CET +01:00)"):
            check(actual.utcoffset() == actual.astimezone(AMSTERDAM).utcoffset(),
                  f"offset {actual.utcoffset()} is not Amsterdam's {actual.astimezone(AMSTERDAM).utcoffset()}",
                  seeded_classes.resp)
        with allure.step("Wall-clock time equals the PG local time"):
            check(actual.strftime("%H:%M") == expected.strftime("%H:%M"), f"{actual:%H:%M} != {expected:%H:%M}", seeded_classes.resp)

    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("{class_id}: spots_available equals true PG remaining capacity")
    @pytest.mark.parametrize("class_id", _class_params())
    def test_spots_available_matches_perfect_gym(self, seeded_classes, pg_truth, class_id):
        actual, expected = seeded_classes[class_id], pg_truth["classes"][class_id]
        check(actual["capacity"] == expected["capacity"], f"capacity {actual['capacity']} != PG {expected['capacity']}", seeded_classes.resp)
        check(actual["spots_available"] == expected["spots_available"],
              f"spots_available {actual['spots_available']} != PG {expected['spots_available']}", seeded_classes.resp)
        check(0 <= actual["spots_available"] <= actual["capacity"], "spots outside [0, capacity]", seeded_classes.resp)
