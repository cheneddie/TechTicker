# TechTicker

**PC 硬體價格週期監控 + 2022 式下跌週期早期警報**

TechTicker 每日自動更新：

- 半導體／儲存裝置／電腦 PPI
- Microsoft / Amazon / Alphabet / Meta 實際 CapEx
- 六大硬體反轉事件
- 0～100 `Downturn Readiness`
- 歷史分數與事件證據

## 六大事件

1. 四大 CSP 下修 AI／資料中心 CapEx
2. AI Server 出貨預測明顯下修
3. CSP Server DRAM 庫存持續累積
4. NAND 供需轉正／合約價 QoQ 轉跌
5. Samsung／SK hynix／Micron 從配額轉向降價搶單
6. DRAM 新廠大量產出由 2028 提前至 2027

## 查看結果

- 最新儀表板：[`docs/DASHBOARD.md`](docs/DASHBOARD.md)
- 最新 JSON：[`data/latest.json`](data/latest.json)
- 分數歷史：[`data/history/daily.csv`](data/history/daily.csv)
- 事件紀錄：[`data/events/events.jsonl`](data/events/events.jsonl)
- 模型定義：[`docs/CYCLE_MODEL.md`](docs/CYCLE_MODEL.md)

## 本機執行

```bash
python scripts/update.py
```

Runtime 只使用 Python standard library。

## 自動更新

GitHub Actions 每天台北時間約 09:15 執行，也支援手動 `workflow_dispatch`。資料更新後自動 commit `data/` 與 `docs/DASHBOARD.md`。

SEC 建議設定 Repository Variable：

```text
SEC_USER_AGENT=Your Name your-email@example.com
```

## 設計原則

- 原始證據可追溯
- 缺資料不假造
- 付費資料不繞過
- 單一新聞不直接等於反轉
- CLEAR / WATCH / TRIGGERED 分級
