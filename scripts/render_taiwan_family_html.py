#!/usr/bin/env python3
"""Render only the committed public snapshot; never import calculation engines."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import time
from urllib.request import Request, urlopen


def text(value):
    if value is None or value == "":
        return "Unknown"
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return html.escape(str(value), quote=True)


def obj(value):
    return value if isinstance(value, dict) else {}


def render(raw):
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Snapshot must be a JSON object")
    pressure = obj(data.get("market_pressure"))
    markets = obj(data.get("market_cta"))
    rows = data.get("top5")
    rows = rows if isinstance(rows, list) else []
    digest = hashlib.sha256(raw).hexdigest()
    out = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width,initial-scale=1">',
           '<title>Onecool 台股親友版｜正式唯讀 Snapshot</title>',
           '<style>body{font-family:system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;line-height:1.7;color:#182a32}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccd5da;padding:.6rem;text-align:left}section{margin:2rem 0}.table{overflow-x:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere}footer{border-top:1px solid #ccd5da;overflow-wrap:anywhere}</style>',
           '</head><body><main><h1>Onecool 台股親友版</h1>',
           '<p>正式唯讀 Snapshot。所有訊號、分數與順序沿用來源；缺漏欄位顯示 Unknown。更新頁面不代表資料日期更新。</p>',
           '<section><h2>市場壓力燈</h2>']
    for key, label in (("light", "市場壓力燈"), ("status", "狀態"), ("action", "正式行動"), ("as_of", "資料日"), ("reason", "判定原因")):
        out.append(f'<p>{label}：{text(pressure.get(key))}</p>')
    out.append(f'<p>資料狀態：{text(data.get("display_status"))}</p><p>候選行動閘門：{text(data.get("candidate_action_gate"))}</p></section>')
    for heading, symbols in (("台灣 CTA", (("0050", "0050 CTA"), ("2330", "2330 CTA"))), ("亞洲 CTA", (("1306", "日本 1306 CTA"), ("069500", "韓國 069500 CTA")))):
        out.append(f'<section><h2>{heading}</h2>')
        for symbol, label in symbols:
            cta = obj(markets.get(symbol))
            out.append(f'<p>{label}：{text(cta.get("cta"))}；趨勢：{text(cta.get("trend"))}；資料日：{text(cta.get("as_of"))}</p>')
        out.append('</section>')
    out.append('<section><h2>Top 5 研究名單</h2><p>排名為 Snapshot 陣列原有順序；不重新評分或排序。個股技術訊號不取代上方正式行動。</p><div class="table"><table><thead><tr>')
    for label in ("排名", "標的", "分數", "估值 PE", "估值 PB", "個股 CTA", "CTA 資料日", "來源行動資格", "股價／估值日"):
        out.append(f'<th scope="col">{label}</th>')
    out.append('</tr></thead><tbody>')
    if not rows:
        out.append('<tr><td colspan="9">Unknown</td></tr>')
    for rank, row in enumerate(rows, 1):
        row = obj(row)
        cta = obj(row.get("individual_cta"))
        cells = [str(rank), text(row.get("symbol")) + ' ' + text(row.get("company_name")), text(row.get("score")), text(row.get("pe")), text(row.get("pb")), text(cta.get("cta")), text(cta.get("as_of")), text(row.get("action_eligibility")), text(row.get("price_as_of"))]
        out.append('<tr>' + ''.join(f'<td>{cell}</td>' for cell in cells) + '</tr>')
    out.append('</tbody></table></div></section><footer><h2>資料日期與驗證</h2>')
    for key in ("generated_at", "screen_as_of", "source_generated_at"):
        out.append(f'<p>{key}：{text(data.get(key))}</p>')
    out.append('<p>generated_at 若為 Unknown，表示 Snapshot 未提供此欄位；各來源產生時間見 source_generated_at。</p>')
    for symbol in ("0050", "2330", "1306", "069500"):
        out.append(f'<p>{symbol} CTA as_of：{text(obj(markets.get(symbol)).get("as_of"))}</p>')
    for row in rows:
        row = obj(row)
        cta = obj(row.get("individual_cta"))
        out.append(f'<p>{text(row.get("symbol"))}：CTA as_of {text(cta.get("as_of"))}；weekly_data_as_of {text(cta.get("weekly_data_as_of"))}；source_data_as_of {text(cta.get("source_data_as_of"))}；財報 {text(row.get("fundamentals_as_of"))}；營收 {text(row.get("monthly_revenue_as_of"))}</p>')
    out.append(f'<p>Snapshot SHA-256：{digest}</p><p><a href="taiwan_stock_family_latest.json">正式 JSON Snapshot</a></p></footer>')
    # Visible, escaped original payload retains every source field for crawlers.
    out.append('<section><h2>完整來源欄位（唯讀）</h2><pre>' + html.escape(raw.decode('utf-8')) + '</pre></section></main></body></html>')
    return ('\n'.join(out) + '\n').encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('data/public/taiwan_stock_family_latest.json'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify-url')
    args = parser.parse_args()
    expected = render(args.source.read_bytes())
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(expected)
    if args.verify_url:
        if not args.verify_url.startswith('https://'):
            parser.error('Only public HTTPS verification is supported')
        for attempt in range(12):
            try:
                with urlopen(Request(args.verify_url, headers={'Cache-Control': 'no-cache'}), timeout=20) as response:
                    if not response.url.startswith('https://') or response.read() != expected:
                        raise ValueError('Public HTML differs from snapshot-rendered HTML')
                print('PASS: public HTTPS HTML matches formal Snapshot: pressure, Taiwan/Asia CTA, ordered Top 5, scores, valuations, dates and hash')
                break
            except (OSError, ValueError):
                if attempt == 11:
                    raise
                time.sleep(10)
    if not args.output and not args.verify_url:
        parser.error('Specify --output or --verify-url')


if __name__ == '__main__':
    main()
