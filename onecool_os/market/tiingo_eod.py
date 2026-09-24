"""Transient Tiingo EOD gap lookup; never cache or log provider price rows."""

from __future__ import annotations

import json
import re
from datetime import date
from math import isfinite
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from onecool_os.market.etf_cta import DailyBar


class TiingoEODError(RuntimeError):
    """A sanitized data-source error safe to include in scan diagnostics."""


class TiingoEODClient:
    """Read a bounded EOD window with the token in an HTTP header."""

    def __init__(self, token: str, *, request=None):
        if not token:
            raise ValueError("Tiingo token is required")
        self._token = token
        self._request = request or urlopen

    def fetch_window(self, symbol: str, start: date, end: date) -> list[dict]:
        if not re.fullmatch(r"[A-Z0-9.-]+", symbol):
            raise TiingoEODError("INVALID_SYMBOL")
        if start > end:
            raise TiingoEODError("INVALID_DATE_RANGE")
        url = (f"https://api.tiingo.com/tiingo/daily/{symbol}/prices?"
               + urlencode({"startDate": start.isoformat(), "endDate": end.isoformat()}))
        query = Request(url, headers={
            "Authorization": f"Token {self._token}",
            "Accept": "application/json",
        })
        try:
            with self._request(query, timeout=15) as response:
                data = json.load(response)
        except HTTPError as exc:
            raise TiingoEODError(f"HTTP_{exc.code}") from None
        except (URLError, TimeoutError, ValueError, OSError):
            raise TiingoEODError("REQUEST_FAILED") from None
        if not isinstance(data, list) or not all(isinstance(row, dict) for row in data):
            raise TiingoEODError("INVALID_RESPONSE")
        return data


def verified_missing_bar(rows: list[dict], missing: date, before: DailyBar,
                         after: DailyBar) -> tuple[DailyBar | None, str]:
    """Cross-check two Yahoo anchors before using one independent EOD bar.

    The returned bar is transient; callers may publish only derived signals.
    """
    parsed: dict[date, DailyBar] = {}
    actions: dict[date, tuple[float, float]] = {}
    for row in rows:
        try:
            day = date.fromisoformat(str(row["date"])[:10])
            prices = [float(row[key]) for key in (
                "adjOpen", "adjHigh", "adjLow", "adjClose")]
            volume_number = float(row["volume"])
            split = float(row["splitFactor"])
            dividend = float(row["divCash"])
        except (KeyError, TypeError, ValueError, OverflowError):
            return None, "INVALID_ROW"
        if (day in parsed or not all(isfinite(x) for x in (*prices, volume_number, split, dividend))
                or min(prices) <= 0 or volume_number < 0 or not volume_number.is_integer()
                or split <= 0 or dividend < 0
                or prices[1] < max(prices[0], prices[2], prices[3])
                or prices[2] > min(prices[0], prices[1], prices[3])):
            return None, "INVALID_ROW"
        parsed[day] = DailyBar(
            trading_date=day, open=prices[0], high=prices[1],
            low=prices[2], close=prices[3], adjusted_close=prices[3],
            volume=int(volume_number), source="tiingo_eod_adjusted_transient",
        )
        actions[day] = (split, dividend)
    if missing not in parsed:
        return None, "DATE_ABSENT"
    if before.trading_date not in parsed or after.trading_date not in parsed:
        return None, "ANCHOR_UNAVAILABLE"
    if actions[missing] != (1.0, 0.0):
        return None, "CORPORATE_ACTION_REQUIRES_REVIEW"
    for anchor in (before, after):
        candidate = parsed[anchor.trading_date]
        if any(
            abs(getattr(candidate, field) - getattr(anchor, field)) >
            max(0.02, abs(getattr(anchor, field)) * 0.002)
            for field in ("open", "high", "low", "adjusted_close")
        ) or abs(candidate.volume - anchor.volume) > max(1, anchor.volume * 0.01):
            return None, "ANCHOR_MISMATCH"
    return parsed[missing], "ROW_VALID"
