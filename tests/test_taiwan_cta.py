from datetime import date, timedelta

import pytest

from onecool_os.market.etf_cta import DailyBar, ETFCTAError
from scripts.update_taiwan_cta import TAIWAN_CTA_SYMBOLS, update


def history(end: date, *, offset: float = 0.0) -> list[DailyBar]:
    bars = []
    for index in range(400):
        day = end - timedelta(days=399 - index)
        close = 100.0 + offset + index
        bars.append(
            DailyBar(
                trading_date=day,
                open=close,
                high=close,
                low=close,
                close=close,
                volume=1000,
                adjusted_close=close,
                source="test",
            )
        )
    return bars


def test_taiwan_cta_uses_shared_engine_and_cutoff(tmp_path) -> None:
    end = date(2026, 7, 28)

    def fetcher(symbol: str, *, period: str) -> list[DailyBar]:
        assert symbol in TAIWAN_CTA_SYMBOLS.values()
        return history(end, offset=10 if symbol == "2330.TW" else 0)

    payload = update(tmp_path, allow_bootstrap=True, fetcher=fetcher)

    assert payload["engine"] == "shared_onecool_cta_engine"
    assert payload["data_cutoff"] == "2026-07-28"
    assert [item["symbol"] for item in payload["results"]] == ["0050", "2330"]
    assert (tmp_path / "cta_latest.json").exists()
    assert (tmp_path / "history" / "0050.csv").exists()
    assert (tmp_path / "history" / "2330.csv").exists()


def test_taiwan_cta_rejects_mixed_cutoffs(tmp_path) -> None:
    def fetcher(symbol: str, *, period: str) -> list[DailyBar]:
        end = date(2026, 7, 28 if symbol == "0050.TW" else 27)
        return history(end)

    with pytest.raises(ETFCTAError, match="one complete trading-date cutoff"):
        update(tmp_path, allow_bootstrap=True, fetcher=fetcher)
