"""Identify a newly observed completed-week CTA event across NAV refreshes."""

from __future__ import annotations

from onecool_os.market.fund_cta import FundCTAResult


def new_weekly_cross_event(
    previous: FundCTAResult | None, current: FundCTAResult
) -> tuple[str, str] | None:
    """Return (cross direction, week-end date) once per distinct weekly cross.

    The engine can keep the most recently completed Friday as its latest week
    through the following Thursday.  Its NEW phase is a property of that week,
    not a fresh instruction to deploy or redeem on every NAV refresh.
    """

    cross = current.weekly_cross
    if cross is None or cross.cross_status not in {"GOLDEN", "DEATH"}:
        return None
    if cross.last_cross_date is None:
        return None
    key = (cross.cross_status, cross.last_cross_date)
    if previous is None or previous.weekly_cross is None:
        return None  # Without a comparable prior snapshot, novelty is unknown.
    prior = previous.weekly_cross
    if (prior.last_cross_status, prior.last_cross_date) == key:
        return None
    return key
