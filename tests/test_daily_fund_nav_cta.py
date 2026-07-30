from datetime import date, timedelta
import json

from onecool_os.market.fund_alpha import FUND_WATCHLIST, FundNav
from scripts.update_fund_nav_cta import update


class FakeNavClient:
    def __init__(self, end: date) -> None:
        self.end = end
        self.calls: list[str] = []

    def fetch_history(self, fund_code: str) -> list[FundNav]:
        self.calls.append(fund_code)
        return [
            FundNav(
                nav_date=self.end - timedelta(days=399 - index),
                nav=100.0 + index,
            )
            for index in range(400)
        ]


def test_daily_update_fetches_each_fund_once_and_only_writes_nav_cta(tmp_path) -> None:
    etf_dir = tmp_path / "data" / "market" / "etf_cta"
    etf_dir.mkdir(parents=True)
    etf_dir.joinpath("cta_latest.json").write_text(
        json.dumps(
            {
                "results": [
                    {"symbol": benchmark, "cta": "HOLD"}
                    for _, benchmark, _ in FUND_WATCHLIST.values()
                ]
                + [
                    {"symbol": "GLD", "cta": "HOLD"},
                    {"symbol": "WTI", "cta": "HOLD"},
                ]
            }
        ),
        encoding="utf-8",
    )
    client = FakeNavClient(date(2026, 7, 30))

    payload = update(
        tmp_path,
        client=client,
        generated_at="2026-07-30T01:30:00+00:00",
    )

    assert client.calls == list(FUND_WATCHLIST)
    assert payload["update_mode"] == "DAILY_NAV_CTA_ONLY"
    assert len(payload["results"]) == 7
    assert {
        item["fund_nav_as_of"] for item in payload["results"]
    } == {"2026-07-30"}
    fund_dir = tmp_path / "data" / "market" / "fund_nav"
    assert fund_dir.joinpath("fund_cta_latest.json").exists()
    assert not fund_dir.joinpath("alpha_latest.json").exists()
    assert not fund_dir.joinpath("peer_ranking_latest.json").exists()
