"""Deterministic JPX/KRX cash-market calendars for readiness gates.

The report pipeline must not infer a local-market holiday from a missing price
bar.  These dates are therefore kept locally, just like the TWSE calendar, so
scheduled health checks remain fail-closed when a provider or workflow is late.
"""

from __future__ import annotations

from datetime import date, timedelta


JPX_HOLIDAY_SOURCE = "https://www.jpx.co.jp/english/corporate/about-jpx/calendar/"
KRX_HOLIDAY_SOURCE = (
    "https://global.krx.co.kr/contents/GLB/05/0501/0501110000/"
    "GLB0501110000.jsp"
)

# Weekday cash-market closures for calendar year 2026.  Weekend entries are
# omitted because they are already non-sessions.
_JPX_HOLIDAYS = {
    date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 12),
    date(2026, 2, 11), date(2026, 2, 23), date(2026, 3, 20),
    date(2026, 4, 29), date(2026, 5, 4), date(2026, 5, 5),
    date(2026, 5, 6), date(2026, 7, 20), date(2026, 8, 11),
    date(2026, 9, 21), date(2026, 9, 22), date(2026, 9, 23),
    date(2026, 10, 12), date(2026, 11, 3), date(2026, 11, 23),
    date(2026, 12, 31),
}

_KRX_HOLIDAYS = {
    date(2026, 1, 1),
    date(2026, 2, 16), date(2026, 2, 17), date(2026, 2, 18),
    date(2026, 3, 2), date(2026, 5, 1), date(2026, 5, 5),
    date(2026, 5, 25), date(2026, 6, 3), date(2026, 8, 17),
    date(2026, 9, 24), date(2026, 9, 25), date(2026, 10, 5),
    date(2026, 10, 9), date(2026, 12, 25), date(2026, 12, 31),
}

_HOLIDAYS = {"JP": _JPX_HOLIDAYS, "KR": _KRX_HOLIDAYS}


def is_regional_session(market: str, day: date) -> bool:
    """Return whether *day* is a known scheduled JPX/KRX cash session."""

    if market not in _HOLIDAYS:
        raise ValueError(f"Unsupported regional market: {market}")
    # Outside the currently governed 2026 schedule, preserve the pre-existing
    # weekday behaviour.  The final-delivery freshness gate still detects a
    # missing open-day bar; annual holiday tables must be extended before that
    # year's holiday can be treated as an excused lag.
    return day.weekday() < 5 and day not in _HOLIDAYS[market]


def latest_regional_session(market: str, day: date) -> date:
    """Return *day* when open, otherwise the preceding local session."""

    while not is_regional_session(market, day):
        day -= timedelta(days=1)
    return day
