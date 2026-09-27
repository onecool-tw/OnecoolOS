"""TWSE session calendar used by Taiwan producers and readiness gates.

The calendar is intentionally local and deterministic: scheduled workflows must
not depend on the holiday web page being reachable at run time.  Dates come
from the official TWSE annual market holiday schedule.
"""

from __future__ import annotations

from datetime import date, timedelta


TWSE_HOLIDAY_SOURCE = "https://www.twse.com.tw/holidaySchedule/holidaySchedule?response=html"

# Official ROC year 115 / calendar year 2026 non-trading weekdays.  Weekend
# entries from the source schedule are omitted because they are already closed.
_TWSE_HOLIDAYS = {
    date(2026, 1, 1),
    date(2026, 2, 12),
    date(2026, 2, 13),
    date(2026, 2, 16),
    date(2026, 2, 17),
    date(2026, 2, 18),
    date(2026, 2, 19),
    date(2026, 2, 20),
    date(2026, 2, 27),
    date(2026, 4, 3),
    date(2026, 4, 6),
    date(2026, 5, 1),
    date(2026, 6, 19),
    date(2026, 9, 25),
    date(2026, 9, 28),
    date(2026, 10, 9),
    date(2026, 10, 26),
    date(2026, 12, 25),
}


def is_twse_session(day: date) -> bool:
    """Return whether *day* is a scheduled TWSE trading session."""

    return day.weekday() < 5 and day not in _TWSE_HOLIDAYS


def latest_twse_session(day: date) -> date:
    """Return *day* when open, otherwise the preceding TWSE session."""

    while not is_twse_session(day):
        day -= timedelta(days=1)
    return day


def twse_session_lag(observed: date, expected: date) -> int:
    """Count scheduled TWSE sessions after *observed* through *expected*."""

    if observed >= expected:
        return 0
    cursor = observed + timedelta(days=1)
    lag = 0
    while cursor <= expected:
        if is_twse_session(cursor):
            lag += 1
        cursor += timedelta(days=1)
    return lag
