"""Known product defects from the Part 2 findings report.

Tests that hit an open bug are marked `xfail(strict=True)`: they stay green while the bug is
open, and turn RED (XPASS strict) the moment it is fixed, so the marker gets removed and the
test becomes a regression guard. Each also gets an Allure issue link.
"""

from __future__ import annotations

import allure
import pytest

BUGS = {
    "F1": "Electrolyte returns 201 CONFIRMED for bookings PG rejected (FROZEN/EXPIRED)",
    "F2": "Idempotency-Key retry creates a duplicate booking",
    "F3": "City Plus priced below City One (PG pricing config)",
    "F4": "spots_available is stale for HIIT Express (API 4, PG 0)",
    "F6": "Purchased membership not reflected in member profile",
    "F7": "Unknown member returns 200 null instead of 404",
}


def known_bug(bug_id: str):
    """Return marks for a test (or pytest.param) blocked by an open finding."""
    reason = f"{bug_id}: {BUGS[bug_id]}"
    return [pytest.mark.xfail(strict=True, reason=reason), allure.issue(bug_id, name=reason)]


def apply(bug_id: str):
    """Decorator form of known_bug()."""
    def deco(fn):
        for mark in reversed(known_bug(bug_id)):
            fn = mark(fn)
        return fn
    return deco
