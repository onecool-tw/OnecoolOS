from onecool_os.market.stockq_rotation import (
    build_rotation_radar,
    screen_funds,
    screen_markets,
)


def ranking(period: str, rows: list[tuple[str, str, str]]) -> str:
    body = "".join(
        f"<tr><td><a href='{href}'>{name}</a></td><td>{value}</td></tr>"
        for name, value, href in rows
    )
    return (
        f"<table><tr><td>{period}</td><td>{period}</td></tr>"
        f"<tr><td>股市</td><td>漲跌幅</td></tr>{body}</table>"
    )


MARKET_HTML = "".join(
    [
        ranking("一個月", [("泰國", "6.5%", "/index/SET.php"), ("新加坡", "5%", "/index/SG.php")]),
        ranking("三個月", [("泰國", "12%", "/index/SET.php"), ("半導體", "10%", "/index/SOX.php")]),
        ranking("六個月", [("泰國", "25%", "/index/SET.php"), ("半導體", "20%", "/index/SOX.php")]),
    ]
)

FUND_HTML = """
<table>
<tr><td>名稱</td><td>一日</td><td>一週</td><td>一個月</td><td>三個月</td><td>六個月</td><td>一年</td><td>今年以來</td></tr>
<tr><td>泰國指數</td><td>1%</td><td>2%</td><td>6%</td><td>12%</td><td>25%</td><td>35%</td><td>20%</td></tr>
<tr><td>基金甲/美元</td><td>1%</td><td>2%</td><td>5%</td><td>10%</td><td>20%</td><td>30%</td><td>18%</td></tr>
<tr><td>基金乙/美元</td><td>1%</td><td>2%</td><td>6%</td><td>8%</td><td>18%</td><td>28%</td><td>16%</td></tr>
<tr><td>基金丙/美元</td><td>1%</td><td>2%</td><td>-1%</td><td>20%</td><td>30%</td><td>40%</td><td>22%</td></tr>
</table>
"""


def test_stage1_requires_three_periods_to_pass() -> None:
    markets = {item.market: item for item in screen_markets(MARKET_HTML)}
    assert markets["泰國"].stage1 == "PASS"
    assert markets["半導體"].stage1 == "WATCH"
    assert "新加坡" not in markets


def test_stage2_requires_all_positive_periods() -> None:
    funds = screen_funds(FUND_HTML)
    assert [item.name for item in funds] == ["基金甲/美元", "基金乙/美元"]


def test_payload_keeps_watch_and_opportunity_only_policy() -> None:
    payload = build_rotation_radar(MARKET_HTML, lambda _: FUND_HTML, as_of="07/23")
    assert payload["passed_markets"][0]["market"] == "泰國"
    assert payload["passed_markets"][0]["stage2"] == "PASS"
    assert payload["rules"]["decision_use"] == "OPPORTUNITY_RADAR_ONLY"
    assert payload["watch_markets"][0]["market"] == "半導體"
