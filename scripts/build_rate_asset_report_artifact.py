"""Build the bounded Data Analytics artifact for the US-rate backtest report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SHORT_NAMES = {
    "A10124": "富邦AI多重資產",
    "A16075": "群益印度中小",
    "B23554": "施羅德環球黃金",
    "B15080": "富蘭克林生技",
    "B09007": "貝萊德世界礦業",
    "B16019": "景順環球消費",
    "B23070": "施羅德環球能源",
    "0050": "台灣50",
    "BTC": "Bitcoin",
}
HELD_FUNDS = {"A10124", "A16075", "B23554", "B15080", "B09007", "B16019", "B23070"}
KEY_CROSS_ASSETS = {"SPY", "QQQ", "IWM", "0050", "SHY", "IEF", "TLT", "GLD", "DXY", "WTI", "VNQ", "BTC"}


def state(asset: dict, rate: str, name: str) -> dict:
    return next(
        row
        for row in asset["state_results"]
        if row["rate_state_id"] == rate and row["state"] == name
    )


def row_for(asset: dict) -> dict:
    rising = state(asset, "DFF", "RISING")["forward"]["12"]
    falling = state(asset, "DFF", "FALLING")["forward"]["12"]
    rising_onset = state(asset, "DFF", "RISING")["state_onsets"]["12"]
    falling_onset = state(asset, "DFF", "FALLING")["state_onsets"]["12"]
    regression = asset["monthly_rate_change_regressions"]
    return {
        "asset_id": asset["asset_id"],
        "asset": SHORT_NAMES.get(asset["asset_id"], asset["asset_id"]),
        "asset_name": asset["name"],
        "asset_class": asset["asset_class"],
        "start": asset["start"],
        "end": asset["end"],
        "months": asset["monthly_observations"],
        "fed_rising_median_12m": rising["median_return_pct"],
        "fed_rising_win_12m": rising["win_rate_pct"],
        "fed_rising_n": rising["sample_months"],
        "fed_falling_median_12m": falling["median_return_pct"],
        "fed_falling_win_12m": falling["win_rate_pct"],
        "fed_falling_n": falling["sample_months"],
        "fed_rising_onset_median_12m": rising_onset["median_return_pct"],
        "fed_rising_onset_n": rising_onset["sample_months"],
        "fed_falling_onset_median_12m": falling_onset["median_return_pct"],
        "fed_falling_onset_n": falling_onset["sample_months"],
        "beta_2y": regression["DGS2"]["return_per_100bp_pct"],
        "r2_2y": regression["DGS2"]["r_squared"],
        "beta_10y": regression["DGS10"]["return_per_100bp_pct"],
        "r2_10y": regression["DGS10"]["r_squared"],
        "beta_30y": regression["DGS30"]["return_per_100bp_pct"],
        "r2_30y": regression["DGS30"]["r_squared"],
    }


def source() -> dict:
    return {
        "id": "rate_backtest",
        "label": "Onecool US Rate x Asset Backtest",
        "path": "data/market/rate_asset_backtest/backtest_latest.json",
        "query": {
            "language": "python",
            "id": "scripts/update_rate_asset_backtest.py",
            "description": "Month-end rate-state backtest using FRED rates, locally adjusted Yahoo prices, and public fund NAV histories.",
            "tables_used": [
                "FRED DFF, DGS2, DGS10, DGS30, T10Y2Y",
                "Yahoo chart raw close/dividend/split histories",
                "data/market/fund_nav/history/*.csv",
            ],
            "filters": [
                "Only completed calendar months through July 2026",
                "Three-month rate change >= +25bp is RISING and <= -25bp is FALLING",
                "30Y observations in the official 2002-02-19 to 2006-02-08 discontinuation interval excluded",
                "No interpolation across missing rate observations",
            ],
            "metric_definitions": [
                "12M median = median adjusted return over the following 12 completed months for every month in the stated rate regime",
                "Rate beta = regression slope of monthly asset return versus monthly yield change, shown as asset return percentage points per +100bp",
                "R-squared = share of monthly return variation described by the single rate-change regression; it is not causal proof",
                "Onset sample = forward return counted once when a rate state begins",
            ],
        },
    }


def widget_source(dataset: str) -> dict:
    """Describe the bounded artifact query used by a chart or table."""

    return {
        "id": "rate_backtest",
        "label": "Onecool US Rate x Asset Backtest",
        "path": "data/market/rate_asset_backtest/backtest_latest.json",
        "query": {
            "language": "sql",
            "sql": f"SELECT * FROM {dataset}",
            "description": f"Read the validated {dataset} rows from the bounded report snapshot.",
            "tables_used": [dataset],
        },
    }


def build(payload: dict) -> dict:
    rows = [row_for(asset) for asset in payload["assets"]]
    held = [row for row in rows if row["asset_id"] in HELD_FUNDS]
    cross = [row for row in rows if row["asset_id"] in KEY_CROSS_ASSETS]

    title = "Onecool 美國利率與各資產回測"
    source_item = source()
    manifest = {
        "version": 1,
        "surface": "report",
        "title": title,
        "description": "政策利率、2年、10年、30年殖利率與殖利率曲線對26項資產的歷史影響。",
        "generatedAt": payload["generated_at"],
        "sources": [source_item],
        "charts": [
            {
                "id": "cross_asset_beta",
                "title": "大類資產的長債殖利率敏感度",
                "subtitle": "每月殖利率上升100bp時的估計單月報酬變化；負值代表利率上升不利。",
                "type": "bar",
                "dataset": "cross_assets",
                "sourceId": "rate_backtest",
                "source": widget_source("cross_assets"),
                "valueFormat": "number",
                "options": {"orientation": "horizontal", "grouping": "grouped"},
                "encodings": {
                    "x": {"field": "asset", "type": "nominal", "label": "資產"},
                    "y": {"fields": ["beta_10y", "beta_30y"], "type": "quantitative", "label": "報酬變化（百分點）"},
                    "tooltip": [
                        {"field": "r2_10y", "type": "quantitative", "label": "10Y R²"},
                        {"field": "r2_30y", "type": "quantitative", "label": "30Y R²"},
                        {"field": "start", "type": "nominal", "label": "樣本起點"},
                    ],
                },
            },
            {
                "id": "held_fund_beta",
                "title": "七檔基金的長債殖利率敏感度",
                "subtitle": "黃金與AI基金對長債殖利率上升較敏感；能源方向相反。",
                "type": "bar",
                "dataset": "held_funds",
                "sourceId": "rate_backtest",
                "source": widget_source("held_funds"),
                "valueFormat": "number",
                "options": {"orientation": "horizontal", "grouping": "grouped"},
                "encodings": {
                    "x": {"field": "asset", "type": "nominal", "label": "基金"},
                    "y": {"fields": ["beta_10y", "beta_30y"], "type": "quantitative", "label": "報酬變化（百分點）"},
                    "tooltip": [
                        {"field": "r2_10y", "type": "quantitative", "label": "10Y R²"},
                        {"field": "months", "type": "quantitative", "label": "月數"},
                    ],
                },
            },
            {
                "id": "fed_regime_forward",
                "title": "Fed利率方向後12個月報酬中位數",
                "subtitle": "降息月份往往伴隨壓力；不能把降息直接視為所有風險資產利多。",
                "type": "bar",
                "dataset": "cross_assets",
                "sourceId": "rate_backtest",
                "source": widget_source("cross_assets"),
                "valueFormat": "number",
                "options": {"orientation": "horizontal", "grouping": "grouped"},
                "encodings": {
                    "x": {"field": "asset", "type": "nominal", "label": "資產"},
                    "y": {"fields": ["fed_rising_median_12m", "fed_falling_median_12m"], "type": "quantitative", "label": "12個月報酬中位數（%）"},
                    "tooltip": [
                        {"field": "fed_rising_n", "type": "quantitative", "label": "升息樣本月"},
                        {"field": "fed_falling_n", "type": "quantitative", "label": "降息樣本月"},
                    ],
                },
            },
        ],
        "tables": [
            {
                "id": "held_fund_table",
                "title": "七檔基金回測摘要",
                "subtitle": "完整月度資料；12M為後續12個月報酬中位數。",
                "dataset": "held_funds",
                "sourceId": "rate_backtest",
                "source": widget_source("held_funds"),
                "defaultSort": {"field": "beta_10y", "direction": "asc"},
                "columns": [
                    {"field": "asset", "label": "基金", "type": "text"},
                    {"field": "start", "label": "起點", "type": "date"},
                    {"field": "fed_rising_median_12m", "label": "Fed↑後12M", "format": "number", "unit": "%"},
                    {"field": "fed_falling_median_12m", "label": "Fed↓後12M", "format": "number", "unit": "%"},
                    {"field": "beta_10y", "label": "10Y +100bp", "format": "number", "unit": "%"},
                    {"field": "r2_10y", "label": "10Y R²", "format": "number"},
                    {"field": "beta_30y", "label": "30Y +100bp", "format": "number", "unit": "%"},
                ],
            },
            {
                "id": "all_asset_table",
                "title": "26項資產完整摘要",
                "subtitle": "依10年期殖利率敏感度由低至高排序。",
                "dataset": "all_assets",
                "sourceId": "rate_backtest",
                "source": widget_source("all_assets"),
                "defaultSort": {"field": "beta_10y", "direction": "asc"},
                "columns": [
                    {"field": "asset", "label": "資產", "type": "text"},
                    {"field": "asset_class", "label": "類別", "type": "text"},
                    {"field": "start", "label": "起點", "type": "date"},
                    {"field": "fed_rising_median_12m", "label": "Fed↑後12M", "format": "number", "unit": "%"},
                    {"field": "fed_falling_median_12m", "label": "Fed↓後12M", "format": "number", "unit": "%"},
                    {"field": "beta_2y", "label": "2Y +100bp", "format": "number", "unit": "%"},
                    {"field": "beta_10y", "label": "10Y +100bp", "format": "number", "unit": "%"},
                    {"field": "beta_30y", "label": "30Y +100bp", "format": "number", "unit": "%"},
                    {"field": "r2_10y", "label": "10Y R²", "format": "number"},
                ],
            },
        ],
        "blocks": [
            {"id": "title", "type": "markdown", "body": f"# {title}"},
            {
                "id": "executive_summary",
                "type": "markdown",
                "sourceId": "rate_backtest",
                "body": "## Executive Summary\n\n- **利率只能當背景，不能取代CTA。** 除了美國公債，單一利率變化對大多數風險資產月報酬的解釋力很低。\n- **長債是最乾淨的利率曝險。** 10年殖利率每上升100bp，SHY、IEF、TLT的估計單月報酬分別約為-1.2%、-7.4%、-14.2%，R²約0.55、0.98、0.87。\n- **你的基金中，黃金與AI對長債利率最敏感。** 10年殖利率每上升100bp，施羅德黃金約-12.8%、富邦AI約-6.3%；施羅德能源約+4.9%，但除黃金外解釋力仍偏低。\n- **降息不是普遍Risk-on。** Fed利率下降月份之後，黃金與長債表現較穩；QQQ、VNQ與生技的12個月中位數沒有同步受益，顯示降息原因比降息本身更重要。",
            },
            {
                "id": "duration_finding",
                "type": "markdown",
                "sourceId": "rate_backtest",
                "body": "## 真正穩定的是債券久期，不是所有資產的利率方向\n\nIEF與TLT對10年、30年殖利率的負敏感度最強，且R²遠高於股票、商品與Bitcoin。黃金也呈負敏感，但解釋力只有約0.09；其餘資產多數R²低於0.07，代表成長、通膨、美元、獲利與風險偏好往往比利率單一變數更重要。",
            },
            {"id": "cross_beta_chart", "type": "chart", "chartId": "cross_asset_beta"},
            {
                "id": "fund_finding",
                "type": "markdown",
                "sourceId": "rate_backtest",
                "body": "## 七檔基金呈現三種不同傳導\n\n- **負利率敏感：** 施羅德黃金、富邦AI、群益印度中小。\n- **接近中性：** 富蘭克林生技、貝萊德世界礦業、景順環球消費。\n- **正向景氣型：** 施羅德能源在長債殖利率上升時反而偏強，較像通膨與需求循環曝險。\n\n這些是歷史敏感度，不是新的評分或買賣條件。",
            },
            {"id": "fund_beta_chart", "type": "chart", "chartId": "held_fund_beta"},
            {"id": "fund_table", "type": "table", "tableId": "held_fund_table"},
            {
                "id": "cutting_cycle_finding",
                "type": "markdown",
                "sourceId": "rate_backtest",
                "body": "## 降息原因比降息動作重要\n\n利率上升階段常出現在經濟仍能承受緊縮時，因此SPY、QQQ、IWM、能源與消費仍可能上漲；利率下降則可能同時反映衰退或金融壓力。歷史上Fed下降月份後12個月，GLD中位數約+19.5%、TLT約+7.4%，但QQQ約-5.3%、VNQ約-6.7%、IBB約-1.7%。這不是預測下一次降息，而是提醒系統必須配合CTA與景氣確認。",
            },
            {"id": "fed_chart", "type": "chart", "chartId": "fed_regime_forward"},
            {
                "id": "recommendations",
                "type": "markdown",
                "body": "## 對Onecool OS的建議\n\n1. **保留現有US 30Y與Market Regime。** 回測證明長債利率對久期、黃金與部分AI資產有解釋價值。\n2. **不新增自動分數或買賣規則。** 利率對大多數風險資產的單變數R²太低。\n3. **CTA維持最高權限。** 利率層只回答『目前逆風或順風來自哪裡』，不能單獨停扣、加碼或賣出。\n4. **先觀察現有週報。** 黃國華Market Regime已經涵蓋DXY、30Y、WTI與風險偏好，暫時不需要再增加一張利率表。",
            },
            {"id": "all_assets", "type": "table", "tableId": "all_asset_table"},
            {
                "id": "further_questions",
                "type": "markdown",
                "body": "## Further Questions\n\n- 未來若要提升解釋力，應測試『實質利率＋通膨預期＋美元』的聯合模型，而不是再增加更多單一殖利率。\n- 現代ETF與Bitcoin成立較晚，完整升降息週期只有少數幾次；需要隨時間累積樣本。",
            },
            {
                "id": "caveats",
                "type": "markdown",
                "sourceId": "rate_backtest",
                "body": "## Caveats and Assumptions\n\n- 回測為描述性關聯，不證明利率造成資產報酬。\n- 月度狀態樣本會重疊；另以狀態起點樣本做方向檢查，但新ETF起點事件通常少於10次。\n- 各資產成立日不同，不能把短樣本與30年以上基金視為同等可信。\n- 30年期公債殖利率依官方說明排除2002年2月至2006年2月停編區間。\n- WTI使用現貨價格變化，不包含期貨轉倉；DXY是價格指數；基金使用美元級別公開淨值。\n- 只使用截至2026年7月31日的完整月份，未納入2026年8月未完成月。",
            },
        ],
    }
    artifact = {
        "surface": "report",
        "manifest": manifest,
        "snapshot": {
            "version": 1,
            "generatedAt": payload["generated_at"],
            "status": "ready",
            "datasets": {
                "all_assets": rows,
                "held_funds": held,
                "cross_assets": cross,
            },
        },
        "sources": [source_item],
        "package_info": {
            "name": "onecool-us-rate-backtest",
            "snapshot": "2026-07 completed month",
        },
    }
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/market/rate_asset_backtest/backtest_latest.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    artifact = build(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
