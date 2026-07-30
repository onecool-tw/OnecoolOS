"""Update the GitHub-cached Onecool Market Dashboard after each US session."""

from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path

from onecool_os.market.dashboard import (
    DASHBOARD_ACTION_REFRESH_GROUPS,
    MARKET_SYMBOLS,
    US_PORTFOLIO_CTA_SYMBOLS,
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


def update(
    root: Path,
    api_key: str,
    *,
    bootstrapper: YahooHistoryBootstrapper | None = None,
    refresh_action_symbols: set[str] | None = None,
) -> dict:
    """Use AV for core US assets and Yahoo for context and portfolio series."""

    data_dir = root / "data" / "market" / "dashboard"
    history_dir = data_dir / "history"
    client = AlphaVantageClient(api_key) if api_key else None
    history_bootstrapper = bootstrapper or YahooHistoryBootstrapper()
    staged = []
    records = []
    providers: dict[str, str] = {}

    # Fetch and calculate every symbol before replacing any successful cache.
    for config in MARKET_SYMBOLS:
        existing = read_history(history_dir / f"{config.symbol}.csv")
        if (
            config.market in {"TW", "CONTEXT"}
            or config.symbol == "RUSSELL_2000"
            or config.symbol in US_PORTFOLIO_CTA_SYMBOLS
        ):
            # Alpha Vantage rejects Taiwan tickers and the Yahoo-style index
            # symbols used for macro context. Yahoo returns adjusted OHLC, so
            # do not apply corporate actions a second time.
            history = merge_and_adjust(
                [], history_bootstrapper.fetch_adjusted_daily(config.provider_symbol)
            )
            providers[config.symbol] = "yahoo_finance"
        else:
            try:
                if client is None:
                    raise RuntimeError("ALPHA_VANTAGE_API_KEY is unavailable")
                if not existing:
                    existing = history_bootstrapper.fetch_daily(
                        config.provider_symbol
                    )
                # The free Alpha Vantage API supports compact but rejects full history.
                daily = client.fetch_daily(
                    config.provider_symbol, outputsize="compact"
                )
                combined = merge_and_adjust(existing, daily)
                existing_actions = {
                    bar.trading_date: (bar.dividend, bar.split_factor)
                    for bar in existing
                    if bar.dividend or bar.split_factor != 1.0
                }
                combined = apply_corporate_actions(combined, existing_actions)
                should_refresh_actions = (
                    config.symbol in (refresh_action_symbols or set())
                    or has_new_price_anomaly(existing, daily)
                )
                if should_refresh_actions:
                    combined = apply_corporate_actions(
                        combined,
                        client.fetch_actions(config.provider_symbol),
                        authoritative=True,
                    )
                history = merge_and_adjust([], combined)
                providers[config.symbol] = "alpha_vantage"
            except Exception:
                # A missing key or a provider failure must degrade to the
                # configured backup instead of aborting the complete cache.
                history = merge_and_adjust(
                    [],
                    history_bootstrapper.fetch_adjusted_daily(
                        config.provider_symbol
                    ),
                )
                providers[config.symbol] = "yahoo_finance_fallback"
        staged.append((config, history))
        records.append(dashboard_record(config, calculate_cta(config.symbol, history)))

    payload = build_dashboard_payload(records)
    payload["provider_by_symbol"] = providers
    payload["provider_fallback_policy"] = (
        "alpha_vantage_primary; yahoo_finance_on_missing_key_or_failure"
    )
    for config, history in staged:
        write_history(history_dir / f"{config.symbol}.csv", history)
    data_dir.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
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
