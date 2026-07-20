from onecool_os.market.peer_ranking import (
    CnyesPeerRankingClient,
    parse_cnyes_peer_ranking,
    ranking_band,
    refresh_peer_rankings,
)


HTML = """
<html><body>
<h1>群益印度中小基金-美元</h1>
<div>股票-印度美元同組基金排行</div>
<div>績效表現 更新日期：2026/07/17</div>
<div>1月 3月 6月 今年以來 1年 3年 5年 10年</div>
<div>基金績效 1% 2% 3% 4% 5% 6% 7% 8%</div>
<div>基準指數 0% 1% 2% 3% 4% 5% 6% 7%</div>
<div>同組平均 -1.1% 7.01% -6.43% -6.72% -2.89% 22.5% 35.14% 86.14%</div>
<div>同組排名 贏過N%基金 6% 63% 82% 86% 74% 89% 91% 95%</div>
<div>歷史淨值</div>
</body></html>
"""


def test_parse_cnyes_published_peer_values() -> None:
    result = parse_cnyes_peer_ranking(
        HTML, fund_code="A16075", source_url="https://example.test"
    )

    assert result.category == "股票-印度美元"
    assert result.as_of == "2026-07-17"
    assert result.percentile_3m == 63
    assert result.percentile_6m == 82
    assert result.percentile_1y == 74
    assert result.peer_average_3m == 7.01
    assert result.peer_average_6m == -6.43
    assert result.peer_average_1y == -2.89
    assert result.data_quality == "VALID"
    assert result.ranking_band == "ABOVE_AVERAGE"


def test_refresh_preserves_last_success_as_stale() -> None:
    previous = {
        "results": [
            {
                "fund_code": "A16075",
                "fund_name": "群益印度中小基金-美元",
                "source": "cnyes_morningstar_published",
                "source_url": "https://example.test",
                "category": "股票-印度美元",
                "as_of": "2026-07-17",
                "percentile_3m": 63,
                "percentile_6m": 82,
                "percentile_1y": 74,
                "peer_average_3m": 7.01,
                "peer_average_6m": -6.43,
                "peer_average_1y": -2.89,
                "data_quality": "VALID",
                "ranking_band": "ABOVE_AVERAGE",
                "reason": "ok",
            }
        ]
    }
    client = CnyesPeerRankingClient(request=lambda _: (_ for _ in ()).throw(OSError()))

    payload = refresh_peer_rankings(client, previous)
    item = next(x for x in payload["results"] if x["fund_code"] == "A16075")

    assert item["data_quality"] == "STALE"
    assert item["percentile_1y"] == 74
    assert payload["source_policy"]["funddj"] == "cross_check_only_not_mixed"


def test_published_ranking_survives_missing_category_label() -> None:
    result = parse_cnyes_peer_ranking(
        HTML.replace("股票-印度美元同組基金排行", ""),
        fund_code="A16075",
        source_url="https://example.test",
    )

    assert result.category is None
    assert result.percentile_1y == 74
    assert result.data_quality == "PARTIAL"


def test_missing_source_is_unknown_and_never_imputed() -> None:
    client = CnyesPeerRankingClient(request=lambda _: b"<html>changed</html>")

    payload = refresh_peer_rankings(client)

    assert len(payload["results"]) == 7
    assert {item["data_quality"] for item in payload["results"]} == {"UNKNOWN"}
    assert all(item["percentile_1y"] is None for item in payload["results"])


def test_ranking_bands_use_percentile_won() -> None:
    assert ranking_band(75) == "LEADING"
    assert ranking_band(50) == "ABOVE_AVERAGE"
    assert ranking_band(25) == "BELOW_AVERAGE"
    assert ranking_band(24) == "WEAK"
    assert ranking_band(None) == "UNKNOWN"
