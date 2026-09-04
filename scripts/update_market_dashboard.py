"""Update the GitHub-cached Onecool Market Dashboard after each US session."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, date, datetime, time
from math import isclose
from pathlib import Path
from zoneinfo import ZoneInfo

from onecool_os.market.dashboard import (
    DASHBOARD_ACTION_REFRESH_GROUPS,
    INNOVATION_OPTION_POLICY,
    INNOVATION_OPTION_SYMBOLS,
    MARKET_SYMBOLS,
    US_PORTFOLIO_CTA_SYMBOLS,
    MarketSymbol,
    build_dashboard_payload,
    dashboard_record,
)
from onecool_os.market.etf_cta import (
    AlphaVantageClient,
    apply_corporate_actions,
    calculate_cta,
    has_new_price_anomaly,
    merge_and_adjust,
    read_history,
    write_history,
)
from onecool_os.market.history_bootstrap import YahooHistoryBootstrapper
from onecool_os.market.us_breakout_scan import (
    build_breakout_scan_payload,
    fetch_yahoo_breakout_inputs,
)
from onecool_os.market.us_portfolio_scores import build_portfolio_score_payload
from onecool_os.market.us_stock_quality import apply_us_super_growth_quality_gate


CORE_ALPHA_FALLBACK_SYMBOLS = {"SPY", "QQQ", "DIA", "SOXX", "NVDA"}
ADJUSTED_HISTORY_SOURCES = {
    "yahoo_finance_adjusted_fallback",
}
DIVIDEND_ABS_TOLERANCE = 1e-3
MINOR_DIVIDEND_ABS_TOLERANCE = 5e-3
MINOR_DIVIDEND_REL_TOLERANCE = 1e-2
INNOVATION_OPTION_CONFIGS = {
    "TSLA": next(item for item in MARKET_SYMBOLS if item.symbol == "TSLA"),
    "SPCX": MarketSymbol("SPCX", "SPCX", "US", "innovation_option"),
}
US_MARKET_TIME_ZONE = ZoneInfo("America/New_York")
US_DAILY_BAR_READY_TIME = time(16, 15)


def _incomplete_us_session_date(
    reference_time: datetime | None = None,
) -> date | None:
    """Return the New York date whose regular session is not safely complete."""

    current = reference_time or datetime.now(UTC)
    if current.tzinfo is None:
        raise ValueError("reference_time must be timezone-aware")
    new_york = current.astimezone(US_MARKET_TIME_ZONE)
    if new_york.weekday() >= 5 or new_york.time() >= US_DAILY_BAR_READY_TIME:
        return None
    return new_york.date()


def _drop_incomplete_us_session(
    config: MarketSymbol,
    bars: list,
    incomplete_session: date | None,
) -> list:
    """Discard a provider's provisional current-session daily bar."""

    is_us_session_symbol = config.market == "US" or config.symbol == "VIX"
    if (
        incomplete_session is None
        or not is_us_session_symbol
        or not bars
        or bars[-1].trading_date != incomplete_session
    ):
        return bars
    return bars[:-1]


def _innovation_option_state(config, history: list) -> dict:
    """Return a daily display row without inventing immature CTA values."""

    weekly_observations = len({
        (bar.trading_date.isocalendar().year, bar.trading_date.isocalendar().week)
        for bar in history
    })
    base = {
        "symbol": config.symbol,
        "as_of": history[-1].trading_date.isoformat(),
        "current_price": round(float(history[-1].adjusted_close), 6),
        "daily_observations": len(history),
        "weekly_observations": weekly_observations,
        "classification": INNOVATION_OPTION_POLICY["classification"],
        "holding_rule": INNOVATION_OPTION_POLICY["holding_rule"],
        "exit_rule": INNOVATION_OPTION_POLICY["exit_rule"],
    }
    if len(history) < 200 or weekly_observations < 50:
        return {
            **base,
            "data_status": "ACCUMULATING",
            "weekly_entry_status": "UNKNOWN",
            "daily_risk_status": "UNKNOWN",
            "display_action": "資料累積中；不得建立CTA訊號",
            "required_daily_observations": 200,
            "required_weekly_observations": 50,
        }

    result = calculate_cta(config.symbol, history)
    weekly = result.weekly_cross
    daily = result.daily_cross
    if weekly.cross_status == "GOLDEN":
        entry_status = "NEW_ENTRY_ELIGIBLE"
        action = "週線剛翻多：可建立小比例長期部位"
    elif weekly.alignment == "GOLDEN":
        entry_status = "ENTRY_ELIGIBLE"
        action = "週線多頭：既有小部位長期持有"
    else:
        entry_status = "NO_NEW_ENTRY"
        action = "週線空頭：停止新增；既有小部位不自動賣出，檢核投資邏輯"
    daily_status = (
        "BULLISH" if daily.alignment == "GOLDEN" else
        "BEARISH" if daily.alignment == "DEATH" else "NEUTRAL"
    )
    return {
        **base,
        "data_status": "READY",
        "weekly_entry_status": entry_status,
        "daily_risk_status": daily_status,
        "display_action": action,
        "weekly_ma30": result.weekly_30ma,
        "weekly_ma50": result.weekly_50ma,
        "daily_sma50": result.daily_50ma,
        "daily_sma200": result.daily_200ma,
        "weekly_cross": result.weekly_cross.__dict__,
        "daily_cross": result.daily_cross.__dict__,
    }


def _action_map(bars: list) -> dict:
    return {
        bar.trading_date: (bar.dividend, bar.split_factor)
        for bar in bars
        if bar.dividend or bar.split_factor != 1.0
    }


def _dividend_on_latest_share_basis(
    trading_date: date, dividend: float, actions: dict
) -> float:
    """Convert a raw historical dividend to the latest post-split share basis.

    Yahoo reports historical dividends on the current share basis, while Alpha
    Vantage reports the cash amount that was paid at the time.  Reconcile the
    two only after applying every later split reported in the same authoritative
    corporate-action history.
    """

    cumulative_split = 1.0
    for action_date, (_, split_factor) in actions.items():
        if action_date > trading_date and split_factor != 1.0:
            cumulative_split *= split_factor
    return dividend / cumulative_split


def _corporate_action_discrepancies(
    bars: list, authoritative: dict
) -> tuple[list[str], list[str]]:
    if not bars:
        return ["history is empty"], []
    yahoo_actions = _action_map(bars)
    first_date = bars[0].trading_date
    last_date = bars[-1].trading_date
    alpha_actions = {
        day: values
        for day, values in authoritative.items()
        if first_date <= day <= last_date
        and (values[0] or values[1] != 1.0)
    }
    mismatches = []
    minor_differences = []
    for day in sorted(yahoo_actions.keys() | alpha_actions.keys()):
        yahoo_dividend, yahoo_split = yahoo_actions.get(day, (0.0, 1.0))
        alpha_raw_dividend, alpha_split = alpha_actions.get(day, (0.0, 1.0))
        alpha_dividend = _dividend_on_latest_share_basis(
            day, alpha_raw_dividend, alpha_actions
        )
        if not isclose(
            yahoo_dividend,
            alpha_dividend,
            abs_tol=DIVIDEND_ABS_TOLERANCE,
        ):
            difference = abs(yahoo_dividend - alpha_dividend)
            relative_difference = difference / max(
                abs(yahoo_dividend), abs(alpha_dividend), 1e-12
            )
            detail = (
                f"{day}: dividend yahoo={yahoo_dividend:.12g} "
                f"alpha={alpha_dividend:.12g} "
                f"difference={difference:.6f}"
            )
            if (
                difference <= MINOR_DIVIDEND_ABS_TOLERANCE
                and relative_difference <= MINOR_DIVIDEND_REL_TOLERANCE
            ):
                minor_differences.append(detail)
            else:
                mismatches.append(detail)
        if not isclose(yahoo_split, alpha_split, abs_tol=1e-6):
            mismatches.append(
                f"{day}: split yahoo={yahoo_split} alpha={alpha_split}"
            )
    return mismatches, minor_differences


def _corporate_action_mismatches(
    bars: list, authoritative: dict
) -> list[str]:
    """Return only material differences that must block publication."""

    mismatches, _ = _corporate_action_discrepancies(bars, authoritative)
    return mismatches


def _alpha_price_fallback(
    config,
    existing: list,
    client: AlphaVantageClient | None,
    *,
    refresh_actions: bool,
) -> list:
    if config.symbol not in CORE_ALPHA_FALLBACK_SYMBOLS or client is None:
        raise RuntimeError(
            f"Yahoo Finance failed and no Alpha Vantage fallback is "
            f"available for {config.symbol}"
        )
    if not existing or any(
        bar.source in ADJUSTED_HISTORY_SOURCES for bar in existing
    ):
        raise RuntimeError(
            f"{config.symbol} needs a complete raw-history rebuild before "
            "Alpha Vantage compact fallback can be used"
        )
    daily = client.fetch_daily(config.provider_symbol, outputsize="compact")
    combined = merge_and_adjust(existing, daily)
    combined = apply_corporate_actions(combined, _action_map(existing))
    if refresh_actions or has_new_price_anomaly(existing, daily):
        combined = apply_corporate_actions(
            combined,
            client.fetch_actions(config.provider_symbol),
            authoritative=True,
        )
    return merge_and_adjust([], combined)


def update(
    root: Path,
    api_key: str,
    *,
    bootstrapper: YahooHistoryBootstrapper | None = None,
    refresh_action_symbols: set[str] | None = None,
    refresh_us_scan: bool = False,
    breakout_input_loader=None,
    reference_time: datetime | None = None,
) -> dict:
    """Use raw Yahoo prices, AV action validation, and core AV fallback."""

    data_dir = root / "data" / "market" / "dashboard"
    history_dir = data_dir / "history"
    client = AlphaVantageClient(api_key) if api_key else None
    history_bootstrapper = bootstrapper or YahooHistoryBootstrapper()
    staged = []
    records = []
    providers: dict[str, str] = {}
    innovation_histories: dict[str, list] = {}
    incomplete_us_session = _incomplete_us_session_date(reference_time)

    action_validation = []
    # Fetch and calculate every symbol before replacing any successful cache.
    for config in MARKET_SYMBOLS:
        existing = read_history(history_dir / f"{config.symbol}.csv")
        needs_raw_rebuild = (
            not existing
            or any(
                bar.source in ADJUSTED_HISTORY_SOURCES
                for bar in existing
            )
        )
        try:
            incoming = history_bootstrapper.fetch_raw_daily(
                config.provider_symbol,
                period="5y" if needs_raw_rebuild else "10d",
            )
            incoming = _drop_incomplete_us_session(
                config, incoming, incomplete_us_session
            )
            base = [] if needs_raw_rebuild else _drop_incomplete_us_session(
                config, existing, incomplete_us_session
            )
            anomaly = has_new_price_anomaly(base, incoming)
            history = merge_and_adjust(base, incoming)
            providers[config.symbol] = "yahoo_finance_raw"
        except Exception:
            history = _alpha_price_fallback(
                config,
                existing,
                client,
                refresh_actions=(
                    config.symbol in (refresh_action_symbols or set())
                ),
            )
            providers[config.symbol] = "alpha_vantage_fallback"
            anomaly = False
            history = _drop_incomplete_us_session(
                config, history, incomplete_us_session
            )

        should_validate_actions = (
            config.symbol in (refresh_action_symbols or set())
            or anomaly
        )
        if should_validate_actions:
            if client is None:
                raise RuntimeError(
                    "ALPHA_VANTAGE_API_KEY is required for scheduled "
                    "corporate-action validation"
                )
            alpha_actions = client.fetch_actions(config.provider_symbol)
            mismatches, minor_differences = _corporate_action_discrepancies(
                history, alpha_actions
            )
            if mismatches:
                raise RuntimeError(
                    f"Corporate Action Mismatch for {config.symbol}: "
                    + "; ".join(mismatches[:10])
                )
            validation = {
                "symbol": config.symbol,
                "status": (
                    "MATCHED_WITH_MINOR_PROVIDER_DIFFERENCE"
                    if minor_differences else "MATCHED"
                ),
                "source_a": "yahoo_finance_raw",
                "source_b": "alpha_vantage",
                "as_of": history[-1].trading_date.isoformat(),
            }
            if minor_differences:
                validation["minor_differences"] = minor_differences
                validation["minor_difference_policy"] = (
                    "non_blocking_only_when_absolute_difference_lte_0.005_"
                    "and_relative_difference_lte_1pct"
                )
            action_validation.append(validation)

        staged.append((config, history))
        if config.symbol in INNOVATION_OPTION_SYMBOLS:
            innovation_histories[config.symbol] = history
        result = calculate_cta(
            config.symbol,
            history,
            required_weekly_close_weekday=(
                6 if config.symbol == "BTC" else None
            ),
        )
        records.append(dashboard_record(config, result))

    # SPCX has less than 50 completed weeks after its 2026 IPO.  Collect and
    # publish its maturity state without weakening the shared CTA engine.
    spcx = INNOVATION_OPTION_CONFIGS["SPCX"]
    spcx_existing = read_history(history_dir / "SPCX.csv")
    spcx_incoming = history_bootstrapper.fetch_raw_daily(
        spcx.provider_symbol, period="5y" if not spcx_existing else "10d"
    )
    spcx_incoming = _drop_incomplete_us_session(
        spcx, spcx_incoming, incomplete_us_session
    )
    spcx_existing = _drop_incomplete_us_session(
        spcx, spcx_existing, incomplete_us_session
    )
    spcx_history = merge_and_adjust(spcx_existing, spcx_incoming)
    providers["SPCX"] = "yahoo_finance_raw"
    staged.append((spcx, spcx_history))
    innovation_histories["SPCX"] = spcx_history

    innovation_watch = [
        _innovation_option_state(
            INNOVATION_OPTION_CONFIGS[symbol], innovation_histories[symbol]
        )
        for symbol in INNOVATION_OPTION_SYMBOLS
    ]
    payload = build_dashboard_payload(
        records, innovation_option_watch=innovation_watch
    )
    payload["us_session_cutoff_policy"] = (
        "exclude_current_New_York_daily_bar_until_16:15_America/New_York"
    )
    payload["excluded_incomplete_us_session"] = (
        incomplete_us_session.isoformat() if incomplete_us_session else None
    )
    histories_by_symbol = {
        config.symbol: history for config, history in staged
    }
    portfolio_scores = build_portfolio_score_payload(
        histories_by_symbol,
        expected_as_of=payload["expected_as_of"],
    )
    payload["us_portfolio_dual_system_scores"] = portfolio_scores
    intelligence_dir = root / "data" / "market" / "us_stock_intelligence"
    scan_path = intelligence_dir / "breakout_scan_latest.json"
    breakout_scan = None
    if refresh_us_scan:
        try:
            if breakout_input_loader is None:
                yfinance = __import__("yfinance")
                scan_histories, scan_fundamentals = fetch_yahoo_breakout_inputs(
                    yfinance,
                    expected_as_of=payload["expected_as_of"],
                    spy_history=histories_by_symbol["SPY"],
                )
            else:
                scan_histories, scan_fundamentals = breakout_input_loader(
                    payload["expected_as_of"]
                )
            breakout_scan = build_breakout_scan_payload(
                scan_histories,
                scan_fundamentals,
                spy_history=histories_by_symbol["SPY"],
                expected_as_of=payload["expected_as_of"],
            )
        except Exception as exc:  # noqa: BLE001 - retain last valid artifact.
            if scan_path.exists():
                breakout_scan = json.loads(scan_path.read_text(encoding="utf-8"))
                breakout_scan["publication_status"] = "LAST_VALID"
                breakout_scan["attempted_as_of"] = payload["expected_as_of"]
                breakout_scan["last_attempt_error"] = str(exc)[:500]
            else:
                breakout_scan = {
                    "schema_version": "1.0",
                    "data_status": "NOT_PUBLISHED",
                    "publication_status": "NO_VALID_SCAN",
                    "attempted_as_of": payload["expected_as_of"],
                    "last_attempt_error": str(exc)[:500],
                    "top5": [],
                }
    elif scan_path.exists():
        breakout_scan = json.loads(scan_path.read_text(encoding="utf-8"))
    if breakout_scan is not None:
        evidence_path = intelligence_dir / "super_growth_evidence_latest.json"
        evidence = (
            json.loads(evidence_path.read_text(encoding="utf-8"))
            if evidence_path.exists()
            else None
        )
        breakout_scan = apply_us_super_growth_quality_gate(
            breakout_scan, evidence
        )
        breakout_scan.setdefault("publication_status", "CURRENT")
        payload["daily_top5_scan"] = breakout_scan
    payload["provider_by_symbol"] = providers
    payload["corporate_action_validation"] = action_validation
    payload["provider_fallback_policy"] = (
        "yahoo_finance_raw_primary; "
        "alpha_vantage_core_price_fallback; "
        "last_successful_cache_on_failure"
    )
    for config, history in staged:
        write_history(history_dir / f"{config.symbol}.csv", history)
    data_dir.mkdir(parents=True, exist_ok=True)
    # JSON NaN is not valid JSON. Refuse the whole staged refresh and leave the
    # last successful cache untouched when a provider returns a non-finite bar.
    serialized = json.dumps(
        payload, indent=2, ensure_ascii=False, allow_nan=False
    ) + "\n"
    (data_dir / "dashboard_latest.json").write_text(serialized, encoding="utf-8")
    scores_dir = intelligence_dir
    scores_dir.mkdir(parents=True, exist_ok=True)
    scores_serialized = json.dumps(
        portfolio_scores, indent=2, ensure_ascii=False, allow_nan=False
    ) + "\n"
    (scores_dir / "portfolio_scores_latest.json").write_text(
        scores_serialized, encoding="utf-8"
    )
    if (
        breakout_scan is not None
        and breakout_scan.get("publication_status") == "CURRENT"
    ):
        scan_serialized = json.dumps(
            breakout_scan, indent=2, ensure_ascii=False, allow_nan=False
        ) + "\n"
        scan_path.write_text(scan_serialized, encoding="utf-8")
    snapshot_date = max(date.fromisoformat(item.as_of) for item in records)
    snapshots = data_dir / "snapshots"
    snapshots.mkdir(parents=True, exist_ok=True)
    (snapshots / f"{snapshot_date.isoformat()}.json").write_text(
        serialized, encoding="utf-8"
    )
    print(serialized, end="")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--refresh-actions-group",
        choices=tuple(DASHBOARD_ACTION_REFRESH_GROUPS),
        help="Refresh one API-safe dashboard dividend/split group.",
    )
    parser.add_argument(
        "--refresh-us-scan",
        action="store_true",
        help="Refresh the same-cutoff US breakout scan and Daily Top 5.",
    )
    args = parser.parse_args()
    update(
        Path("."),
        os.environ.get("ALPHA_VANTAGE_API_KEY", ""),
        refresh_action_symbols=set(
            DASHBOARD_ACTION_REFRESH_GROUPS.get(
                args.refresh_actions_group, ()
            )
        ),
        refresh_us_scan=args.refresh_us_scan,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
