from datetime import UTC, date, datetime

from onecool_os.market.fundamental_cycle import (
    GROWTH_SERIES,
    Observation,
    SERIES_SPECS,
    build_fundamental_cycle_payload,
    parse_fred_csv,
    update_fundamental_cycle_cache,
)


def observations(values: list[float]) -> list[Observation]:
    return [
        Observation(date(2024 + index // 12, index % 12 + 1, 1), value)
        for index, value in enumerate(values)
    ]


def test_parse_fred_csv_ignores_missing_values() -> None:
    payload = "observation_date,PAYEMS\n2026-01-01,100\n2026-02-01,.\n2026-03-01,102\n"

    parsed = parse_fred_csv(payload, "PAYEMS")

    assert [item.value for item in parsed] == [100.0, 102.0]
    assert parsed[-1].observation_date == date(2026, 3, 1)


def test_cycle_classifies_broad_growth_with_inflation_as_boom() -> None:
    rising = observations([100 + index for index in range(24)])
    inflation = observations([100 * (1.003**index) for index in range(24)])
    narrowing_credit = observations([3.0 - index * 0.03 for index in range(24)])
    series = {series_id: rising for series_id in GROWTH_SERIES}
    series["PCEPILFE"] = inflation
    series["BAA10YM"] = narrowing_credit

    payload = build_fundamental_cycle_payload(
        series,
        generated_at=datetime(2026, 8, 25, tzinfo=UTC),
    )

    assert payload["phase"] == "BOOM"
    assert payload["phase_zh"] == "榮景"
    assert payload["data_status"] == "READY"
    assert payload["data_as_of"] == "2025-12-01"
    assert payload["decision_authority"] == "CONTEXT_ONLY"


def test_cycle_requires_enough_growth_series() -> None:
    series = {
        SERIES_SPECS[0].series_id: observations([100 + index for index in range(24)])
    }

    payload = build_fundamental_cycle_payload(series)

    assert payload["phase"] == "UNKNOWN"
    assert payload["data_status"] == "UNKNOWN"
    assert payload["confidence"] == "LOW"


def test_cycle_identifies_recession_only_with_broad_decline_and_tighter_credit() -> None:
    falling = observations([130 - index for index in range(24)])
    stable_inflation = observations([100 * (1.002**index) for index in range(24)])
    widening_credit = observations([1.5 + index * 0.03 for index in range(24)])
    series = {series_id: falling for series_id in GROWTH_SERIES}
    series["PCEPILFE"] = stable_inflation
    series["BAA10YM"] = widening_credit

    payload = build_fundamental_cycle_payload(series)

    assert payload["phase"] == "RECESSION"
    assert payload["credit_state"] == "WIDENING"


def test_cycle_identifies_broad_turnaround_as_recovery() -> None:
    turnaround = observations(
        [120 - index for index in range(21)] + [103, 106, 109]
    )
    stable_inflation = observations([100 * (1.002**index) for index in range(24)])
    narrowing_credit = observations([3.0 - index * 0.03 for index in range(24)])
    series = {series_id: turnaround for series_id in GROWTH_SERIES}
    series["PCEPILFE"] = stable_inflation
    series["BAA10YM"] = narrowing_credit

    payload = build_fundamental_cycle_payload(series)

    assert payload["phase"] == "RECOVERY"


def test_update_writes_latest_and_monthly_snapshot(tmp_path) -> None:
    rising = observations([100 + index for index in range(24)])
    inflation = observations([100 * (1.003**index) for index in range(24)])
    narrowing_credit = observations([3.0 - index * 0.03 for index in range(24)])
    series = {series_id: rising for series_id in GROWTH_SERIES}
    series["PCEPILFE"] = inflation
    series["BAA10YM"] = narrowing_credit

    class FakeClient:
        def fetch(self, series_id):
            return series[series_id]

    payload = update_fundamental_cycle_cache(tmp_path, client=FakeClient())
    month = payload["generated_at"][:7]

    assert payload["monthly_change"] == "UNKNOWN"
    assert (
        tmp_path
        / "data/market/fundamental_cycle/fundamental_cycle_latest.json"
    ).exists()
    assert (
        tmp_path / f"data/market/fundamental_cycle/snapshots/{month}.json"
    ).exists()
