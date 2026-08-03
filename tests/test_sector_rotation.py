from datetime import date, timedelta

from onecool_os.market.etf_cta import DailyBar
from onecool_os.market.sector_rotation import (
    SECTOR_ETFS,
    build_sector_rotation_payload,
    calculate_sector_return,
)


def history(symbol: str, slope: float) -> list[DailyBar]:
    start = date(2026, 6, 1)
    return [
        DailyBar(
            trading_date=start + timedelta(days=index),
            open=100 + index * slope,
            high=100 + index * slope,
            low=100 + index * slope,
            close=100 + index * slope,
            volume=100,
            adjusted_close=100 + index * slope,
            source=symbol,
        )
        for index in range(61)
    ]


def test_sector_rotation_requires_all_eleven_same_date_series() -> None:
    results = [
        calculate_sector_return(symbol, history(symbol, index / 10 + 0.1))
        for index, symbol in enumerate(SECTOR_ETFS)
    ]

    payload = build_sector_rotation_payload(results)

    assert len(payload["results"]) == 11
    assert len(payload["top_sectors"]) == 3
    assert payload["as_of"] == "2026-07-31"
    assert payload["results"][0]["composite_score"] >= payload["results"][-1][
        "composite_score"
    ]
