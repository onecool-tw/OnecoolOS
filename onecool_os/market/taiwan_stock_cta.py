"""Background CTA cache for the broad Taiwan stock candidate universe.

The fundamental screen owns ranking.  This module only maintains technical
state for every screened symbol so a stock already selected by the screen can
be evaluated immediately.  Provider failures are isolated per symbol and can
never promote, remove, or rerank a candidate.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from onecool_os.market.etf_cta import (
    CTAResult,
    DailyBar,
    ETFCTAError,
    calculate_cta,
    merge_and_adjust,
    read_history,
    write_history,
)


SCHEMA_VERSION = "1.0"
DEFAULT_BATCH_SIZE = 40


def universe_from_screen(screen: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the full screen universe, including incomplete fundamentals."""

    explicit = screen.get("universe")
    if isinstance(explicit, list) and explicit:
        members = [dict(item) for item in explicit if item.get("symbol")]
    else:
        # Backward compatibility for the first v1 screen snapshots.  Rankings
        # plus exclusions reconstruct the 200-symbol liquidity universe.
        members = []
        seen: set[str] = set()
        for item in [*screen.get("rankings", []), *screen.get("exclusions", [])]:
            symbol = str(item.get("symbol", "")).strip()
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            members.append({
                "symbol": symbol,
                "company_name": str(item.get("company_name", "")).strip(),
                "liquidity_rank": item.get("liquidity_rank"),
                "provider_symbol": f"{symbol}.TW",
            })
    return sorted(
        members,
        key=lambda item: (
            item.get("liquidity_rank") is None,
            item.get("liquidity_rank") or 10**9,
            str(item["symbol"]),
        ),
    )


def classify_onecool_state(item: dict[str, Any] | None) -> dict[str, str]:
    """Translate raw crosses into the formal week-first Onecool interpretation."""

    if not item or item.get("update_status") == "UNKNOWN":
        return {
            "state": "UNKNOWN",
            "action": "WATCH_ONLY_CTA_UNKNOWN",
        }
    weekly = str((item.get("weekly_cross") or {}).get("alignment", "UNKNOWN"))
    daily = str((item.get("daily_cross") or {}).get("alignment", "UNKNOWN"))
    if weekly == "GOLDEN" and daily == "GOLDEN":
        return {
            "state": "WEEKLY_BULLISH_DAILY_BULLISH",
            "action": "ELIGIBLE_IF_0050_BULLISH_AND_PRESSURE_GREEN",
        }
    if weekly == "GOLDEN" and daily == "DEATH":
        return {
            "state": "WEEKLY_BULLISH_DAILY_BEARISH",
            "action": "HOLD_EXISTING_PAUSE_RIGHT_SIDE_ADD",
        }
    if weekly == "DEATH" and daily == "GOLDEN":
        return {
            "state": "WEEKLY_BEARISH_DAILY_BULLISH",
            "action": "WATCH_ONLY_REBOUND_NOT_FORMAL_BULLISH",
        }
    if weekly == "DEATH" and daily == "DEATH":
        return {
            "state": "WEEKLY_BEARISH_DAILY_BEARISH",
            "action": "WATCH_ONLY_FULL_WEAKNESS",
        }
    return {
        "state": "UNKNOWN",
        "action": "WATCH_ONLY_CTA_UNKNOWN",
    }


def update_candidate_cta(
    screen_path: Path,
    data_dir: Path,
    *,
    fetcher: Callable[[list[str], str], dict[str, list[DailyBar]]],
    generated_at: datetime | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    """Update all universe symbols while preserving last-known valid results."""

    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    if not screen_path.exists():
        raise ETFCTAError(f"Taiwan stock screen is missing: {screen_path}")
    screen = json.loads(screen_path.read_text(encoding="utf-8"))
    universe = universe_from_screen(screen)
    if not universe:
        raise ETFCTAError("Taiwan stock screen contains no universe symbols.")

    latest_path = data_dir / "cta_latest.json"
    previous = _read_previous(latest_path)
    previous_items = {
        str(item.get("symbol")): item for item in previous.get("results", [])
    }
    provider_to_member = {
        str(item.get("provider_symbol") or f"{item['symbol']}.TW"): item
        for item in universe
    }
    histories = {
        provider: read_history(data_dir / "history" / f"{member['symbol']}.csv")
        for provider, member in provider_to_member.items()
    }
    bootstrap_symbols = [provider for provider, bars in histories.items() if not bars]

    bootstrap, bootstrap_errors = _fetch_in_batches(
        fetcher, bootstrap_symbols, "5y", batch_size
    )
    incremental, incremental_errors = _fetch_in_batches(
        fetcher, list(provider_to_member), "1mo", batch_size
    )

    timestamp = generated_at or datetime.now(UTC)
    results: list[dict[str, Any]] = []
    for provider, member in provider_to_member.items():
        symbol = str(member["symbol"])
        existing = histories[provider] or bootstrap.get(provider, [])
        incoming = incremental.get(provider, [])
        error = incremental_errors.get(provider) or bootstrap_errors.get(provider)
        try:
            if not existing:
                raise ETFCTAError(f"{symbol} has no bootstrap history.")
            if not incoming:
                raise ETFCTAError(error or f"{symbol} has no incremental observations.")
            history = merge_and_adjust(existing, incoming)
            result: CTAResult = calculate_cta(
                symbol, history, exclude_incomplete_latest_week=True
            )
            write_history(data_dir / "history" / f"{symbol}.csv", history)
            item = asdict(result)
            item.update({
                "company_name": member.get("company_name", ""),
                "provider_symbol": provider,
                "liquidity_rank": member.get("liquidity_rank"),
                "update_status": "CURRENT",
                "source_data_as_of": history[-1].trading_date.isoformat(),
                "weekly_data_as_of": _weekly_data_as_of(history),
                "last_attempt_at": timestamp.isoformat(),
                "error": None,
            })
            try:
                screen_date = date.fromisoformat(str(screen.get("expected_as_of")))
            except ValueError:
                screen_date = None
            if (
                screen_date is not None
                and _business_day_lag(history[-1].trading_date, screen_date) > 1
            ):
                item["update_status"] = "STALE_LAST_KNOWN"
                item["error"] = "Price history cutoff trails the screen by more than one business day."
        except Exception as exc:  # noqa: BLE001 - isolate provider/data failures.
            item = _stale_or_unknown(
                previous_items.get(symbol), member, provider, timestamp, str(exc)
            )
        item.update(classify_onecool_state(item))
        results.append(item)

    counts = {
        status: sum(item["update_status"] == status for item in results)
        for status in ("CURRENT", "STALE_LAST_KNOWN", "UNKNOWN")
    }
    cutoffs = sorted({
        str(item["as_of"])
        for item in results
        if item.get("as_of") and item["update_status"] == "CURRENT"
    })
    payload = {
        "schema_version": SCHEMA_VERSION,
        "metric": "Onecool Taiwan Candidate CTA",
        "generated_at": timestamp.isoformat(),
        "screen_as_of": screen.get("expected_as_of"),
        "universe_method": screen.get("universe_method"),
        "source": "Yahoo Finance raw daily history with local corporate-action adjustment",
        "engine": "shared_onecool_cta_engine",
        "ranking_authority": "NONE",
        "policy": "WEEKLY_PRIMARY_DAILY_AUXILIARY; CTA_NEVER_CHANGES_SCREEN_RANK",
        "requested_count": len(universe),
        "coverage": {
            "current": counts["CURRENT"],
            "stale_last_known": counts["STALE_LAST_KNOWN"],
            "unknown": counts["UNKNOWN"],
        },
        "current_data_cutoff_min": cutoffs[0] if cutoffs else None,
        "current_data_cutoff_max": cutoffs[-1] if cutoffs else None,
        "results": results,
    }
    data_dir.mkdir(parents=True, exist_ok=True)
    temporary = latest_path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(latest_path)
    return payload


def _fetch_in_batches(
    fetcher: Callable[[list[str], str], dict[str, list[DailyBar]]],
    symbols: list[str],
    period: str,
    batch_size: int,
) -> tuple[dict[str, list[DailyBar]], dict[str, str]]:
    results: dict[str, list[DailyBar]] = {}
    errors: dict[str, str] = {}
    for start in range(0, len(symbols), batch_size):
        batch = symbols[start:start + batch_size]
        try:
            fetched = fetcher(batch, period)
        except Exception as exc:  # noqa: BLE001 - provider batch boundary.
            errors.update({symbol: str(exc) for symbol in batch})
            continue
        for symbol in batch:
            bars = fetched.get(symbol, [])
            if bars:
                results[symbol] = bars
            else:
                errors[symbol] = f"Yahoo returned no {period} history for {symbol}."
    return results, errors


def _read_previous(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _weekly_data_as_of(history: Iterable[DailyBar]) -> str | None:
    bars = sorted(history, key=lambda bar: bar.trading_date)
    if not bars:
        return None
    latest = bars[-1].trading_date
    if latest.weekday() == 4:
        return latest.isoformat()
    latest_iso = latest.isocalendar()
    completed = [
        bar.trading_date for bar in bars
        if bar.trading_date.isocalendar()[:2] != latest_iso[:2]
    ]
    return completed[-1].isoformat() if completed else None


def _business_day_lag(start: date, end: date) -> int:
    if start >= end:
        return 0
    return sum(
        date.fromordinal(start.toordinal() + offset).weekday() < 5
        for offset in range(1, (end - start).days + 1)
    )


def _stale_or_unknown(
    previous: dict[str, Any] | None,
    member: dict[str, Any],
    provider: str,
    timestamp: datetime,
    error: str,
) -> dict[str, Any]:
    if previous and previous.get("as_of"):
        item = dict(previous)
        item.update({
            "update_status": "STALE_LAST_KNOWN",
            "last_attempt_at": timestamp.isoformat(),
            "error": error,
        })
        return item
    return {
        "symbol": str(member["symbol"]),
        "company_name": member.get("company_name", ""),
        "provider_symbol": provider,
        "liquidity_rank": member.get("liquidity_rank"),
        "as_of": None,
        "cta": "UNKNOWN",
        "reason": "Insufficient or unavailable adjusted-price history.",
        "daily_cross": None,
        "weekly_cross": None,
        "update_status": "UNKNOWN",
        "last_attempt_at": timestamp.isoformat(),
        "error": error,
    }
