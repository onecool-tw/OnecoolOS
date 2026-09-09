# Onecool 美股個股系統｜每日報告規則

版本：v1.3 US Super Growth Quality Gate
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
4. AI／半導體CTA與具體短期風險
5. 美股投組Top 5變化
6. 創新選擇權部位（TSLA／SPCX；每日固定顯示）
7. 今日行動

## Daily Top 5發布規則

### 共用評分契約（onecool_us_dual_v2）

- 候選與五檔持股必須使用同一次輸入與 `score_security`；禁止固定基本面舊分數。
- 正式門檻直接讀取產物 `thresholds`：沿用程式 CANSLIM 70、Minervini 80；
  不得再於報告中另寫 CANSLIM 80。門檻調整須另行版本化與驗證。
- 價格基準統一標示 `adjusted_close`；重疊標的使用 Dashboard 的相同歷史。
- 基本面缺漏、日期在未來、超過180日或數值不完整，一律 Unknown，不能補零。
  180日是過期上限，不代表較新的資料自動完成最新財報查核。
- Technical Confidence不是投資分數；資料日期、OHLCV、映射、交易日不一致即排除。
- 個別持股驗證失敗只影響該檔；基本面失敗可保留已驗證技術分數，雙系統狀態為Unknown。
- 50日平均成交金額2,000萬美元是新候選與新增部位門檻。既有持股低於門檻時，
  保留技術與基本面分數並標示`BELOW_NEW_ENTRY_MINIMUM`，不得因此把整份投組改為
  `PARTIAL`；日期、OHLCV、交易日或映射錯誤仍照常阻擋。
- `data_status=READY`只代表該模組；不得把Dashboard READY解讀成候選、基本面與AI全部通過。
- 已依使用者決定停用AI右側四項確認；不計算或顯示X／4，也不保留Unknown佔位。
- AI／半導體判斷使用QQQ、SOXX、NVDA CTA與具日期及來源的短期風險事實；不得合成確認數或改寫CTA。
- 每個指數／AI CTA一行；資料品質錯誤不得改寫CTA或自動當成市場SELL。

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

## 美股超級成長品質閘門

Daily Top 5技術排名完成後，所有「新候選」必須再讀取
`data/market/us_stock_intelligence/super_growth_evidence_latest.json`，逐檔檢查具日期、
理由及來源的競爭優勢、結構性成長續航、財務品質、集中度與治理風險、能力圈及估值。
缺少證據一律為`UNKNOWN`，不得由CAN SLIM分數、股價上漲或新聞印象推測。

- A：品質與估值全部通過；仍須等待正式技術觸發、市場CTA、個股CTA與壓力綠燈。
- B：品質通過但估值未通過或未確認；只研究，不行動。
- C：品質證據不足或成長仍待證明；只研究，不行動。
- `REJECT`：任一必要品質閘門有具證據的失敗結果。

品質閘門只註記候選，不得改寫原始技術排名、CAN SLIM／Minervini分數或CTA。
既有BABA、XYZ、QRVO、RH、UPBD部位不因品質分級自動賣出；仍依既有CTA與投資邏輯管理。
CAN SLIM只作概念對照，不另加一層分數：C/A為盈餘與營收成長，N/L為創新與領導地位，
S/I為供需與法人證據，M由美股大盤CTA負責。

## TSLA／SPCX特有CTA規則

TSLA與SPCX屬於「小比例、長期創新選擇權部位」，不適用一般美股個股的完整進出CTA。
兩者亦明確豁免超級成長品質閘門，不得因A／B／C分級改寫其特有規則。

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
