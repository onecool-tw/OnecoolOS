"""Deterministic US-rate regime backtest for Onecool cross-asset research.

The module is deliberately separate from CTA.  It describes how assets behaved
after observable month-end rate states and never creates a trading signal.
"""

from __future__ import annotations

import csv
import io
import json
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

from onecool_os.market.etf_cta import DailyBar, merge_and_adjust


FRED_ENDPOINT = "https://fred.stlouisfed.org/graph/fredgraph.csv"
YAHOO_CHART_ENDPOINT = "https://query1.finance.yahoo.com/v8/finance/chart"
STATE_THRESHOLD_PCT_POINTS = 0.25
FORWARD_HORIZONS = (1, 3, 6, 12)


@dataclass(frozen=True)
class RateSpec:
    series_id: str
    name: str
    kind: str = "yield"


@dataclass(frozen=True)
class AssetSpec:
    asset_id: str
    name: str
    asset_class: str
    source: str
    symbol: str | None = None
    local_path: str | None = None
    value_column: str = "adjusted_close"
    note: str | None = None


RATE_SPECS = (
    RateSpec("DFF", "Effective Fed Funds Rate", "policy_rate"),
    RateSpec("DGS2", "US Treasury 2Y Yield"),
    RateSpec("DGS10", "US Treasury 10Y Yield"),
    RateSpec("DGS30", "US Treasury 30Y Yield"),
    RateSpec("T10Y2Y", "US 10Y minus 2Y Curve", "curve"),
)


ASSET_SPECS = (
    AssetSpec("SPY", "S&P 500", "US equity", "yahoo", "SPY"),
    AssetSpec("QQQ", "Nasdaq 100", "US growth equity", "yahoo", "QQQ"),
    AssetSpec("IWM", "Russell 2000", "US small-cap equity", "yahoo", "IWM"),
    AssetSpec("0050", "元大台灣50", "Taiwan equity", "yahoo", "0050.TW"),
    AssetSpec("SHY", "1-3Y US Treasury ETF", "Short Treasury", "yahoo", "SHY"),
    AssetSpec("IEF", "7-10Y US Treasury ETF", "Intermediate Treasury", "yahoo", "IEF"),
    AssetSpec("TLT", "20+Y US Treasury ETF", "Long Treasury", "yahoo", "TLT"),
    AssetSpec("GLD", "Gold ETF", "Gold", "yahoo", "GLD"),
    AssetSpec(
        "DXY",
        "US Dollar Index",
        "US dollar",
        "yahoo",
        "DX-Y.NYB",
        note="Price index; not an investable total-return vehicle.",
    ),
    AssetSpec(
        "WTI",
        "WTI Spot Crude Oil",
        "Energy commodity",
        "fred",
        "DCOILWTICO",
        note="Spot-price change; excludes futures roll yield and collateral return.",
    ),
    AssetSpec("VNQ", "US REIT ETF", "REIT", "yahoo", "VNQ"),
    AssetSpec("BTC", "Bitcoin USD", "Crypto", "yahoo", "BTC-USD"),
    AssetSpec("AIQ", "Global X Artificial Intelligence ETF", "AI proxy", "yahoo", "AIQ"),
    AssetSpec("SMIN", "iShares MSCI India Small-Cap ETF", "India proxy", "yahoo", "SMIN"),
    AssetSpec("RING", "iShares MSCI Global Gold Miners ETF", "Gold-miner proxy", "yahoo", "RING"),
    AssetSpec("IBB", "iShares Biotechnology ETF", "Biotech proxy", "yahoo", "IBB"),
    AssetSpec("PICK", "iShares MSCI Global Metals & Mining ETF", "Mining proxy", "yahoo", "PICK"),
    AssetSpec("RXI", "iShares Global Consumer Discretionary ETF", "Consumption proxy", "yahoo", "RXI"),
    AssetSpec("IXC", "iShares Global Energy ETF", "Energy-equity proxy", "yahoo", "IXC"),
    AssetSpec("A10124", "富邦AI智能新趨勢多重資產型基金-A(美元)", "Held fund", "local", local_path="data/market/fund_nav/history/A10124.csv", value_column="nav"),
    AssetSpec("A16075", "群益印度中小基金-美元", "Held fund", "local", local_path="data/market/fund_nav/history/A16075.csv", value_column="nav"),
    AssetSpec("B23554", "施羅德環球-環球黃金美元A累積", "Held fund", "local", local_path="data/market/fund_nav/history/B23554.csv", value_column="nav"),
    AssetSpec("B15080", "富蘭克林坦伯頓-生技領航A(acc)", "Held fund", "local", local_path="data/market/fund_nav/history/B15080.csv", value_column="nav"),
    AssetSpec("B09007", "貝萊德世界礦業A2美元", "Held fund", "local", local_path="data/market/fund_nav/history/B09007.csv", value_column="nav"),
    AssetSpec("B16019", "景順環球消費趨勢基金A美元", "Held fund", "local", local_path="data/market/fund_nav/history/B16019.csv", value_column="nav"),
    AssetSpec("B23070", "施羅德環球能源基金", "Held fund", "local", local_path="data/market/fund_nav/history/B23070.csv", value_column="nav"),
)


class RateAssetBacktestError(RuntimeError):
    """Raised when source data is missing or structurally invalid."""


def _download(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "OnecoolOS/1.0 rate-backtest"})
    with urlopen(request, timeout=60) as response:  # noqa: S310 - fixed HTTPS sources.
        return response.read()


def fetch_fred_series(series_id: str, *, start: str = "1950-01-01") -> pd.Series:
    url = f"{FRED_ENDPOINT}?{urlencode({'id': series_id, 'cosd': start})}"
    payload = _download(url).decode("utf-8-sig")
    frame = pd.read_csv(io.StringIO(payload))
    date_column = "DATE" if "DATE" in frame.columns else "observation_date"
    if date_column not in frame or series_id not in frame:
        raise RateAssetBacktestError(f"FRED fields missing for {series_id}")
    dates = pd.to_datetime(frame[date_column], errors="coerce")
    values = pd.to_numeric(frame[series_id], errors="coerce")
    series = pd.Series(values.to_numpy(), index=dates, name=series_id).dropna()
    if series_id == "DGS30":
        # FRED's official notes say the 30Y constant-maturity series was
        # discontinued after 2002-02-18 and reintroduced on 2006-02-09.
        # Exclude that interval even if a distribution endpoint supplies rows.
        gap = (series.index > pd.Timestamp("2002-02-18")) & (
            series.index < pd.Timestamp("2006-02-09")
        )
        series = series[~gap]
    if series.empty:
        raise RateAssetBacktestError(f"FRED returned no observations for {series_id}")
    return series.sort_index()


def fetch_yahoo_adjusted_close(symbol: str) -> pd.Series:
    query = urlencode(
        {
            "period1": 0,
            "period2": 4102444800,
            "interval": "1d",
            "events": "div,splits",
        }
    )
    payload = json.loads(_download(f"{YAHOO_CHART_ENDPOINT}/{symbol}?{query}"))
    chart = payload.get("chart") or {}
    if chart.get("error"):
        raise RateAssetBacktestError(f"Yahoo error for {symbol}: {chart['error']}")
    results = chart.get("result") or []
    if not results:
        raise RateAssetBacktestError(f"Yahoo returned no result for {symbol}")
    return yahoo_result_to_adjusted_close(results[0], symbol)


def yahoo_result_to_adjusted_close(result: Mapping, symbol: str) -> pd.Series:
    timestamps = result.get("timestamp") or []
    indicators = result.get("indicators") or {}
    closes = (indicators.get("quote") or [{}])[0].get("close")
    if not timestamps or not closes or len(timestamps) != len(closes):
        raise RateAssetBacktestError(f"Yahoo price fields invalid for {symbol}")
    dates = pd.to_datetime(timestamps, unit="s", utc=True).tz_convert(None).normalize()
    events = result.get("events") or {}
    dividends = {
        datetime.fromtimestamp(int(item.get("date", key)), UTC).date(): float(item["amount"])
        for key, item in (events.get("dividends") or {}).items()
        if item.get("amount") is not None
    }
    splits = {}
    for key, item in (events.get("splits") or {}).items():
        day = datetime.fromtimestamp(int(item.get("date", key)), UTC).date()
        numerator = float(item.get("numerator") or 0)
        denominator = float(item.get("denominator") or 0)
        if numerator > 0 and denominator > 0:
            splits[day] = numerator / denominator
    bars = []
    previous_close: float | None = None
    for day, close in zip(dates, closes):
        if close is None or not math.isfinite(float(close)) or float(close) <= 0:
            continue
        trading_date = day.date()
        split_factor = splits.get(trading_date, 1.0)
        if split_factor == 1.0 and previous_close is not None:
            split_factor = infer_split_factor(previous_close, float(close))
        bars.append(
            DailyBar(
                trading_date=trading_date,
                open=float(close),
                high=float(close),
                low=float(close),
                close=float(close),
                volume=0,
                dividend=dividends.get(trading_date, 0.0),
                split_factor=split_factor,
                source="yahoo_chart_raw_locally_adjusted",
            )
        )
        previous_close = float(close)
    adjusted = merge_and_adjust([], bars)
    series = pd.Series(
        [bar.adjusted_close for bar in adjusted],
        index=pd.to_datetime([bar.trading_date for bar in adjusted]),
        name=symbol,
        dtype="float64",
    ).dropna()
    series = series[~series.index.duplicated(keep="last")]
    if series.empty:
        raise RateAssetBacktestError(f"Yahoo returned no valid prices for {symbol}")
    return series.sort_index()


def infer_split_factor(previous_close: float, current_close: float) -> float:
    """Conservatively infer an omitted simple split from an integer price gap."""

    if previous_close <= 0 or current_close <= 0:
        return 1.0
    raw_ratio = current_close / previous_close
    if 0.55 <= raw_ratio <= 1.8:
        return 1.0
    for factor in (2.0, 3.0, 4.0, 5.0, 10.0):
        if abs(current_close * factor / previous_close - 1.0) <= 0.05:
            return factor
        if abs(current_close / factor / previous_close - 1.0) <= 0.05:
            return 1.0 / factor
    return 1.0


def read_local_series(root: Path, spec: AssetSpec) -> pd.Series:
    if not spec.local_path:
        raise RateAssetBacktestError(f"Local path missing for {spec.asset_id}")
    path = root / spec.local_path
    frame = pd.read_csv(path)
    if "date" not in frame or spec.value_column not in frame:
        raise RateAssetBacktestError(f"Local fields invalid for {spec.asset_id}")
    dates = pd.to_datetime(frame["date"], errors="coerce")
    values = pd.to_numeric(frame[spec.value_column], errors="coerce")
    series = pd.Series(values.to_numpy(), index=dates, name=spec.asset_id).dropna()
    return series[~series.index.duplicated(keep="last")].sort_index()


def month_end(series: pd.Series) -> pd.Series:
    clean = series.dropna().sort_index()
    clean.index = pd.DatetimeIndex(clean.index).to_period("M").to_timestamp("M")
    monthly = clean.groupby(level=0).last()
    current_month = pd.Timestamp.now(tz="UTC").tz_localize(None).to_period("M")
    return monthly[monthly.index.to_period("M") < current_month]


def classify_direction(series: pd.Series, threshold: float = STATE_THRESHOLD_PCT_POINTS) -> pd.Series:
    change = series - series.shift(3)
    return pd.Series(
        np.select(
            [change >= threshold, change <= -threshold],
            ["RISING", "FALLING"],
            default="STABLE",
        ),
        index=series.index,
        name=f"{series.name}_state",
    ).where(change.notna())


def build_rate_states(rates: Mapping[str, pd.Series]) -> dict[str, pd.Series]:
    states: dict[str, pd.Series] = {}
    for spec in RATE_SPECS:
        series = rates[spec.series_id]
        if spec.kind != "curve":
            states[spec.series_id] = classify_direction(series)
            continue
        direction = classify_direction(series).replace(
            {"RISING": "STEEPENING", "FALLING": "FLATTENING"}
        )
        states["T10Y2Y_DIRECTION"] = direction
        states["T10Y2Y_LEVEL"] = pd.Series(
            np.where(series < 0, "INVERTED", "POSITIVE"),
            index=series.index,
            name="T10Y2Y_level",
        ).where(series.notna())
    return states


def _metrics(returns: pd.Series) -> dict[str, float | int | None | str]:
    clean = returns.replace([np.inf, -np.inf], np.nan).dropna()
    count = int(clean.size)
    if not count:
        return {
            "sample_months": 0,
            "mean_return_pct": None,
            "median_return_pct": None,
            "win_rate_pct": None,
            "worst_return_pct": None,
            "best_return_pct": None,
            "sample_quality": "INSUFFICIENT",
        }
    return {
        "sample_months": count,
        "mean_return_pct": round(float(clean.mean() * 100), 4),
        "median_return_pct": round(float(clean.median() * 100), 4),
        "win_rate_pct": round(float((clean > 0).mean() * 100), 2),
        "worst_return_pct": round(float(clean.min() * 100), 4),
        "best_return_pct": round(float(clean.max() * 100), 4),
        "sample_quality": "HIGH" if count >= 120 else "MEDIUM" if count >= 60 else "LOW",
    }


def _regression(asset_return: pd.Series, rate_change: pd.Series) -> dict[str, float | int | None]:
    joined = pd.concat([asset_return, rate_change], axis=1).dropna()
    if len(joined) < 24 or float(joined.iloc[:, 1].std()) == 0:
        return {"sample_months": int(len(joined)), "return_per_100bp_pct": None, "correlation": None, "r_squared": None}
    x = joined.iloc[:, 1].to_numpy(dtype=float)
    y = joined.iloc[:, 0].to_numpy(dtype=float)
    slope, _intercept = np.polyfit(x, y, 1)
    correlation = float(np.corrcoef(x, y)[0, 1])
    return {
        "sample_months": int(len(joined)),
        "return_per_100bp_pct": round(float(slope * 100), 4),
        "correlation": round(correlation, 4),
        "r_squared": round(correlation * correlation, 4),
    }


def backtest_asset(
    prices: pd.Series,
    rates: Mapping[str, pd.Series],
    states: Mapping[str, pd.Series],
) -> dict:
    prices = month_end(prices)
    monthly_return = prices.pct_change(fill_method=None)
    forward = {h: prices.shift(-h) / prices - 1.0 for h in FORWARD_HORIZONS}
    state_results = []
    for state_id, state_series in states.items():
        aligned_state = state_series.reindex(prices.index)
        for state in sorted(str(value) for value in aligned_state.dropna().unique()):
            mask = aligned_state == state
            record = {
                "rate_state_id": state_id,
                "state": state,
                "concurrent_1m": _metrics(monthly_return[mask]),
                "forward": {str(h): _metrics(values[mask]) for h, values in forward.items()},
                "state_onsets": {
                    str(h): _metrics(values[mask & (aligned_state.shift(1) != state)])
                    for h, values in forward.items()
                },
            }
            state_results.append(record)
    regressions = {}
    for spec in RATE_SPECS:
        rate = rates[spec.series_id].reindex(prices.index)
        regressions[spec.series_id] = _regression(monthly_return, rate.diff())
    return {
        "start": prices.index.min().date().isoformat(),
        "end": prices.index.max().date().isoformat(),
        "monthly_observations": int(prices.size),
        "state_results": state_results,
        "monthly_rate_change_regressions": regressions,
    }


def _write_monthly_csv(path: Path, series: pd.Series, value_name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = month_end(series).rename(value_name).to_frame()
    frame.index.name = "month_end"
    frame.to_csv(path, float_format="%.8f")


def _read_monthly_csv(path: Path, name: str) -> pd.Series:
    frame = pd.read_csv(path)
    if "month_end" not in frame or "value" not in frame:
        raise RateAssetBacktestError(f"Cached monthly fields invalid for {name}")
    dates = pd.to_datetime(frame["month_end"], errors="coerce")
    values = pd.to_numeric(frame["value"], errors="coerce")
    return pd.Series(values.to_numpy(), index=dates, name=name).dropna().sort_index()


def run_backtest(
    root: Path,
    output_dir: Path | None = None,
    *,
    refresh_sources: bool = True,
) -> dict:
    destination = output_dir or root / "data/market/rate_asset_backtest"
    rates = {}
    for spec in RATE_SPECS:
        cache = destination / "rates" / f"{spec.series_id}.csv"
        rates[spec.series_id] = (
            month_end(fetch_fred_series(spec.series_id))
            if refresh_sources or not cache.exists()
            else _read_monthly_csv(cache, spec.series_id)
        )
    for series_id, series in rates.items():
        _write_monthly_csv(destination / "rates" / f"{series_id}.csv", series, "value")
    states = build_rate_states(rates)

    def load_asset(spec: AssetSpec) -> pd.Series:
        cache = destination / "assets" / f"{spec.asset_id}.csv"
        if not refresh_sources and cache.exists():
            return _read_monthly_csv(cache, spec.asset_id)
        if spec.source == "yahoo":
            return fetch_yahoo_adjusted_close(str(spec.symbol))
        if spec.source == "fred":
            return fetch_fred_series(str(spec.symbol), start="1970-01-01")
        return read_local_series(root, spec)

    loaded_assets: dict[str, pd.Series] = {}
    load_errors: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(load_asset, spec): spec for spec in ASSET_SPECS}
        for future in as_completed(futures):
            spec = futures[future]
            try:
                loaded_assets[spec.asset_id] = future.result()
            except Exception as exc:  # noqa: BLE001 - isolated provider boundary.
                load_errors[spec.asset_id] = str(exc)

    asset_results = []
    provider_errors = []
    for spec in ASSET_SPECS:
        try:
            if spec.asset_id in load_errors:
                raise RateAssetBacktestError(load_errors[spec.asset_id])
            prices = loaded_assets[spec.asset_id]
            monthly = month_end(prices)
            _write_monthly_csv(destination / "assets" / f"{spec.asset_id}.csv", monthly, "value")
            result = backtest_asset(monthly, rates, states)
            asset_results.append(
                {
                    "asset_id": spec.asset_id,
                    "name": spec.name,
                    "asset_class": spec.asset_class,
                    "source": spec.source,
                    "symbol": spec.symbol,
                    "note": spec.note,
                    **result,
                }
            )
        except Exception as exc:  # noqa: BLE001 - one asset must not sink the study.
            provider_errors.append({"asset_id": spec.asset_id, "error": str(exc)})

    if len(asset_results) < len(ASSET_SPECS) - 2:
        raise RateAssetBacktestError(
            f"Only {len(asset_results)} of {len(ASSET_SPECS)} assets succeeded"
        )
    payload = {
        "schema_version": "1.0",
        "module": "Onecool US Rate x Asset Backtest",
        "generated_at": datetime.now(UTC).isoformat(),
        "decision_role": "RESEARCH_ONLY",
        "cta_override_allowed": False,
        "method": {
            "frequency": "monthly month-end",
            "rate_direction": "three-month change: >= +25bp rising, <= -25bp falling, otherwise stable",
            "curve_level": "10Y-2Y below zero is inverted",
            "asset_return": "locally adjusted total return from raw Yahoo close, split and dividend events; fund NAV return for held funds",
            "forward_horizons_months": list(FORWARD_HORIZONS),
            "state_onsets": "forward returns measured only once when a state begins, reducing repeated counting of one regime",
            "regression": "asset monthly return versus one-month rate change; slope shown per +100bp",
            "warning": "Descriptive historical association, not proof that rates caused the asset return.",
        },
        "rates": [spec.__dict__ for spec in RATE_SPECS],
        "asset_count_expected": len(ASSET_SPECS),
        "asset_count_valid": len(asset_results),
        "provider_errors": provider_errors,
        "assets": asset_results,
    }
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "backtest_latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_summary_csv(payload, destination / "summary_latest.csv")
    return payload


def write_summary_csv(payload: Mapping, path: Path) -> None:
    rows = []
    for asset in payload["assets"]:
        for result in asset["state_results"]:
            for horizon, metrics in result["forward"].items():
                rows.append(
                    {
                        "asset_id": asset["asset_id"],
                        "asset_name": asset["name"],
                        "asset_class": asset["asset_class"],
                        "start": asset["start"],
                        "end": asset["end"],
                        "rate_state_id": result["rate_state_id"],
                        "state": result["state"],
                        "forward_months": horizon,
                        **metrics,
                    }
                )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        if not rows:
            return
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
