"""Provider-bar publication guards; no signal or ranking calculations."""
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from onecool_os.market.regional_calendar import (
    is_regional_session,
    latest_regional_session,
)
from onecool_os.market.taiwan_calendar import is_twse_session, latest_twse_session


ASIA_READY = {
    "TW": ("Asia/Taipei", time(14, 0)),
    "JP": ("Asia/Tokyo", time(15, 45)),
    "KR": ("Asia/Seoul", time(15, 45)),
}


def completed_daily_bars(bars, market, reference_time=None):
    if market not in ASIA_READY:
        return bars
    now = reference_time or datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("reference_time must be timezone-aware")
    zone, ready = ASIA_READY[market]
    local = now.astimezone(ZoneInfo(zone))
    session_today = (
        is_twse_session(local.date())
        if market == "TW"
        else is_regional_session(market, local.date())
    )
    return [bar for bar in bars if bar.trading_date < local.date() or (
        bar.trading_date == local.date() and session_today
        and local.time() >= ready
    )]


def latest_completed_market_session(market, reference_time=None):
    """Return the latest local cash session whose daily bar may be final."""

    if market not in ASIA_READY:
        raise ValueError(f"Unsupported Asia market: {market}")
    now = reference_time or datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("reference_time must be timezone-aware")
    zone, ready = ASIA_READY[market]
    local = now.astimezone(ZoneInfo(zone))
    candidate = local.date()
    is_session = (
        is_twse_session(candidate)
        if market == "TW"
        else is_regional_session(market, candidate)
    )
    if is_session and local.time() < ready:
        from datetime import timedelta
        candidate -= timedelta(days=1)
    return (
        latest_twse_session(candidate)
        if market == "TW"
        else latest_regional_session(market, candidate)
    )
