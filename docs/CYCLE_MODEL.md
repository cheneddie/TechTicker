# TechTicker 硬體價格週期模型

## 目的

TechTicker 追蹤是否正在形成類似 2022～2023 的硬體下跌週期。

核心邏輯：

> 需求降溫 + 庫存累積 + 供給增長超過需求 = 價格下跌週期的高風險組合。

## Downturn Readiness 0～100

- 0–19：主升／供給吃緊
- 20–39：過熱但尚未反轉
- 40–54：築頂監控
- 55–69：下跌週期形成
- 70–84：明確下跌
- 85–100：深度去庫存／崩價

組成：

1. 六大反轉事件：75%
2. FRED 公開價格代理 3 個月動能：15%
3. 四大 CSP SEC XBRL 實際 CapEx 年增率：10%

若某資料源暫時無法取得，缺失資料不會被硬填成負面訊號。

## 六大反轉事件

1. 四大 CSP 下修 AI／資料中心 CapEx 指引
2. AI Server 出貨預測首次明顯下修
3. CSP Server DRAM 庫存持續累積
4. NAND 供需轉正／合約價 QoQ 轉跌
5. Samsung／SK hynix／Micron 從配額轉向降價搶單
6. DRAM 新廠大量產出時程由 2028 提前至 2027

## 資料來源

- FRED / U.S. BLS PPI：半導體、儲存裝置、電子電腦製造
- SEC Company Facts XBRL：Microsoft、Amazon、Alphabet、Meta 的實際資本支出
- Google News RSS：事件發現器，查詢鎖定 TrendForce、公司與主流產業新聞關鍵字
- 所有事件證據保存至 `data/events/events.jsonl`

## 重要限制

- FRED PPI 是美國生產者價格代理，不等於台灣零售 DDR5/SSD/GPU 街價。
- Google News RSS 只是事件發現器；單篇新聞不直接等於反轉，因此使用 CLEAR / WATCH / TRIGGERED 分級。
- SEC CapEx 是實際財報數字，不等於公司對未來 CapEx 的口頭 guidance；guidance 由事件層監控。
- DRAM/NAND 精確合約價很多屬付費資料，本專案只使用公開可驗證資訊，不繞過付費牆。
- 分數是規則式早期警報，不是統計機率，也不是投資建議。

## 資料持久化

- `data/latest.json`：最新完整快照
- `data/history/daily.csv`：每日總分歷史
- `data/events/events.jsonl`：事件證據 append-only log
- `docs/DASHBOARD.md`：人類可讀儀表板
