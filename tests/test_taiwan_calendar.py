from datetime import date

from onecool_os.market.taiwan_calendar import (
    is_twse_session,
    latest_twse_session,
    twse_session_lag,
)


def test_official_2026_twse_holiday_schedule_is_closed():
    weekday_holidays = {
        date(2026, 1, 1),
        date(2026, 2, 12), date(2026, 2, 13),
        date(2026, 2, 16), date(2026, 2, 17), date(2026, 2, 18),
        date(2026, 2, 19), date(2026, 2, 20), date(2026, 2, 27),
        date(2026, 4, 3), date(2026, 4, 6), date(2026, 5, 1),
        date(2026, 6, 19), date(2026, 9, 25), date(2026, 9, 28),
        date(2026, 10, 9), date(2026, 10, 26), date(2026, 12, 25),
    }

    assert all(not is_twse_session(day) for day in weekday_holidays)


def test_mid_autumn_long_weekend_resolves_to_last_real_session():
    assert latest_twse_session(date(2026, 9, 25)) == date(2026, 9, 24)
    assert latest_twse_session(date(2026, 9, 28)) == date(2026, 9, 24)
    assert twse_session_lag(date(2026, 9, 24), date(2026, 9, 28)) == 0


def test_real_session_after_holiday_is_not_excused():
    assert is_twse_session(date(2026, 9, 29))
    assert latest_twse_session(date(2026, 9, 29)) == date(2026, 9, 29)
    assert twse_session_lag(date(2026, 9, 24), date(2026, 9, 29)) == 1
