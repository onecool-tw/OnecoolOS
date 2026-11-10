"""Historical weekly-completion replay using the frozen production CTA primitives.

Research-only: never imported by production modules. It deliberately does not
translate CTA labels into buy/sell orders.
"""
from datetime import date
from onecool_os.market.etf_cta import (
    ETFCTAError, InsufficientCTAHistory, _detect_cross, cross_priority_cta,
)

def replay_signal(symbol, bars, cutoff):
    """Use only bars observable through cutoff and completed ISO weeks.

    Current Friday counts as completed only if it is already a *closed* bar
    supplied by the caller. Past holiday-shortened weeks become completed
    once a newer ISO week has begun. Caller must validate exchange closures,
    market-session readiness and timezone separately.
    """
    history = sorted((bar for bar in bars if bar.trading_date <= cutoff),
                     key=lambda b: b.trading_date)
    if not history or history[-1].trading_date != cutoff:
        raise ETFCTAError("cutoff must have a verified, closed market bar")
    if len(history) < 200:
        raise InsufficientCTAHistory(symbol, "daily", len(history), 200)
    if any(b.adjusted_close is None for b in history):
        raise ETFCTAError("adjusted prices missing")
    dates = [b.trading_date for b in history]
    daily = [float(b.adjusted_close) for b in history]
    weekly = {}
    for b in history:
        key = (b.trading_date.isocalendar().year, b.trading_date.isocalendar().week)
        weekly[key] = (b.trading_date, float(b.adjusted_close))
    keys = list(weekly)
    latest_key = keys[-1]
    # Today's week is provisional except when Friday's close is verified.
    if cutoff.weekday() != 4:
        weekly.pop(latest_key)
    complete = list(weekly.values())
    if len(complete) < 50:
        raise InsufficientCTAHistory(symbol, "weekly", len(complete), 50)
    d = _detect_cross(dates, daily, 50, 200,
                      confirmed_through=5, active_through=60)
    w = _detect_cross([x[0] for x in complete], [x[1] for x in complete],
                      30, 50, confirmed_through=4, active_through=52)
    action, reason = cross_priority_cta(d, w)
    return {"symbol": symbol, "as_of": cutoff.isoformat(), "cta": action,
            "reason": reason, "daily_cross": d, "weekly_cross": w,
            "last_complete_week": complete[-1][0].isoformat(),
            "sessions": len(history), "complete_weeks": len(complete)}
