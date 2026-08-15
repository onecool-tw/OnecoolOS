"""Update the GitHub-cached Onecool Market Dashboard after each US session."""

from __future__ import annotations

import argparse
import json
import os
from datetime import date
from math import isclose
from pathlib import Path

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


CORE_ALPHA_FALLBACK_SYMBOLS = {"SPY", "QQQ", "DIA", "SOXX", "NVDA"}
ADJUSTED_HISTORY_SOURCES = {
    "yahoo_finance_adjusted_fallback",
}
DIVIDEND_ABS_TOLERANCE = 1e-3
INNOVATION_OPTION_CONFIGS = {
    "TSLA": next(item for item in MARKET_SYMBOLS if item.symbol == "TSLA"),
    "SPCX": MarketSymbol("SPCX", "SPCX", "US", "innovation_option"),
}


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


def _corporate_action_mismatches(
    bars: list, authoritative: dict
) -> list[str]:
    if not bars:
        return ["history is empty"]
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
    for day in sorted(yahoo_actions.keys() | alpha_actions.keys()):
        yahoo_dividend, yahoo_split = yahoo_actions.get(day, (0.0, 1.0))
        alpha_dividend, alpha_split = alpha_actions.get(day, (0.0, 1.0))
        if not isclose(
            yahoo_dividend,
            alpha_dividend,
            abs_tol=DIVIDEND_ABS_TOLERANCE,
        ):
            mismatches.append(
                f"{day}: dividend yahoo={yahoo_dividend} "
                f"alpha={alpha_dividend} "
                f"difference={abs(yahoo_dividend - alpha_dividend):.6f}"
            )
        if not isclose(yahoo_split, alpha_split, abs_tol=1e-6):
            mismatches.append(
                f"{day}: split yahoo={yahoo_split} alpha={alpha_split}"
            )
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
            base = [] if needs_raw_rebuild else existing
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
            mismatches = _corporate_action_mismatches(
                history, alpha_actions
            )
            if mismatches:
                raise RuntimeError(
                    f"Corporate Action Mismatch for {config.symbol}: "
                    + "; ".join(mismatches[:10])
                )
            action_validation.append(
                {
                    "symbol": config.symbol,
                    "status": "MATCHED",
                    "source_a": "yahoo_finance_raw",
                    "source_b": "alpha_vantage",
                    "as_of": history[-1].trading_date.isoformat(),
                }
            )

        staged.append((config, history))
        if config.symbol in INNOVATION_OPTION_SYMBOLS:
            innovation_histories[config.symbol] = history
        records.append(
            dashboard_record(config, calculate_cta(config.symbol, history))
        )

    # SPCX has less than 50 completed weeks after its 2026 IPO.  Collect and
    # publish its maturity state without weakening the shared CTA engine.
    spcx = INNOVATION_OPTION_CONFIGS["SPCX"]
    spcx_existing = read_history(history_dir / "SPCX.csv")
    spcx_incoming = history_bootstrapper.fetch_raw_daily(
        spcx.provider_symbol, period="5y" if not spcx_existing else "10d"
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
    args = parser.parse_args()
    update(
        Path("."),
        os.environ.get("ALPHA_VANTAGE_API_KEY", ""),
        refresh_action_symbols=set(
            DASHBOARD_ACTION_REFRESH_GROUPS.get(
                args.refresh_actions_group, ()
            )
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
    INNOVATION_OPTION_POLICY,
    INNOVATION_OPTION_SYMBOLS,
