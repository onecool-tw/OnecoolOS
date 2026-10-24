from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from onecool_os.market.etf_cta import DailyBar, ETFCTAError, read_history, write_history
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


def test_taiwan_cta_uses_three_schedules_plus_health_recovery() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "update-taiwan-cta.yml").read_text()

    assert workflow.count("- cron:") == 3
    assert 'cron: "0 7 * * 1-5"' in workflow
    assert 'cron: "0 8 * * 1-5"' in workflow
    assert 'cron: "0 9 * * 1-5"' in workflow


@pytest.mark.parametrize('cached', [False, True])
def test_closed_session_row_does_not_break_pair_cutoff_on_the_following_day(tmp_path, cached):
    if cached:
        for symbol in TAIWAN_CTA_SYMBOLS:
            write_history(tmp_path / 'history' / f'{symbol}.csv', history(date(2026, 10, 23)))

    def fetcher(symbol, *, period):
        return history(date(2026, 10, 22 if symbol == '0050.TW' else 23))

    payload = update(tmp_path, allow_bootstrap=True, fetcher=fetcher,
                     reference_time=datetime.fromisoformat('2026-10-24T14:00:00+08:00'))
    assert payload['data_cutoff'] == '2026-10-22'
    for symbol in TAIWAN_CTA_SYMBOLS:
        bars = read_history(tmp_path / 'history' / f'{symbol}.csv')
        assert bars[-1].trading_date == date(2026, 10, 22)
        assert date(2026, 10, 23) not in {bar.trading_date for bar in bars}
