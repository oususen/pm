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

---

## 補足: BOM側に工程/ラインを持たせる案（将来検討）
- 現状採用: BOMは構成のみを持ち、ルーティングは別テーブル。BOMからボタンでルーティングを自動生成し、生成時にベース工程/ラインを指定する。
- 将来案: BOM明細に `process_id`, `line_id`, `time_value`, `time_unit` などを追加し、入力時に工程/ラインを紐付ける。入力内容をそのままルーティングに昇格させる、またはルーティング草案として生成する。
- 検討ポイント: ルーティングの順序・待ち時間をどこで管理するか、工程別に部品を紐づけるか（二重管理リスク）。必要になったらスキーマ拡張＋UI対応を実施。

## 補足: 工程別の部品消費マスタ
- テーブル: `m_routing_step_material` を追加（工程に対して部品・数量・消費タイミング）。
- 目的: 共通部品を複数工程で消費するケースを明示し、計画・引当・在庫管理で工程単位の消費を扱うため。
- API: `/api/routing-step-materials/` (GET/POST/PUT/DELETE)。

---

## 8. 進捗管理 vs 在庫管理（ルール整理）

### 進捗管理（ライン需要展開）
- 入力源: 受注（確定/内示）。OPEN 受注明細をデフォルトルーティング逆順で全工程に一括展開。
- 保存先: `t_line_demand`（line, product, plan_date 単位）。確定/内示/計画/実績を保持。
- 対象工程: 全工程（最終工程だけでなく中間工程も展開）で進捗把握が目的。
- トリガ: `/api/line-demands/expand/`（clear_existing オプション）で再生成。
- 表示: 進捗管理画面では `t_line_demand` をそのまま表示。バックログは参照しない。

### 在庫管理（前後ライン間のバケツリレー）

- コンセプト: 前ラインが「取り込み」時に後ラインのplan_qtyを自動集計。手動展開は不要。
- 保存先: `line_backlog`テーブル

  ```python
  line_backlog(
    plan_date,
    process_id,           # 工程ID
    product_id,          # 製品ID
    line_id,             # このライン
    order_qty,           # 発注数/受注数（取り込み時に自動計算）
    plan_qty,            # 計画数量（ユーザーが入力する生産計画）
    actual_qty,          # 実績数量（実際の生産数量）
    stock_qty,           # 在庫数量
    planned_stock_qty,   # 計画在庫数量
    source_line_id,      # （参考）後ライン
    source_routing_step_id,
    updated_at
  )
  ```

  - `line_id` … このライン
  - `order_qty` … 発注数/受注数
    - **最終ライン**: LineDemand.plan_qtyをそのまま取得
    - **他ライン**: 後ラインのplan_qty × BOM個数を集計（複数後ラインの場合は合計）
  - `plan_qty` … ユーザーが入力する生産計画数量
  - `actual_qty` … 実績
  - `stock_qty` … 在庫
  - `planned_stock_qty` … 計画在庫

- order_qtyの計算ロジック（pickup時）:
  1. このラインが生産する製品（output_product）を特定（phantom製品は除外）
  2. 各製品について：
     - **ステップ1**: child_product にこの製品を持つ BOM 明細を取得（親製品 = 後工程で作る品）
     - **ステップ2**: 親製品がphantom製品の場合、さらにその親を辿る
       - phantom製品のBOMを再帰的に探索し、最終的な非phantom製品（final_parent）を特定
       - BOM個数は階層を通して累積（total_qty_per = qty1 × qty2 × ...）
     - **ステップ3**: final_parentを output_product に持つ RoutingStep（後工程ライン）を取得
    - **ステップ4**: 後工程ラインの LineBacklog.plan_qty を取得し、total_qty_per を掛け算  
       - リードタイム考慮：稼働日ベースで lt_days 日前倒し  
         - 優先順: RoutingStep.lead_time_days > Line.lead_time_days > BOMItem.lead_time_days  
         - 使用カレンダ: `calendar_code='tiera_muke'` を参照（未設定時は暦日）
     - 複数ライン・複数親製品があればすべて合計
  3. 後ラインからの需要が 0 件の場合（最終ライン）は LineDemand から取得

  **phantom製品の処理例**:
  - 現在ライン: Line 7、output_product = 195 (YD40000608)
  - BOM: 195 → 324 (YD60000441S, phantom, qty=1) → 113 (YD60000441, qty=1)
  - final_parent = 113、total_qty_per = 1 × 1 = 1
  - 後工程ライン: Line 5 (113を出力)
  - order_qty = Line 5の plan_qty × 1

- トリガ:
  - 取り込み: `/api/line-backlogs/pickup/`
    - 既存データの有無に関わらず order_qty を再計算して LineBacklog に保存
  - 保存: `/api/line-backlogs/save/`
    - ユーザーが入力した計画データ（plan_qty等）をLineBacklogに保存

- 表示: 生産計画入力画面は order_qty（需要）、計画、実績、在庫、計画在庫の5列を表示。

### 違いのまとめ

- 目的: 進捗管理=全工程俯瞰、在庫管理=前後ラインの発注/受注つなぎ。
- 展開範囲: 進捗管理は全工程一括、在庫管理は取り込み時に後ラインから自動集計。
- データ源: 進捗管理=受注（確定/内示）、在庫管理=後ライン計画（plan_qty）。
- 表示データ: 進捗管理=`t_line_demand`、在庫管理=`line_backlog`。
- ボタン: 進捗管理は一括展開（API）、在庫管理はライン単位で「取り込み」「保存」のみ。

### 生産計画入力画面のフロー（新設計）

1. **ラインを選択**
   - ユーザーが生産計画を立てたいラインを選択

2. **取り込み** (`/api/line-backlogs/pickup/`)
   - 選択したラインの需要データを取得・計算
   - **既存データがある場合**: LineBacklogからそのまま取得
   - **既存データがない場合**:
     - 後ラインのplan_qtyを集計 × BOM個数 → order_qty
     - 後ラインがない（最終ライン）場合はLineDemand.plan_qtyから → order_qty
     - 計算結果をLineBacklogに保存
   - 画面に order_qty（需要）、計画、実績、在庫、計画在庫を表示

3. **計画入力**
   - ユーザーが各製品・日付の計画数量を入力

4. **保存** (`/api/line-backlogs/save/`)
   - 入力した計画データをLineBacklogに保存
   - plan_qty、actual_qty、stock_qty、planned_stock_qtyを更新
   - **保存後、前ラインが「取り込み」を押すと、この保存したplan_qtyが自動集計される**

---

## 9. 工程ガント表示（フロント仕様・最新版）

- **データソース**: `line_backlog` を読み取り専用で取得（API: `GET /line-backlogs/` with `line`, `plan_date__gte`, `plan_date__lte`）。`expand_processes` は使用しない（書き込み抑止）。
- **期間**: 5日固定（基準日を中心に一昨日・前日・当日・翌日・明後日）。ラインの勤務カレンダ＋勤務パターンから稼働時間帯を生成し、休憩を除いた連続セグメントを横軸に使用。
- **所要時間の算出**:
  - `computed_time_min` を最優先。
  - 無ければルーティングの `duration_min × plan_qty`（最小1分扱い）。`cycle_time_min`（m_process_cycle_time）は使わない。
- **工程順序**: `step_no` を降順にして「最終工程→前工程→…→頭工程」。`step_no` が無い場合は工程IDで降順。
- **開始時刻の決め方**:
  - 最終工程: `plan_date` の最初の稼働セグメント開始（例: 勤務開始 08:00）を起点に配置。
  - 前工程以降: 直後工程の開始から「サイクル×3台分（固定 BUFFER_FACTOR=3）」だけ巻き戻す。勤務時間外に食い込む場合は前日の稼働セグメントへシフトして開始。
- **バー配置**: 同一工程・同一製品につき1本のバー（plan_qty 全量）を描画。左に計画ロット数、バー内に「開始–終了（HH:MM）」を表示。工程内の並びは `plan_date` → `sequence_no` を基準にしつつ、前倒しで得た開始時刻がカーソルより早ければその時刻に合わせて配置。
- **表示専用**: ガント表示では DB への書き込みは行わない（line_backlog の読込のみ）。
---

## 10. 生産計画入力画面のUI仕様（現状確認）

- ボタン構成: 「新規行追加」「クリア」「保存」「取り込み」「工程ガント表示」の5つに集約。旧「工程展開」ボタンと工程展開グリッドは廃止。
- 取り込み: 選択中ライン・期間で `/api/line-backlogs/pickup/` を呼び、order_qty/plan_qty/実績/在庫を行データに展開。
- 保存: 編集した行のうち `product_id` と `process_id` がある日別セルだけを `/api/line-backlogs/save/` に送信。plan_qty・sequence_no などを更新。
- ガント表示: ページ内下部に `ProcessGanttView` を埋め込み。トグル表示で、開くたびに現在のライン・期間で GET `/api/line-backlogs/` を読み込み、上記ガント仕様（§9）で描画。表示のみで DB 書き込みなし。
- 行リセット: クリアは現在の rows を初期化するだけ（工程展開結果など他セクションは存在しない）。
- その他: 新規行は `process_id` が空のままだと保存対象外。pickup で取得した行は process_id を保持するため保存可。

---

## 11. BOM→ルーティング自動生成（現行実装）

- トリガ: BOM画面のPOST `/api/boms/{bom_id}/generate_routing/`。BOMツリーからルーティングを作り直す（既存ステップは削除）。
- 対象データ: `sourcing_type='MAKE'` のBOM明細だけを再帰的に収集。子BOMを先に辿るポストオーダーで集め、(depth, path) を持たせて工程順を決定。
- 必須項目: 各明細に `process` と `time_unit(MINUTE/DAY)` が必要。MINUTEなら `duration_min>0`、DAYなら `lead_time_days>0`。lineは指定あれば反映。
- ルーティングヘッダ: `AUTO-{parent_product_code}-{bom.version}` をデフォルト発番。description自動生成、`is_default=true` を指定すると同製品の他ルートは非デフォルト化。
- ステップ生成: 収集順に `step_no=1..` を振り、`process/item.line/output_product=item.child_product` を設定。`hierarchy_depth` と `hierarchy_path`（例: 1.2.3）でBOM階層を保持。`time_unit` と `duration_min/lead_time_days` は明細値を転記。
- 最終工程オプション: リクエストに `final_process` を渡した場合、親製品を `output_product` にした終端ステップを末尾に追加（line/time_unit/duration_min/lead_time_daysはリクエスト値）。
- 材料自動紐付け: 各ステップの `output_product` に有効BOMがあれば、その子明細を `routing_step_material` として `consume_timing='START'` で登録。
- 出力/更新対象: `m_routing` ヘッダ、`m_routing_step`、`m_routing_step_material` のみを更新。その他テーブルへの書き込みは行わない。
