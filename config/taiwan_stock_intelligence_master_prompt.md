# Onecool Taiwan Stock Intelligence — Screening Contract

版本：v1.0 Taiwan Broad Screen  
正式篩選檔：`data/market/taiwan_stock_intelligence/screen_latest.json`

## 唯一名單來源

- 日報研究優先名單只能讀取正式篩選檔的 `top5`，不得從對話內容、
  單一股票查詢、新聞或主觀判斷增補標的。
- 使用者詢問某檔股票只代表個股研究，不代表該股通過系統篩選。
- 0050、2330及亞洲CTA仍只讀 Onecool Market Dashboard；本篩選器不得
  計算、改寫或推導CTA。

## 發布條件

- 候選池為正式上市、具月營收資料的四位數普通股，按官方成交金額取
  前200檔。
- 所有候選股必須使用同一價格／估值截止日、同一月營收期間、同一財報
  期間及同一版評分規則。
- 分數80分以上為正式候選；75至79.99分只列觀察，不進正式Top表格。
- 正式表格最多5檔、同產業最多2檔，不硬湊。
- 缺漏、重複、異常或非正值EPS／本益比／股價淨值比一律排除，不得用
  推估值補齊。
- 日報只有在 `data_status=READY` 且 `publication_status=CURRENT` 時發布
  `top5`；否則揭露資料異常，不沿用對話中的舊名單冒充當日結果。

## 行動層

篩選分數只決定研究優先順序。實際行動仍依0050 CTA、個股正式CTA、
估值及市場壓力燈共同決定；市場黃／紅燈時不得因高分而新增主動部位。
