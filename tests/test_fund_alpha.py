from datetime import date, timedelta

import pytest

from onecool_os.market.etf_cta import DailyBar, ETFCTAError
from onecool_os.market.fund_alpha import (
    FUND_WATCHLIST,
    AnueFundClient,
    FundNav,
    alpha_payload,
    calculate_excess_return,
    calculate_period_excess_return,
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


def test_excess_return_uses_identical_dates() -> None:
    start = date(2025, 7, 15)
    end = date(2026, 7, 15)
    funds = [fund_nav(start, 100), fund_nav(end, 130)]
    etfs = [etf_bar(start, 100), etf_bar(end, 120)]

    result = calculate_excess_return("A10124", funds, etfs)

    assert result.start_date == "2025-07-15"
    assert result.end_date == "2026-07-15"
    assert result.fund_return_1y == pytest.approx(30)
    assert result.proxy_return_1y == pytest.approx(20)
    assert result.excess_return_percentage_points == pytest.approx(10)
    assert result.status == "positive"


def test_three_and_six_month_excess_returns_use_identical_dates() -> None:
    end = date(2026, 7, 17)
    three_month_start = date(2026, 4, 17)
    six_month_start = date(2026, 1, 16)
    funds = [
        fund_nav(six_month_start, 100),
        fund_nav(three_month_start, 110),
        fund_nav(end, 132),
    ]
    etfs = [
        etf_bar(six_month_start, 100),
        etf_bar(three_month_start, 105),
        etf_bar(end, 126),
    ]

    three_month = calculate_period_excess_return(
        "A10124", funds, etfs, months=3, period="3m"
    )
    six_month = calculate_period_excess_return(
        "A10124", funds, etfs, months=6, period="6m"
    )

    assert three_month.start_date == "2026-04-17"
    assert three_month.end_date == "2026-07-17"
    assert three_month.fund_return == pytest.approx(20)
    assert three_month.proxy_return == pytest.approx(20)
    assert three_month.status == "flat"
    assert six_month.start_date == "2026-01-16"
    assert six_month.fund_return == pytest.approx(32)
    assert six_month.proxy_return == pytest.approx(26)
    assert six_month.excess_return_percentage_points == pytest.approx(6)


def test_period_return_is_unknown_when_history_is_too_short() -> None:
    end = date(2026, 7, 17)
    result = calculate_period_excess_return(
        "A10124",
        [fund_nav(date(2026, 5, 1), 100), fund_nav(end, 110)],
        [etf_bar(date(2026, 5, 1), 100), etf_bar(end, 105)],
        months=3,
        period="3m",
    )

    assert result.status == "unknown"
    assert result.excess_return_percentage_points is None


def test_excess_return_unknown_when_dates_do_not_overlap() -> None:
    result = calculate_excess_return(
        "A10124",
        [fund_nav(date(2026, 7, 15), 100)],
        [etf_bar(date(2026, 7, 16), 100)],
    )

    assert result.status == "unknown"
    assert result.excess_return_percentage_points is None


def test_excess_return_allows_nearby_common_start() -> None:
    end = date(2026, 7, 15)
    start = date(2025, 7, 11)

    result = calculate_excess_return(
        "A10124",
        [fund_nav(start, 100), fund_nav(end, 110)],
        [etf_bar(start, 100), etf_bar(end, 105)],
    )

    assert result.start_date == "2025-07-11"
    assert result.excess_return_percentage_points == pytest.approx(5)


def test_completed_months_and_consecutive_status() -> None:
    fund_history = []
    etf_history = []
    for end, fund_end, etf_end in [
        (date(2026, 8, 31), 120, 110),
        (date(2026, 9, 30), 130, 110),
        (date(2026, 10, 30), 140, 120),
    ]:
        start = end.replace(year=end.year - 1)
        fund_history.extend([fund_nav(start, 100), fund_nav(end, fund_end)])
        etf_history.extend([etf_bar(start, 100), etf_bar(end, etf_end)])

    snapshots = completed_month_snapshots(
        "A10124",
        fund_history,
        etf_history,
        as_of=date(2026, 11, 15),
    )

    assert [item.end_date for item in snapshots] == [
        "2026-08-31",
        "2026-09-30",
        "2026-10-30",
    ]
    assert consecutive_status(snapshots) == "positive_3_months"


def test_changed_proxy_has_no_pre_cutover_months() -> None:
    snapshots = completed_month_snapshots(
        "A10124",
        [fund_nav(date(2025, 6, 30), 100), fund_nav(date(2026, 6, 30), 110)],
        [etf_bar(date(2025, 6, 30), 100), etf_bar(date(2026, 6, 30), 105)],
        as_of=date(2026, 7, 20),
    )

    assert snapshots == []
    assert consecutive_status(snapshots) == "insufficient_data"


def test_start_gap_over_ten_days_is_unknown() -> None:
    end = date(2026, 7, 15)
    old = date(2025, 6, 30)
    result = calculate_excess_return(
        "A10124",
        [fund_nav(old, 100), fund_nav(end, 110)],
        [etf_bar(old, 100), etf_bar(end, 105)],
    )

    assert result.status == "unknown"


def test_watchlist_uses_simplified_cta_proxies() -> None:
    assert {code: values[1] for code, values in FUND_WATCHLIST.items()} == {
        "A10124": "AIQ",
        "A16075": "SMIN",
        "B23554": "RING",
        "B15080": "IBB",
        "B09007": "PICK",
        "B16019": "RXI",
        "B23070": "IXC",
    }


def test_payload_labels_raw_difference_as_excess_return() -> None:
    funds = [
        fund_nav(date(2025, 7, 15), 100),
        fund_nav(date(2026, 4, 15), 105),
        fund_nav(date(2026, 7, 15), 110),
    ]
    etfs = [
        etf_bar(date(2025, 7, 15), 100),
        etf_bar(date(2026, 4, 15), 102),
        etf_bar(date(2026, 7, 15), 105),
    ]
    result = calculate_excess_return(
        "A16075", funds, etfs
    )

    period = calculate_period_excess_return(
        "A16075", funds, etfs, months=3, period="3m"
    )
    payload = alpha_payload(
        [result], {"A16075": []}, {"A16075": {"3m": period}}
    )

    assert payload["schema_version"] == "2.1"
    assert payload["metric"] == "Onecool Excess Return"
    assert "alpha" not in payload["definition"].lower()
    assert payload["results"][0]["proxy_etf"] == "SMIN"
    assert payload["periods"] == ["3m", "6m", "1y"]
    assert payload["results"][0]["period_returns"]["3m"]["period"] == "3m"
    assert payload["results"][0]["fund_return_1y"] == result.fund_return_1y
