"""Collect official Taiwan market-pressure inputs without evaluating the light.

This module is deliberately a data adapter.  It never contains GREEN/YELLOW/RED
thresholds and never writes the formal market-pressure SSOT.
"""

from __future__ import annotations

import json
import re
import time
from datetime import UTC, date, datetime
from html import unescape
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlencode
from urllib.request import Request, urlopen

OUTPUT_PATH = Path(
    "data/market/taiwan_stock_intelligence/market_pressure_inputs_latest.json"
)
TWSE_MARGIN_URL = "https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN"
TAIFEX_VIX_URL = "https://www.taifex.com.tw/cht/7/vixMinNew"
USER_AGENT = "OnecoolOS/1.0 official-market-data-validator"


def _number(value: Any) -> float | None:
    text = str(value).replace(",", "").replace("+", "").strip()
    if not text or text in {"--", "-", "N/A"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _roc_date(text: str) -> str | None:
    match = re.search(r"(?<!\d)(\d{3})[年/-](\d{1,2})[月/-](\d{1,2})日?", text)
    if not match:
        return None
    year, month, day = map(int, match.groups())
    return date(year + 1911, month, day).isoformat()


def _field_index(fields: list[str], token: str) -> int | None:
    for index, field in enumerate(fields):
        if token in field.replace(" ", ""):
            return index
    return None


def parse_twse_margin(payload: Mapping[str, Any], requested_as_of: str) -> dict[str, Any]:
    """Parse the official TWSE market-wide margin/short balance response."""

    tables = payload.get("tables")
    if not isinstance(tables, list):
        tables = [payload]
    published_dates: set[str] = set()
    metrics: dict[str, dict[str, float | None]] = {}
    saw_margin_row = saw_short_row = False

    for table in tables:
        if not isinstance(table, Mapping):
            continue
        title = str(table.get("title") or "")
        parsed_date = _roc_date(title)
        if parsed_date:
            published_dates.add(parsed_date)
        fields = [str(field) for field in (table.get("fields") or [])]
        rows = table.get("data") or []
        if not fields or not isinstance(rows, list):
            continue
        previous_index = _field_index(fields, "前日餘額")
        current_index = _field_index(fields, "今日餘額")
        change_index = _field_index(fields, "今日增減")
        if current_index is None:
            continue
        for row in rows:
            if not isinstance(row, list) or not row:
                continue
            label = re.sub(r"\s+", "", str(row[0]))
            is_margin = "融資" in label
            is_short = "融券" in label
            if not (is_margin or is_short):
                continue
            current = _number(row[current_index]) if current_index < len(row) else None
            previous = (
                _number(row[previous_index])
                if previous_index is not None and previous_index < len(row)
                else None
            )
            change = (
                _number(row[change_index])
                if change_index is not None and change_index < len(row)
                else (current - previous if current is not None and previous is not None else None)
            )
            if current is None:
                continue
            metrics[label] = {"previous": previous, "current": current, "change": change}
            saw_margin_row |= is_margin
            saw_short_row |= is_short

    if requested_as_of not in published_dates:
        return {
            "status": "NOT_PUBLISHED",
            "as_of": max(published_dates) if published_dates else None,
            "metrics": {},
            "error": "REQUESTED_DATE_NOT_PRESENT",
        }
    if not (saw_margin_row and saw_short_row):
        return {
            "status": "PUBLISHED_PARSE_FAILED",
            "as_of": requested_as_of,
            "metrics": metrics,
            "error": "MARGIN_OR_SHORT_BALANCE_NOT_PARSED",
        }
    return {
        "status": "VERIFIED",
        "as_of": requested_as_of,
        "metrics": metrics,
        "error": None,
    }


def parse_taifex_vix(html: str, requested_as_of: str) -> dict[str, Any]:
    """Extract the official VIX value, including values stored in input tags."""

    slash_date = requested_as_of.replace("-", "/")
    row_match = re.search(
        rf"<tr\b[^>]*>.*?{re.escape(slash_date)}.*?</tr>", html, re.I | re.S
    )
    if not row_match:
        dates = sorted(set(re.findall(r"20\d{2}/\d{2}/\d{2}", html)))
        return {
            "status": "NOT_PUBLISHED",
            "as_of": dates[-1].replace("/", "-") if dates else None,
            "value": None,
            "error": "REQUESTED_DATE_NOT_PRESENT",
        }

    row = row_match.group(0)
    values = [
        _number(unescape(value))
        for value in re.findall(r"\bvalue\s*=\s*[\"']([^\"']+)[\"']", row, re.I)
    ]
    values = [value for value in values if value is not None and 0 < value < 200]
    if not values:
        text = re.sub(r"<[^>]+>", " ", row)
        text = text.replace(slash_date, " ").replace(requested_as_of, " ")
        candidates = [
            _number(value)
            for value in re.findall(r"(?<!\d)(\d{1,3}(?:\.\d+)?)", unescape(text))
        ]
        values = [value for value in candidates if value is not None and 0 < value < 200]
    if not values:
        return {
            "status": "PUBLISHED_PARSE_FAILED",
            "as_of": requested_as_of,
            "value": None,
            "error": "VIX_VALUE_NOT_PARSED",
        }
    return {
        "status": "VERIFIED",
        "as_of": requested_as_of,
        "value": values[-1],
        "error": None,
    }


def _get_json(url: str, *, timeout: int = 30) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8-sig"))


def _get_text(url: str, *, timeout: int = 30) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def collect_once(
    requested_as_of: str,
    *,
    get_json: Callable[[str], Mapping[str, Any]] = _get_json,
    get_text: Callable[[str], str] = _get_text,
) -> dict[str, dict[str, Any]]:
    margin_url = TWSE_MARGIN_URL + "?" + urlencode({
        "date": requested_as_of.replace("-", ""),
        "selectType": "MS",
        "response": "json",
    })
    try:
        margin = parse_twse_margin(get_json(margin_url), requested_as_of)
    except Exception as exc:  # network/provider failure is preserved, never guessed
        margin = {"status": "FETCH_FAILED", "as_of": None, "metrics": {}, "error": type(exc).__name__}
    margin["source_url"] = margin_url

    try:
        volatility = parse_taifex_vix(get_text(TAIFEX_VIX_URL), requested_as_of)
    except Exception as exc:
        volatility = {"status": "FETCH_FAILED", "as_of": None, "value": None, "error": type(exc).__name__}
    volatility["source_url"] = TAIFEX_VIX_URL
    return {"margin": margin, "volatility": volatility}


def collect_market_pressure_inputs(
    requested_as_of: str,
    *,
    attempts: int = 1,
    interval_seconds: int = 0,
    collector: Callable[[str], dict[str, dict[str, Any]]] = collect_once,
) -> dict[str, Any]:
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    sources: dict[str, dict[str, Any]] = {}
    attempts_used = 0
    for attempt in range(1, attempts + 1):
        attempts_used = attempt
        sources = collector(requested_as_of)
        if all(item.get("status") == "VERIFIED" for item in sources.values()):
            break
        if attempt < attempts and interval_seconds:
            time.sleep(interval_seconds)
    issues = [name + ":" + str(item.get("status")) for name, item in sources.items()
              if item.get("status") != "VERIFIED" or item.get("as_of") != requested_as_of]
    return {
        "schema_version": "1.0",
        "module": "Onecool Taiwan Official Market Pressure Inputs",
        "generated_at": datetime.now(UTC).isoformat(),
        "requested_as_of": requested_as_of,
        "status": "READY" if not issues else "UPDATE_INCOMPLETE",
        "attempts_used": attempts_used,
        "issues": issues,
        "sources": sources,
        "authority": "OFFICIAL_INPUT_CACHE_ONLY_NO_PRESSURE_LIGHT_CALCULATION",
    }


def write_market_pressure_inputs(root: Path, payload: Mapping[str, Any]) -> Path:
    destination = root / OUTPUT_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(destination)
    return destination
