# スケジューリング逆算ロジック v3（詳細版）

## 0. 前提
- 営業日テーブル：`m_calendar_day (is_working_day, work_minutes)` を使用。
- DAY工程は“その日末に完了”とみなす（スナップ規則）。
- 計算結果は `t_schedule_detail` に書き出す。

---

## 1. 日跨ぎ関数
### 1.1 work_back(end_dt, minutes, calendar)
```
remain = minutes
cursor = end_dt
while remain > 0:
  day = calendar.day(cursor.date)
  if not day.is_working: 
      cursor = prev_day_end(cursor.date, calendar); continue
  start_of_day = day_end - day.work_minutes
  # day_end = 営業日の終了時刻（例: 17:00）。work_minutes=480 なら 9:00-17:00 相当。
  usable = max(0, (cursor - start_of_day).minutes)
  use = min(remain, usable)
  cursor -= use
  remain -= use
  if remain > 0: cursor = prev_day_end(cursor.date - 1, calendar)
return cursor
```

### 1.2 work_forward(start_dt, minutes, calendar)
`work_back` の逆向き。`usable = day_end - max(start_dt, day_start)` を使って加算。

---

## 2. MINUTE工程の所要算出
```
qty = lot_size or order_qty
ct = lookup_cycle_time(product=step_output_product, process=step.process, line=step.line, date=ref_date)
duration_min = step.duration_min or (ct.setup_time_min + ct.cycle_time_sec * qty / 60)
```

> **基準製品**：`m_routing_step_output.output_product_id` を使用。  
> 溶接ステーションごとに output_product を変えることで、サイクル差を自然に表現。
> 受注品番も最終工程の output_product と一致させ、進度・在庫・スケジュールを同一コードで追う。

---

## 3. 逐次着手（transfer_batch）の具体化
前工程（P）→後工程（S）で `transfer_batch_qty=B` のとき：
1) Pの `duration_min` を qty で均等割り：`per_unit = (duration_min - setup) / qty`
2) B個ごとの完了時刻リストを生成：`t_k = P.start + setup + per_unit * (k*B)`
3) Sは `start = max(S.start, t_1)` で起動。各バッチごとに `t_schedule_detail` を分割して登録（`batch_no=1..`）。

> 移動/段取りのバッチ間オーバーヘッドがあれば `m_routing_step_param` に `transfer_gap_min` を追加して加算してもよい（現状はロジック側で固定値0扱い）。

---

## 4. バッファ制御（WIP）
- 監視対象：`WIP(t) = 完了累計(P, t) - 開始累計(S, t)`
- 目標レンジ：`[target_buffer_qty, max_buffer_qty]`
- 制御方法（簡易）：
  - `WIP < target` → Sの開始を遅らせる（`start += Δ`）
  - `WIP > max` → Pの開始を遅らせる or 休止（翌日の空き枠へスライド）

> 実装はヒューリスティックで十分（例：5分刻みで調整）。高度化は将来の最適化問題。

---

## 5. DAY工程の扱い
- `time_unit='DAY'`：`lead_time_days = d` の場合、`end = shift_business_days(end, -d)`
- 日内位置：`end` を営業日の終了時刻にスナップ、`start = work_back(end, work_minutes_of_d, calendar)` で“その日を丸々占有”扱いにしてもよい。

---

## 6. 書き出し（t_schedule_detail）
各ステップ/バッチごとに：
```
INSERT t_schedule_detail(order_id, routing_step_id, planned_start, planned_end, batch_no, quantity, status)
VALUES (...)
```
- MINUTE工程：バッチごとに分割（`batch_no` 連番）。
- DAY工程：`batch_no=1, quantity=lot_size or order_qty`。

---

## 7. 整合チェック
- `time_unit='DAY' AND lead_time_days<=0` → NG
- `time_unit='MINUTE' AND COALESCE(duration_min, calc_duration)<=0` → NG
- `BUY AND supplier_id IS NULL` → NG
- 連続性：`step_no` の欠番禁止（アプリ/マイグレーションで保証）
