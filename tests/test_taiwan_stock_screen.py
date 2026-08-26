import pytest

from onecool_os.market.taiwan_stock_screen import build_taiwan_stock_screen_payload


def _inputs(count=12):
    prices = []
    valuations = []
    revenues = []
    income = []
    for index in range(count):
        code = str(2300 + index)
        industry = "電子" if index < 7 else "金融"
        prices.append({
            "Date": "1150825", "Code": code, "Name": f"公司{index}",
            "TradeValue": str((count - index) * 1_000_000),
            "ClosingPrice": str(100 + index),
        })
        valuations.append({
            "Date": "1150825", "Code": code,
            "PEratio": str(8 + index), "PBratio": str(1 + index / 10),
        })
        revenues.append({
            "資料年月": "11507", "公司代號": code,
            "公司名稱": f"公司{index}", "產業別": industry,
            "營業收入-去年同月增減(%)": str(60 - index),
            "累計營業收入-前期比較增減(%)": str(50 - index),
        })
        income.append({
            "年度": "115", "季別": "2", "公司代號": code,
            "基本每股盈餘（元）": str(10 - index / 2),
        })
    return prices, valuations, revenues, income


def test_screen_builds_broad_ranked_universe_and_limits_industries():
    payload = build_taiwan_stock_screen_payload(
        *_inputs(), universe_size=10, top_n=5, industry_limit=2
    )

    assert payload["data_status"] == "READY"
    assert payload["expected_as_of"] == "2026-08-25"
    assert payload["universe_size"] == 10
    assert len(payload["universe"]) == 10
    assert payload["universe"][0]["provider_symbol"].endswith(".TW")
    assert payload["validated_count"] == 10
    assert len(payload["top5"]) <= 4  # only two industries, max two each
    assert all(item["score"] >= 80 for item in payload["top5"])
    assert all(count <= 2 for count in _industry_counts(payload["top5"]).values())
    assert payload["data_quality"]["estimated_values_used"] is False


def test_screen_excludes_missing_values_instead_of_estimating():
    prices, valuations, revenues, income = _inputs()
    valuations = [row for row in valuations if row["Code"] != "2300"]

    payload = build_taiwan_stock_screen_payload(
        prices, valuations, revenues, income, universe_size=10
    )

    excluded = next(item for item in payload["exclusions"] if item["symbol"] == "2300")
    assert "valuation" in excluded["reason"]
    assert all(item["symbol"] != "2300" for item in payload["top5"])


def test_screen_rejects_mixed_price_and_valuation_cutoffs():
    prices, valuations, revenues, income = _inputs()
    valuations[0]["Date"] = "1150824"

    with pytest.raises(ValueError, match="one common value"):
        build_taiwan_stock_screen_payload(prices, valuations, revenues, income)


def test_screen_detects_duplicate_symbols():
    prices, valuations, revenues, income = _inputs()
    revenues.append(dict(revenues[0]))

    payload = build_taiwan_stock_screen_payload(
        prices, valuations, revenues, income, universe_size=10
    )

    assert "2300" in payload["data_quality"]["duplicate_codes"]
    assert all(item["symbol"] != "2300" for item in payload["top5"])


def test_user_interest_does_not_change_fixed_scores_or_rankings():
    inputs = _inputs()
    first = build_taiwan_stock_screen_payload(
        *inputs, universe_size=10, top_n=5, industry_limit=2
    )
    second = build_taiwan_stock_screen_payload(
        *inputs, universe_size=10, top_n=5, industry_limit=2
    )

    assert first["top5"] == second["top5"]
    assert [item["score"] for item in first["rankings"]] == [
        item["score"] for item in second["rankings"]
    ]


def test_etf_like_code_without_monthly_revenue_is_not_in_universe():
    prices, valuations, revenues, income = _inputs()
    prices.append({
        "Date": "1150825", "Code": "0050", "Name": "ETF",
        "TradeValue": "999999999999", "ClosingPrice": "200",
    })
    valuations.append({
        "Date": "1150825", "Code": "0050", "PEratio": "10", "PBratio": "1",
    })

    payload = build_taiwan_stock_screen_payload(
        prices, valuations, revenues, income, universe_size=10
    )

    assert all(item["symbol"] != "0050" for item in payload["rankings"])


def _industry_counts(items):
    result = {}
    for item in items:
        result[item["industry"]] = result.get(item["industry"], 0) + 1
    return result
