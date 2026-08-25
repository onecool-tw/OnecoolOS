"""Reproducible Taiwan large/liquid stock research screen.

The screen is deliberately separate from CTA.  It uses only official TWSE
open-data snapshots, builds a broad liquid universe first, then applies one
common scoring version and cutoff.  Missing fields are exclusions, never
estimated values.
"""

from __future__ import annotations

from collections import Counter
from datetime import date
from math import isfinite
from typing import Iterable


SCREEN_VERSION = "onecool_tw_stock_screen_v1"
FORMAL_THRESHOLD = 80.0
WATCH_THRESHOLD = 75.0
DEFAULT_UNIVERSE_SIZE = 200
DEFAULT_TOP_N = 5
DEFAULT_INDUSTRY_LIMIT = 2


def build_taiwan_stock_screen_payload(
    price_rows: list[dict],
    valuation_rows: list[dict],
    revenue_rows: list[dict],
    income_rows: list[dict],
    *,
    universe_size: int = DEFAULT_UNIVERSE_SIZE,
    top_n: int = DEFAULT_TOP_N,
    industry_limit: int = DEFAULT_INDUSTRY_LIMIT,
) -> dict:
    """Validate, score, and rank a broad Taiwan-listed stock universe."""

    if universe_size < top_n or top_n < 1 or industry_limit < 1:
        raise ValueError("invalid universe, Top N, or industry limit")

    price_date = _single_date(price_rows, "Date")
    valuation_date = _single_date(valuation_rows, "Date")
    if price_date != valuation_date:
        raise ValueError(
            "price and valuation snapshots do not share one cutoff: "
            f"{price_date}, {valuation_date}"
        )
    revenue_period = _single_value(revenue_rows, "資料年月")
    income_year = _single_value(income_rows, "年度")
    income_quarter = _single_value(income_rows, "季別")

    duplicate_codes = set()
    price_map = _unique_map(price_rows, "Code", duplicate_codes)
    valuation_map = _unique_map(valuation_rows, "Code", duplicate_codes)
    revenue_map = _unique_map(revenue_rows, "公司代號", duplicate_codes)
    income_map = _unique_map(
        [row for row in income_rows if str(row.get("公司代號", "")).strip()],
        "公司代號",
        duplicate_codes,
    )

    liquid = []
    for code, row in price_map.items():
        if (
            not _is_common_stock_code(code)
            or code in duplicate_codes
            or code not in revenue_map
        ):
            continue
        trade_value = _number(row.get("TradeValue"))
        close = _number(row.get("ClosingPrice"))
        if trade_value is None or close is None or trade_value <= 0 or close <= 0:
            continue
        liquid.append((trade_value, code))
    liquid.sort(key=lambda item: (item[0], item[1]), reverse=True)
    universe = [code for _, code in liquid[:universe_size]]

    raw_candidates = []
    exclusions = []
    for liquidity_rank, code in enumerate(universe, start=1):
        missing = []
        valuation = valuation_map.get(code)
        revenue = revenue_map.get(code)
        income = income_map.get(code)
        if valuation is None:
            missing.append("valuation")
        if revenue is None:
            missing.append("monthly revenue")
        if income is None:
            missing.append("quarterly income statement")
        if missing:
            exclusions.append({"symbol": code, "reason": "missing " + ", ".join(missing)})
            continue

        metrics = {
            "monthly_revenue_yoy": _number(
                revenue.get("營業收入-去年同月增減(%)")
            ),
            "cumulative_revenue_yoy": _number(
                revenue.get("累計營業收入-前期比較增減(%)")
            ),
            "eps": _number(income.get("基本每股盈餘（元）")),
            "pe": _number(valuation.get("PEratio")),
            "pb": _number(valuation.get("PBratio")),
        }
        invalid = [
            name for name, value in metrics.items()
            if value is None or not isfinite(value)
        ]
        if metrics["eps"] is not None and metrics["eps"] <= 0:
            invalid.append("eps_non_positive")
        if metrics["pe"] is not None and metrics["pe"] <= 0:
            invalid.append("pe_non_positive")
        if metrics["pb"] is not None and metrics["pb"] <= 0:
            invalid.append("pb_non_positive")
        if invalid:
            exclusions.append({
                "symbol": code,
                "reason": "invalid or unavailable " + ", ".join(sorted(set(invalid))),
            })
            continue

        raw_candidates.append({
            "symbol": code,
            "company_name": str(revenue.get("公司名稱", "")).strip(),
            "industry": str(revenue.get("產業別", "未分類")).strip() or "未分類",
            "price_as_of": price_date,
            "fundamentals_as_of": f"{_roc_year_to_ad(income_year)}Q{income_quarter}",
            "monthly_revenue_as_of": _roc_month_to_iso(revenue_period),
            "price_basis": "official_unadjusted_close",
            "liquidity_rank": liquidity_rank,
            **metrics,
            "outlier_flags": [
                name for name in ("monthly_revenue_yoy", "cumulative_revenue_yoy")
                if abs(metrics[name]) > 500
            ],
        })

    if not raw_candidates:
        raise ValueError("Data Analyst validation failed: no complete candidates")

    _score_candidates(raw_candidates)
    ranked = sorted(
        raw_candidates,
        key=lambda item: (item["score"], -item["liquidity_rank"], item["symbol"]),
        reverse=True,
    )
    formal = [item for item in ranked if item["score"] >= FORMAL_THRESHOLD]
    watch = [
        item for item in ranked
        if WATCH_THRESHOLD <= item["score"] < FORMAL_THRESHOLD
    ]
    top = _apply_industry_limit(formal, top_n, industry_limit)

    return {
        "schema_version": "1.0",
        "screen_version": SCREEN_VERSION,
        "classification": "Onecool Taiwan official-data cross-sectional score",
        "data_status": "READY",
        "publication_status": "CURRENT",
        "expected_as_of": price_date,
        "price_basis": "official_unadjusted_close",
        "fundamentals_as_of": f"{_roc_year_to_ad(income_year)}Q{income_quarter}",
        "monthly_revenue_as_of": _roc_month_to_iso(revenue_period),
        "universe_method": "top common stocks by official daily trade value",
        "universe_size": len(universe),
        "validated_count": len(ranked),
        "formal_threshold": FORMAL_THRESHOLD,
        "watch_threshold": WATCH_THRESHOLD,
        "industry_limit": industry_limit,
        "formal_candidate_count": len(formal),
        "top5": top,
        "watchlist": watch[:10],
        "rankings": ranked,
        "exclusion_count": len(exclusions),
        "exclusions": exclusions,
        "data_quality": {
            "duplicate_codes": sorted(duplicate_codes),
            "ranking_recalculated": True,
            "estimated_values_used": False,
            "common_cutoff_verified": True,
            "outlier_policy": (
                "revenue growth above 500% is flagged; fixed score bands prevent "
                "extreme values from receiving extra credit"
            ),
        },
    }


def _score_candidates(candidates: list[dict]) -> None:
    """Apply fixed, versioned bands so daily peer composition cannot move scores."""

    liquidity_values = [-item["liquidity_rank"] for item in candidates]
    for item in candidates:
        components = {
            "monthly_revenue_yoy": _growth_points(item["monthly_revenue_yoy"]),
            "cumulative_revenue_yoy": _growth_points(item["cumulative_revenue_yoy"]),
            "eps": _eps_points(item["eps"]),
            "pe": _pe_points(item["pe"]),
            "pb": _pb_points(item["pb"]),
        }
        components["liquidity"] = round(
            _percentile(-item["liquidity_rank"], liquidity_values)
            * 15.0,
            2,
        )
        item["score_components"] = components
        item["score"] = round(sum(components.values()), 2)
        item["confidence"] = "HIGH"
        item["selection_status"] = (
            "FORMAL" if item["score"] >= FORMAL_THRESHOLD
            else "WATCH" if item["score"] >= WATCH_THRESHOLD
            else "BELOW_THRESHOLD"
        )


def _growth_points(value: float) -> float:
    if value <= 0:
        return 0.0
    if value < 5:
        return 5.0
    if value < 10:
        return 10.0
    if value < 20:
        return 15.0
    if value < 40:
        return 18.0
    return 20.0


def _eps_points(value: float) -> float:
    if value < 1:
        return 5.0
    if value < 2:
        return 10.0
    if value < 5:
        return 18.0
    if value < 10:
        return 24.0
    return 30.0


def _pe_points(value: float) -> float:
    if value <= 10:
        return 10.0
    if value <= 15:
        return 8.0
    if value <= 20:
        return 6.0
    if value <= 30:
        return 4.0
    if value <= 40:
        return 2.0
    return 0.0


def _pb_points(value: float) -> float:
    if value <= 1:
        return 5.0
    if value <= 2:
        return 4.0
    if value <= 3:
        return 3.0
    if value <= 5:
        return 2.0
    if value <= 8:
        return 1.0
    return 0.0


def _apply_industry_limit(items: list[dict], top_n: int, limit: int) -> list[dict]:
    counts: Counter[str] = Counter()
    selected = []
    for item in items:
        if counts[item["industry"]] >= limit:
            continue
        selected.append(item)
        counts[item["industry"]] += 1
        if len(selected) == top_n:
            break
    return selected


def _unique_map(rows: Iterable[dict], key: str, duplicates: set[str]) -> dict[str, dict]:
    result = {}
    for row in rows:
        code = str(row.get(key, "")).strip()
        if not code:
            continue
        if code in result:
            duplicates.add(code)
            result.pop(code, None)
        elif code not in duplicates:
            result[code] = row
    return result


def _single_date(rows: list[dict], key: str) -> str:
    value = _single_value(rows, key)
    if len(value) == 7:
        return f"{int(value[:3]) + 1911}-{value[3:5]}-{value[5:7]}"
    if len(value) == 8:
        return f"{value[:4]}-{value[4:6]}-{value[6:8]}"
    return date.fromisoformat(value).isoformat()


def _single_value(rows: list[dict], key: str) -> str:
    values = {str(row.get(key, "")).strip() for row in rows if str(row.get(key, "")).strip()}
    if len(values) != 1:
        raise ValueError(f"{key} does not have one common value: {sorted(values)}")
    return values.pop()


def _roc_year_to_ad(value: str) -> int:
    return int(value) + 1911 if len(value) <= 3 else int(value)


def _roc_month_to_iso(value: str) -> str:
    if len(value) != 5:
        raise ValueError(f"invalid ROC month: {value}")
    return f"{int(value[:3]) + 1911}-{value[3:5]}"


def _number(value) -> float | None:
    try:
        number = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _is_common_stock_code(code: str) -> bool:
    return len(code) == 4 and code.isdigit()


def _percentile(value: float, values: list[float]) -> float:
    ordered = sorted(values)
    if len(ordered) <= 1:
        return 1.0
    below = sum(candidate < value for candidate in ordered)
    equal = sum(candidate == value for candidate in ordered)
    rank = below + (equal - 1) / 2
    return rank / (len(ordered) - 1)
