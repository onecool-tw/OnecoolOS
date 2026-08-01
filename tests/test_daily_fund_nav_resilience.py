from datetime import date, timedelta

import pytest

from onecool_os.market.etf_cta import ETFCTAError
from onecool_os.market.fund_alpha import FUND_WATCHLIST, FundNav, write_nav_history
from scripts.update_fund_nav_cta import update


class StubClient:
    def __init__(self, failures: set[str]) -> None:
        self.failures = failures

    def fetch_history(self, fund_code: str) -> list[FundNav]:
        if fund_code in self.failures:
            raise RuntimeError("provider unavailable")
        return [FundNav(nav_date=date(2026, 8, 1), nav=120.0)]


def seed_histories(root) -> None:
    start = date(2025, 6, 1)
    history = [
        FundNav(nav_date=start + timedelta(days=index), nav=100 + index / 100)
        for index in range(420)
    ]
    for fund_code in FUND_WATCHLIST:
        write_nav_history(
            root / "data" / "market" / "fund_nav" / "history" / f"{fund_code}.csv",
            history,
        )


def test_one_provider_failure_does_not_block_other_funds(tmp_path) -> None:
    seed_histories(tmp_path)

    payload = update(
        tmp_path,
        client=StubClient({"A10124"}),
        generated_at="2026-08-01T00:30:00+00:00",
    )

    assert payload["nav_refresh"]["status"] == "PARTIAL"
    assert payload["nav_refresh"]["successful_provider_reads"] == 6
    assert payload["nav_refresh"]["failed_provider_reads"] == 1
    assert payload["nav_refresh"]["funds"]["A10124"]["status"] == "FALLBACK_EXISTING"
    assert payload["nav_refresh"]["funds"]["A16075"]["status"] == "UPDATED"
    by_code = {item["fund_code"]: item for item in payload["results"]}
    assert by_code["A10124"]["fund_nav_as_of"] == "2026-07-25"
    assert by_code["A16075"]["fund_nav_as_of"] == "2026-08-01"


def test_all_provider_failures_abort_without_publishing_cache(tmp_path) -> None:
    seed_histories(tmp_path)

    with pytest.raises(ETFCTAError, match="All seven"):
        update(tmp_path, client=StubClient(set(FUND_WATCHLIST)))

    assert not (
        tmp_path / "data" / "market" / "fund_nav" / "fund_cta_latest.json"
    ).exists()
