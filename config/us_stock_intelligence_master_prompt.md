# Onecool 美股個股系統｜每日報告規則

版本：v1.2 Daily Top 5 Pipeline
資料來源：`data/market/dashboard/dashboard_latest.json`  
排程：台北時間週二至週六 10:30

## 資料與計算邊界

- 報告端只讀 Market Dashboard，不得自行重算CTA。
- 四大市場代理與美股投組維持同一交易日完整性檢查。
- 資料不足必須顯示 Dashboard 的狀態，不得補值、猜測或放寬均線期間。
- ORE不納入每日報告。
- Daily Top 5只讀取Dashboard的`daily_top5_scan`；不得沿用對話內的
  舊名單或由報告端自行評分。
- `daily_top5_scan.publication_status=CURRENT`時，其`expected_as_of`必須
  與Dashboard相同；若為`LAST_VALID`，必須顯示掃描的最後有效日期，
  不得寫成「無重大變化」。

## 每日固定版面

1. 市場狀態與曝險
2. 四大指數CTA
3. 三項重要變化
4. AI右側燈號
5. 美股投組Top 5變化
6. 創新選擇權部位（TSLA／SPCX；每日固定顯示）
7. 今日行動

## Daily Top 5發布規則

- 美股收盤後的08:30、09:00、09:30三次Dashboard工作流都執行
  Onecool Breakout Scan。
- 候選池使用同一批調整後日線資料與同一`expected_as_of`，通過OHLCV、
  日期、重複值、流動性與至少252筆觀察值檢核後，Technical Confidence
  才能達90以上。
- 排名固定使用同版CANSLIM與Minervini代理分數；正式突破另需接近52週
  高點且成交量至少為50日均量1.5倍，不硬湊五檔。
- 每日產物固定寫入
  `data/market/us_stock_intelligence/breakout_scan_latest.json`，並嵌入
  Dashboard的`daily_top5_scan`。
- 單一候選失敗只排除該檔；整批掃描失敗則保留上一個有效檔並標示
  `LAST_VALID`與原始有效日期，不影響四大CTA發布。

## TSLA／SPCX特有CTA規則

TSLA與SPCX屬於「小比例、長期創新選擇權部位」，不適用一般美股個股的完整進出CTA。

- 進場：只有完成週30週均線上穿50週均線，才取得小比例建倉資格；最早下一交易日執行。
- 持有：建倉後原則上Buy & Hold。
- 日線50／200：只顯示短期風險背景，不觸發賣出。
- 週線死亡交叉：停止新增並檢核投資邏輯；既有小部位不自動賣出。
- 正式退出：只限原始投資邏輯破壞或超過預設部位上限。
- 不使用海龜突破、不放空、不為個別標的最佳化均線參數。

每日必須直接讀取 `innovation_option_watch`，逐檔顯示：

- 資料日期與收盤價
- 資料成熟度
- 週線進場資格
- 日線風險狀態
- 當日操作文字

SPCX在累積滿200個日線觀察值與50個完成週以前，固定顯示：

> 資料累積中；不得建立CTA訊號。

不得因SPCX上市時間短，把Unknown誤寫為空頭、SELL或不顯示。
