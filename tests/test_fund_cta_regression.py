"""Frozen, date-by-date fund CTA and v1.3 Action baseline.

The committed NAV prefix is pinned separately from the expected verdicts.
Adding newer NAVs is safe; changing a historical NAV needs explicit review and
a deliberately versioned replacement for this fixture.
"""

import hashlib
import json
from datetime import date
from pathlib import Path

from onecool_os.market.fund_alpha import FUND_WATCHLIST, read_nav_history
from onecool_os.market.fund_cta import calculate_fund_cta
from onecool_os.market.fund_cta_events import new_weekly_cross_event


ROOT = Path(__file__).resolve().parents[1]
BASELINE = json.loads(
    (ROOT / "tests/fixtures/fund_cta_regression_v1.json").read_text(
        encoding="utf-8"
    )
)


def _history(code):
    return read_nav_history(ROOT / f"data/market/fund_nav/history/{code}.csv")


def _snapshot(result):
    def cross(signal):
        return {
            "alignment": signal.alignment,
            "cross_status": signal.cross_status,
            "phase": signal.phase,
            "last_cross_status": signal.last_cross_status,
            "last_cross_date": signal.last_cross_date,
        }

    return {
        "nav_date": result.fund_nav_as_of,
        "nav_observations": result.nav_observations,
        "cta": result.fund_cta,
        "dca_action": result.dca_action,
        "daily": cross(result.daily_cross),
        "weekly": cross(result.weekly_cross),
        "weekly_30ma": result.weekly_30ma,
        "weekly_50ma": result.weekly_50ma,
    }


def test_seven_funds_have_eight_frozen_periods_and_unchanged_inputs():
    assert BASELINE["schema_version"] == 1
    assert len(BASELINE["periods"]) == 8
    assert set(BASELINE["funds"]) == set(FUND_WATCHLIST)
    for code, entry in BASELINE["funds"].items():
        navs = [
            nav for nav in _history(code)
            if nav.nav_date <= date.fromisoformat(entry["input_cutoff"])
        ]
        assert len(navs) == entry["input_rows"], code
        canonical = "\n".join(
            f"{nav.nav_date.isoformat()},{nav.nav:g},{nav.currency},{nav.source}"
            for nav in navs
        )
        assert hashlib.sha256(canonical.encode()).hexdigest() == entry["input_sha256"], code
        assert set(BASELINE["periods"]) <= set(entry["snapshots"])


def test_date_by_date_cta_action_and_completed_week_cross_match_baseline():
    for code, entry in BASELINE["funds"].items():
        navs = _history(code)
        for day, expected in entry["snapshots"].items():
            as_of = date.fromisoformat(day)
            result = calculate_fund_cta(
                code, (nav for nav in navs if nav.nav_date <= as_of)
            )
            assert _snapshot(result) == expected, (code, day)


def test_invesco_cross_is_once_and_only_after_friday_close():
    code = "B16019"
    navs = _history(code)

    def at(day):
        return calculate_fund_cta(
            code, (nav for nav in navs if nav.nav_date <= date.fromisoformat(day))
        )

    before = at("2026-09-18")
    incomplete = at("2026-09-21")
    friday = at("2026-09-25")
    monday = at("2026-09-28")
    next_friday = at("2026-10-02")

    assert before.weekly_30ma < before.weekly_50ma
    assert incomplete.weekly_cross.cross_status == "NONE"
    assert incomplete.weekly_30ma == before.weekly_30ma
    assert incomplete.weekly_50ma == before.weekly_50ma
    assert friday.weekly_30ma > friday.weekly_50ma
    assert new_weekly_cross_event(incomplete, friday) == (
        "GOLDEN", "2026-09-25"
    )
    # The engine still sees 9/25 as the latest completed week on Monday.
    # A report must not interpret that same event as another capital action.
    assert monday.weekly_cross.phase == "NEW"
    assert new_weekly_cross_event(friday, monday) is None
    assert next_friday.weekly_cross.phase == "CONFIRMED"
    assert new_weekly_cross_event(monday, next_friday) is None
    assert new_weekly_cross_event(None, friday) is None
