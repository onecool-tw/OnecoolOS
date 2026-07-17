from datetime import date, timedelta

import pytest

from onecool_os.market.etf_cta import DailyBar, ETFCTAError
from onecool_os.market.fund_alpha import (
    AnueFundClient,
    FundNav,
    calculate_relative_alpha,
    completed_month_snapshots,
    consecutive_status,
    merge_nav_history,
    parse_anue_nav_history,
)


def fund_nav(day: date, value: float) -> FundNav:
    return FundNav(nav_date=day, nav=value)


def etf_bar(day: date, value: float) -> DailyBar:
    return DailyBar(
        trading_date=day,
        open=value,
        high=value,
        low=value,
        close=value,
        volume=1,
        adjusted_close=value,
    )


def test_parse_anue_nav_history() -> None:
    payload = {
        "data": {
            "fundID": "A10124",
            "hearder": {"ccy": "美元"},
            "navHIS": [
                {"navDate": "2026-07-15T00:00:00", "nav": "12.34"}
            ],
        }
    }

    history = parse_anue_nav_history(payload, "A10124")

    assert history == [fund_nav(date(2026, 7, 15), 12.34)]


def test_client_uses_public_navhis_endpoint() -> None:
    urls = []
    response = b'{"data":{"fundID":"A10124","hearder":{"ccy":"USD"},"navHIS":[{"navDate":"2026-07-15T00:00:00","nav":"1"}]}}'
    client = AnueFundClient(request=lambda url: urls.append(url) or response)

    client.fetch_history("A10124")

    assert len(urls) == 1
    assert "fundDetailEnum=NavHIS" in urls[0]
    assert "FundID=A10124" in urls[0]


def test_parse_rejects_wrong_fund() -> None:
    with pytest.raises(ETFCTAError, match="Invalid Anue NAV"):
        parse_anue_nav_history({"data": {"fundID": "wrong"}}, "A10124")


def test_merge_nav_history_replaces_same_date() -> None:
    day = date(2026, 7, 15)

    merged = merge_nav_history([fund_nav(day, 1)], [fund_nav(day, 2)])

    assert merged == [fund_nav(day, 2)]


def test_relative_alpha_uses_identical_dates() -> None:
    start = date(2025, 7, 15)
    end = date(2026, 7, 15)
    funds = [fund_nav(start, 100), fund_nav(end, 130)]
    etfs = [etf_bar(start, 100), etf_bar(end, 120)]

    result = calculate_relative_alpha("A10124", funds, etfs)

    assert result.start_date == "2025-07-15"
    assert result.end_date == "2026-07-15"
    assert result.fund_return_1y == pytest.approx(30)
    assert result.benchmark_return_1y == pytest.approx(20)
    assert result.alpha_percentage_points == pytest.approx(10)
    assert result.status == "positive"


def test_relative_alpha_unknown_when_dates_do_not_overlap() -> None:
    result = calculate_relative_alpha(
        "A10124",
        [fund_nav(date(2026, 7, 15), 100)],
        [etf_bar(date(2026, 7, 16), 100)],
    )

    assert result.status == "unknown"
    assert result.alpha_percentage_points is None


def test_relative_alpha_allows_nearby_common_start() -> None:
    end = date(2026, 7, 15)
    start = date(2025, 7, 11)

    result = calculate_relative_alpha(
        "A10124",
        [fund_nav(start, 100), fund_nav(end, 110)],
        [etf_bar(start, 100), etf_bar(end, 105)],
    )

    assert result.start_date == "2025-07-11"
    assert result.alpha_percentage_points == pytest.approx(5)


def test_completed_months_and_consecutive_status() -> None:
    fund_history = []
    etf_history = []
    for end, fund_end, etf_end in [
        (date(2026, 4, 30), 120, 110),
        (date(2026, 5, 29), 130, 110),
        (date(2026, 6, 30), 140, 120),
    ]:
        start = end.replace(year=end.year - 1)
        fund_history.extend([fund_nav(start, 100), fund_nav(end, fund_end)])
        etf_history.extend([etf_bar(start, 100), etf_bar(end, etf_end)])

    snapshots = completed_month_snapshots(
        "A10124",
        fund_history,
        etf_history,
        as_of=date(2026, 7, 15),
    )

    assert [item.end_date for item in snapshots] == [
        "2026-04-30",
        "2026-05-29",
        "2026-06-30",
    ]
    assert consecutive_status(snapshots) == "positive_3_months"


def test_start_gap_over_ten_days_is_unknown() -> None:
    end = date(2026, 7, 15)
    old = date(2025, 6, 30)
    result = calculate_relative_alpha(
        "A10124",
        [fund_nav(old, 100), fund_nav(end, 110)],
        [etf_bar(old, 100), etf_bar(end, 105)],
    )

    assert result.status == "unknown"
