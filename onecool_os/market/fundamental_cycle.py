"""Monthly, cacheable US fundamental-cycle context for Fund Intelligence.

This is an IZAAX-inspired Onecool interpretation, not a reproduction of any
author's proprietary model.  It summarizes released official data and never
creates a fund trading signal.
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.request import Request, urlopen


FRED_CSV_ENDPOINT = "https://fred.stlouisfed.org/graph/fredgraph.csv"


@dataclass(frozen=True)
class SeriesSpec:
    series_id: str
    name: str
    category: str


@dataclass(frozen=True)
class Observation:
    observation_date: date
    value: float


SERIES_SPECS = (
    SeriesSpec("PAYEMS", "Nonfarm payrolls", "employment"),
    SeriesSpec("RRSFS", "Real retail and food services sales", "consumption"),
    SeriesSpec("PCEC96", "Real personal consumption expenditures", "consumption"),
    SeriesSpec("NEWORDER", "Core capital-goods new orders", "investment"),
    SeriesSpec("PERMIT", "Building permits", "housing"),
    SeriesSpec("INDPRO", "Industrial production", "production"),
    SeriesSpec("PCEPILFE", "Core PCE price index", "inflation"),
    SeriesSpec("BAA10YM", "Baa corporate spread over 10Y Treasury", "credit"),
)
GROWTH_SERIES = tuple(spec.series_id for spec in SERIES_SPECS[:6])
CACHE_PATH = Path("data/market/fundamental_cycle/fundamental_cycle_latest.json")
SNAPSHOT_DIR = Path("data/market/fundamental_cycle/snapshots")


class FundamentalCycleError(RuntimeError):
    """Raised when official macro data cannot be parsed or summarized safely."""


def fred_series_url(series_id: str) -> str:
    """Return the no-key official FRED CSV URL with sufficient lookback."""

    return f"{FRED_CSV_ENDPOINT}?id={series_id}&cosd=2020-01-01"


def parse_fred_csv(payload: bytes | str, series_id: str) -> list[Observation]:
    """Parse one FRED graph CSV while rejecting missing/non-numeric rows."""

    text = payload.decode("utf-8-sig") if isinstance(payload, bytes) else payload
    reader = csv.DictReader(io.StringIO(text))
    date_field = "DATE" if "DATE" in (reader.fieldnames or ()) else "observation_date"
    if series_id not in (reader.fieldnames or ()) or date_field not in (
        reader.fieldnames or ()
    ):
        raise FundamentalCycleError(f"FRED CSV fields missing for {series_id}")
    observations: list[Observation] = []
    for row in reader:
        raw = (row.get(series_id) or "").strip()
        if not raw or raw == ".":
            continue
        try:
            observations.append(
                Observation(date.fromisoformat(row[date_field]), float(raw))
            )
        except (TypeError, ValueError) as exc:
            raise FundamentalCycleError(
                f"Invalid FRED observation for {series_id}"
            ) from exc
    if not observations:
        raise FundamentalCycleError(f"No valid FRED observations for {series_id}")
    return sorted(observations, key=lambda item: item.observation_date)


class FredGraphClient:
    """Small public FRED CSV client; no API key and no forecast data."""

    def __init__(self, request: Callable[[str], bytes] | None = None) -> None:
        self._request = request or _download

    def fetch(self, series_id: str) -> list[Observation]:
        return parse_fred_csv(self._request(fred_series_url(series_id)), series_id)


def _download(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "OnecoolOS/1.0 macro-context"})
    with urlopen(request, timeout=45) as response:  # noqa: S310 - fixed HTTPS host.
        return response.read()


def _window_average(values: Sequence[Observation], start: int, end: int) -> float:
    window = values[start:end]
    if len(window) != end - start:
        raise FundamentalCycleError("Insufficient observations for cycle window")
    return sum(item.value for item in window) / len(window)


def _growth_signal(
    values: Sequence[Observation], *, offset: int = 0
) -> tuple[str, float]:
    """Compare adjacent three-month averages without optimized thresholds."""

    if len(values) < 6 + offset:
        return "UNKNOWN", 0.0
    end = len(values) - offset
    recent = _window_average(values, end - 3, end)
    previous = _window_average(values, end - 6, end - 3)
    if previous == 0:
        return "UNKNOWN", 0.0
    change_pct = (recent / previous - 1.0) * 100.0
    if change_pct > 0:
        return "POSITIVE", change_pct
    if change_pct < 0:
        return "NEGATIVE", change_pct
    return "FLAT", change_pct


def _inflation_signal(values: Sequence[Observation]) -> tuple[str, float | None, float | None]:
    if len(values) < 19:
        return "UNKNOWN", None, None
    current_yoy = (values[-1].value / values[-13].value - 1.0) * 100.0
    prior_yoy = (values[-7].value / values[-19].value - 1.0) * 100.0
    delta = current_yoy - prior_yoy
    if current_yoy >= 2.5 and delta > 0.2:
        state = "ACCELERATING_PRESSURE"
    elif current_yoy >= 2.5:
        state = "PRESSURE"
    elif delta < -0.2:
        state = "EASING"
    else:
        state = "STABLE"
    return state, current_yoy, delta


def _credit_signal(values: Sequence[Observation]) -> tuple[str, float | None]:
    signal, change = _growth_signal(values)
    if signal == "POSITIVE":
        return "WIDENING", change
    if signal == "NEGATIVE":
        return "NARROWING", change
    return signal, change


def build_fundamental_cycle_payload(
    series: Mapping[str, Sequence[Observation]],
    *,
    generated_at: datetime | None = None,
) -> dict:
    """Build a deterministic context snapshot from released observations only."""

    records = []
    current_positive = current_negative = 0
    prior_positive = prior_negative = 0
    for spec in SERIES_SPECS:
        values = list(series.get(spec.series_id, ()))
        if not values:
            records.append(
                {
                    "series_id": spec.series_id,
                    "name": spec.name,
                    "category": spec.category,
                    "status": "UNKNOWN",
                    "source_url": f"https://fred.stlouisfed.org/series/{spec.series_id}",
                }
            )
            continue
        record = {
            "series_id": spec.series_id,
            "name": spec.name,
            "category": spec.category,
            "as_of": values[-1].observation_date.isoformat(),
            "latest_value": values[-1].value,
            "source_url": f"https://fred.stlouisfed.org/series/{spec.series_id}",
        }
        if spec.series_id in GROWTH_SERIES:
            status, change = _growth_signal(values)
            prior_status, _ = _growth_signal(values, offset=3)
            record.update(
                status=status,
                three_month_average_change_pct=round(change, 4),
                prior_status=prior_status,
            )
            current_positive += status == "POSITIVE"
            current_negative += status == "NEGATIVE"
            prior_positive += prior_status == "POSITIVE"
            prior_negative += prior_status == "NEGATIVE"
        elif spec.series_id == "PCEPILFE":
            status, yoy, delta = _inflation_signal(values)
            record.update(
                status=status,
                yoy_pct=round(yoy, 4) if yoy is not None else None,
                six_month_yoy_delta_pct_points=(
                    round(delta, 4) if delta is not None else None
                ),
            )
        else:
            status, change = _credit_signal(values)
            record.update(
                status=status,
                three_month_average_change_pct=(
                    round(change, 4) if change is not None else None
                ),
            )
        records.append(record)

    known_growth = current_positive + current_negative + sum(
        item.get("status") == "FLAT"
        for item in records
        if item.get("series_id") in GROWTH_SERIES
    )
    inflation = next(
        (item.get("status") for item in records if item.get("series_id") == "PCEPILFE"),
        "UNKNOWN",
    )
    credit = next(
        (item.get("status") for item in records if item.get("series_id") == "BAA10YM"),
        "UNKNOWN",
    )
    if known_growth < 5:
        phase = "UNKNOWN"
    elif current_negative >= 4 and credit == "WIDENING":
        phase = "RECESSION"
    elif current_positive >= 4 and (
        prior_negative >= 4 or current_positive - prior_positive >= 2
    ):
        phase = "RECOVERY"
    elif current_positive >= 5 and inflation in {
        "PRESSURE",
        "ACCELERATING_PRESSURE",
    }:
        phase = "BOOM"
    elif current_positive >= 4:
        phase = "GROWTH"
    else:
        phase = "DIVERGENT"

    known_count = sum(item.get("status") != "UNKNOWN" for item in records)
    data_status = "READY" if known_count == len(SERIES_SPECS) else (
        "PARTIAL" if known_count >= 6 else "UNKNOWN"
    )
    confidence = "HIGH" if data_status == "READY" and phase != "DIVERGENT" else (
        "MEDIUM" if data_status in {"READY", "PARTIAL"} else "LOW"
    )
    timestamp = generated_at or datetime.now(UTC)
    dated_records = [item["as_of"] for item in records if item.get("as_of")]
    return {
        "schema_version": "1.0",
        "module": "Onecool Fundamental Cycle Context",
        "method": "IZAAX-inspired Onecool interpretation; context only",
        "generated_at": timestamp.isoformat(),
        "data_as_of": max(dated_records) if dated_records else None,
        "phase": phase,
        "phase_zh": {
            "RECOVERY": "復甦",
            "GROWTH": "成長",
            "BOOM": "榮景",
            "RECESSION": "衰退",
            "DIVERGENT": "分歧",
            "UNKNOWN": "Unknown",
        }[phase],
        "confidence": confidence,
        "data_status": data_status,
        "growth_breadth": {
            "positive": current_positive,
            "negative": current_negative,
            "known": known_growth,
        },
        "inflation_state": inflation,
        "credit_state": credit,
        "results": records,
        "decision_authority": "CONTEXT_ONLY",
        "revision_warning": "FRED observations may be revised; no vintage backtest claim",
    }


def _previous_month_snapshot(root: Path, month_key: str) -> dict | None:
    directory = root / SNAPSHOT_DIR
    candidates = sorted(path for path in directory.glob("*.json") if path.stem < month_key)
    if not candidates:
        return None
    return json.loads(candidates[-1].read_text(encoding="utf-8"))


def update_fundamental_cycle_cache(
    root: Path,
    *,
    client: FredGraphClient | None = None,
) -> dict:
    """Fetch official series and atomically publish the latest context cache."""

    provider = client or FredGraphClient()
    series: dict[str, Sequence[Observation]] = {}
    provider_errors: dict[str, str] = {}
    for spec in SERIES_SPECS:
        try:
            series[spec.series_id] = provider.fetch(spec.series_id)
        except Exception as exc:  # noqa: BLE001 - external provider boundary.
            provider_errors[spec.series_id] = str(exc)
    if not series:
        raise FundamentalCycleError("All FRED fundamental-cycle requests failed")
    payload = build_fundamental_cycle_payload(series)
    payload["provider_errors"] = provider_errors
    month_key = payload["generated_at"][:7]
    previous = _previous_month_snapshot(root, month_key)
    previous_phase = previous.get("phase") if previous else None
    payload["previous_phase"] = previous_phase
    payload["monthly_change"] = (
        "UNKNOWN"
        if previous_phase is None
        else "NO_CHANGE"
        if previous_phase == payload["phase"]
        else f"{previous_phase}->{payload['phase']}"
    )
    path = root / CACHE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    snapshot = root / SNAPSHOT_DIR / f"{month_key}.json"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot_temporary = snapshot.with_suffix(".tmp")
    snapshot_temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    snapshot_temporary.replace(snapshot)
    return payload


def load_fundamental_cycle(root: Path) -> dict | None:
    path = root / CACHE_PATH
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
