from pathlib import Path

from onecool_os.market.fund_intelligence import load_master_prompt


def test_concise_freeze_prompt_contains_finalized_contract() -> None:
    prompt = (
        Path(__file__).parents[1]
        / "config"
        / "fund_intelligence_master_prompt.md"
    ).read_text(encoding="utf-8")

    sections = [
        "Market Dashboard",
        "Fund CTA Dashboard",
        "Onecool Excess Return",
        "US Sector Rotation Monitor",
        "AI Revolution Monitor",
        "Global Market Rotation Radar",
        "Delta Summary",
        "Portfolio Decision",
        "Macro Intelligence",
        "OFAI Decision Synthesis",
        "Data Analyst Validation",
    ]
    positions = [prompt.index(f"{index}. {name}") for index, name in enumerate(sections, 1)]
    assert positions == sorted(positions)
    assert "基金 | Proxy ETF | Fund CTA | ETF CTA | Confirm | Action" in prompt
    assert "基金 | Proxy | 3M | 6M | 1Y | Overall" in prompt
    assert "不加入 1M" in prompt
    assert "SMH 不再使用" in prompt
    assert "不輸出 Bottom、SPY、12W、均線、交叉、成交量或候選清單" in prompt
    assert "印度、世界礦業、環球消費維持續扣" in prompt
    assert "Tesla 正式排除" in prompt
    assert "完整覆蓋固定為六家公司 `6／6`" in prompt
    assert prompt.index("| DXY |") < prompt.index("| US 30Y |") < prompt.index("| BTC |")
    assert "BTC週線為UTC週一至週日" in prompt
    assert "不得改變任何基金CTA" in prompt
    assert "Market Regime（總經情境）" in prompt
    assert "Liquidity｜Market-implied Growth｜Inflation｜Risk Appetite｜Primary Scenario" in prompt
    assert "A LIQUIDITY RISK-ON" in prompt
    assert "D DEFENSIVE STRESS" in prompt
    assert "VIX必須反向解讀" in prompt
    assert "總經情境只負責解釋市場環境" in prompt
    assert "不得推翻基金" in prompt


def test_master_prompt_loader_exposes_version_and_stable_hash() -> None:
    root = Path(__file__).parents[1]

    loaded = load_master_prompt(root)

    assert loaded["version"] == "v1.2 Freeze"
    assert len(loaded["sha256"]) == 64
    assert loaded["content"].startswith("# Onecool Fund Intelligence v1.2")
