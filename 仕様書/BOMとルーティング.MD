# BOMとルーティング

## 概要
BOMからルーティングを自動生成する際のルールをまとめる。
対象はBOMツリー（BOM TREE）とルーティング工程（m_routing_step）。

## 用語
- BOM階層: BOMツリー上の深さ。ドット区切りの数で表現する。
- hierarchy_path: BOMツリーでの通しパス。例: `1.1.1.4`
- hierarchy_depth: 階層の深さ。例: `1.1.1.4` -> 4
- step_no: 工程順を表す番号。昇順で前工程 -> 後工程。
- parallel_group: 同一step_no内の順序グループ。

## BOM -> ルーティング自動生成
### 1) 階層パスの付け方
- BOMを深さ優先で辿り、兄弟の順序(idx)を積み上げて `hierarchy_path` を作る。
- 例: 1番目の子 -> `1`、その子の1番目の子 -> `1.1`、以後同様。
- `hierarchy_depth` はドット区切りの数。
  - `1.1.1.4` -> 4
  - `18.1` -> 2

### 2) 工程番号(step_no)と並列グループ(parallel_group)
受注展開(ORDERDEMAND)で工程順として使用できるよう、以下の採番ルールを適用する。

- **step_no**: 階層を反転して付与する。
  - `step_no = (max_depth - 階層数 + 1) * 1000`
  - 最終工程(階層1)が最大step_noになる。
- **parallel_group**: `hierarchy_path` の数字を連結して整数化。
  - `1.1.1.4` -> `1114`
  - `1.1.4.1` -> `1141`
  - `1.1.18.1` -> `11181`

### 3) 最終工程
- 最終工程(完成品)は `hierarchy_path = final`、`hierarchy_depth = 0`。
- `step_no` は自動生成工程の **最大step_no + 1** に設定する。
  - 最終工程が常に最後(最大)になることを保証する。

### 4) 自動生成時のルーティングヘッダ開始日時
- BOM詳細画面の「BOMからルーティング生成」では、ルーティングヘッダの `有効開始日時` を指定できる。
- 初期値は **実行時点の2日後 08:00** とする。
- 未指定でAPIを呼んだ場合も、バックエンドで **2日後 08:00** を補完して保存する。

### 5) BOM明細との紐付け
- 自動生成される `RoutingStep` には、生成元の `BOMItem` を `source_bom_item_id` として保存する。
- BOM↔Routingの同期時は `source_bom_item_id` を最優先キーとして解決する。
- `remark`（親製品コード）は表示・補助用途として維持する。

## ORDERDEMAND展開での利用
- 受注展開は `step_no` 昇順 -> `parallel_group` 昇順で処理される。
- 上記ルールにより、BOM階層の順序が工程順として利用可能になる。
- 注意: BOMの並び順が工程順と一致していることが前提。

## 注意事項
- step_noは `(routing_id, step_no, parallel_group)` で一意。
- `time_unit='DAY'` の場合は `lead_time_days >= 0` を許可する。
- リードタイムの遡りは稼働日(カレンダ)を考慮して算出する。
- 一次情報はBOMItemとし、RoutingStepはBOMから生成される派生データとして扱う。
- BOM↔Routing同期の紐付けはFK（`source_bom_item_id`）優先に段階移行し、`remark` は表示情報として維持する（詳細: `仕様書/LT同期改善チケット.md`）。
- BOM明細削除時は、削除前に影響候補の `RoutingStep` 一覧を表示する。
- 一覧のうち `source_bom_item_id = 対象BOMItem.id` の工程は **自動削除対象** とし、利用者がチェックを入れた場合のみ `BOMItem` 削除と同時に削除する。
- 一覧のうち `source_bom_item_id` で一致しない **推定一致** の工程は **手動確認対象** とし、自動削除しない。
- UIでは `影響ステップ数 / 自動削除対象 / 手動確認対象` を分けて表示し、誤認防止のため削除対象範囲を明示する。

## BOM画面の複製系操作

### 1) 別製品へのコピー
- BOM詳細画面の `BOMをコピー` は、**同一親製品の改版用ではなく**、**別の親製品**へ構成を複製する機能とする。
- API: `POST /api/boms/{id}/copy/`
- リクエスト:
  - `new_parent_product_id`
- コピー先BOMの以下はコピー元を引き継ぐ。
  - `version`
  - `valid_from`
  - `valid_to`
  - `is_active`
  - `is_coproduct`
  - `BOMItem` 全件

### 2) 同一親製品の別バージョン作成
- BOM詳細画面に `別バージョン作成` ボタンを表示する。
- この機能は、**親製品を変えずに**、`版` と `有効開始日` を変えた新BOMを作るための機能とする。
- 用途:
  - 設変
  - 外作先切替
  - 将来日切替
  - ルーティング未来版の元データ作成
- API: `POST /api/boms/{id}/duplicate_version/`
- リクエスト:
  - `version` 必須
  - `valid_from` 必須（`YYYY-MM-DD`）
  - `valid_to` 任意（`YYYY-MM-DD`）
  - `is_active` 任意
- 制約:
  - `version` はコピー元と異なる値を必須とする
  - `valid_to` を指定する場合は `valid_to >= valid_from`
  - 既存の `parent_product × version × valid_from` と重複するBOMは作成不可
- 新BOM作成時、以下をコピー元から引き継ぐ。
  - `parent_product`
  - `is_coproduct`
  - `BOMItem` 全件
- UI初期値:
  - `version`: 元版が `vN` 形式なら `v(N+1)` を提案
  - `valid_from`: 元BOMに `valid_to` があれば翌日、無ければ当日
  - `is_active`: コピー元の値を引き継ぐ

## ルーティングマスタ画面（`/masters/routing`）の表示ルール

### 一覧（左ペイン）
- 列は `品番 / 品名 / 既定 / 有効` を表示する。
- 一覧取得の `GET /api/routings/` はヘッダ項目のみ返し、`steps` は含めない。
- 一覧行を選択すると、右ペインは選択した `routing_id` の工程のみを表示する。

### ルーティングヘッダの有効日時
- ルーティングヘッダ（`m_routing`）は `valid_from_datetime` / `valid_to_datetime` を持つ。
- 未設定時は以下のように扱う。
  - `valid_from_datetime=NULL`: 下限なし
  - `valid_to_datetime=NULL`: 上限なし
- 有効ルーティングの判定条件は `is_active=True` かつ `valid_from_datetime <= 基準日時 <= valid_to_datetime`。
- 同一品番で複数ルーティングが同時に有効な場合の優先順は以下とする。
  - `is_default=True`
  - `valid_from_datetime` の新しいもの
  - `id` の大きいもの
- 基準が日付のみの処理では、その日の **08:00** を基準日時として判定する。
  - 例: `2026-04-01` を基準日に渡した場合、`2026-04-01 08:00` 時点で有効なルーティングを採用する。

### 工程一覧（右ペイン）
- ソート順は `step_no` 昇順（同値時は `parallel_group` 昇順）。
- ヘッダ行はスクロール時に固定表示する。
- 旧「備考」列は「親製品」表示に変更し、値は `m_routing_step.remark`（親製品コード）を表示する。
- `hierarchy_path`（階層）と `parallel_group`（並列G）は表示専用（編集不可）とする。
- `使用個数` は整数で編集可能とする。
- 右ペイン上部で `既定 / 有効 / 有効開始日時 / 有効終了日時` を編集・保存できる。
- 工程一覧に `外作先` 列を表示し、値は `m_routing_step.supplier_id` に紐づく `m_supplier.supplier_name` を表示する。

### 工程の手動追加（`/masters/routing`）
- 右ペイン上部に `工程追加` ボタンを持ち、押下時にインライン入力行を表示する。
- 入力項目:
  - `工程番号(step_no)`（必須, 1以上整数）
  - `並列G(parallel_group)`（必須, 1以上整数）
  - `工程(process)`（必須）
  - `ライン(line)`（任意）
  - `外作先(supplier)`（任意）
  - `加工後品目(output_product)`（任意）
  - `時間単位(time_unit)`（`DAY`/`MINUTE`）
  - `LT(日)`（`DAY`時必須, 0以上整数）
  - `所要時間(分)`（`MINUTE`時必須, 1以上整数）
  - `親製品(remark)`（任意）
- 保存は `POST /api/routing-steps/` で行い、成功時は工程一覧を再読込する。

### ルーティング工程追加時の購買ルール（2026-08-24追加）

- 調達区分が `BUY`（購買）の場合、工程は利用者入力に任せず **PURCHASE** へ強制設定する。
- 購買工程では `process_id=NULL` を新規作成しない。
- 目的は、購買ルーティングが受注展開・進度計算で工程未解決にならないようにするためである。

### ルーティング有効期間の使用箇所

有効期間の判定には2種類がある。

- **ポイント判定**（`build_effective_routing_q`）: ある1時点で有効なルーティングを取得
- **レンジ判定**（`build_effective_routing_range_q`）: 指定期間内のどこかで有効なルーティングを取得

| 場面 | 判定方法 | 基準 | ファイル |
|------|---------|------|---------|
| 対象製品判定（在庫・進度計算） | レンジ | `start_date〜end_date` | `inventory_calculator.py` |
| バックログ取り込み（pickup） | レンジ + 日付別選別 | `start_dt〜end_dt` → `plan_date`ごと | `backlog_pickup_service.py` |
| 購買需要取り込み（pickup_purchase） | レンジ | `start_dt〜end_dt` | `backlog_pickup_service.py` |
| 計画保存時の最終品判定 | ポイント（日付ごとOR結合） | 保存対象の各日付 | `production/views.py` |
| バックログ保存時のルーティング解決 | ポイント | `plan_date` | `backlog_save_service.py` |
| 累積LT取得 | ポイント | `now()` | `inventory_calculator.py` |
| 在庫移行検出 | ポイント | `now()` | `production/views.py` |
| 棚卸初期化 | ポイント | 棚卸日 | `stocktake_initializer.py` |
| BOM展開・LT計算 | ポイント | `reference_date` / `now()` | `bom_service.py` |
| マスタ画面の工程表示 | ポイント | `now()` | `masters/views.py` |
| シリアライザの工程取得 | ポイント | `now()` | `serializers.py` |
| 購買画面の設変紐づけ | ポイント | `now()` | `purchase/views.py` |
| 購買ライン特定 | ポイント | `now()` | `backlog_pickup_service.py` |

**備考:**
- レンジ判定を使う場面は「期間を跨ぐルーティング切替」を考慮する必要がある場面（在庫計算、需要取り込み）
- ポイント判定を使う場面は「その時点で正しい1つのルーティング」を確定する場面（保存、表示、LT取得）
- pickup では大枠をレンジで取得した後、`is_step_effective_for_reference(step, plan_date)` で日付ごとに有効ステップを選別する二段階方式を採用

### ルーティング工程の外作先
- `m_routing_step` は `supplier_id`（`m_supplier` へのFK, NULL可）を持つ。
- 丸ごと外作運用では、親ルーティングに外注工程を1行追加し、`supplier_id` で外作先を管理する。

### 変更履歴（`/masters/routing`）
- ルーティングマスタ画面に `変更履歴` ボタンを表示し、選択中ルーティングの変更履歴をモーダルで一覧表示する。
- 履歴一覧の列は `記録日時 / 操作 / 対象 / 変更者 / 内容` とする。
- 対象は以下を含む。
  - ルーティングヘッダの作成 / 更新 / 削除
  - ルーティング工程の作成 / 更新 / 削除
- ヘッダ更新の記録対象は `routing_code / description / is_default / is_active / valid_from_datetime / valid_to_datetime`。
- 工程更新の記録対象は `step_no / hierarchy_path / parallel_group / process / line / supplier / output_product / time_unit / lead_time_days / duration_min / remark`。
- 履歴はバックエンドで自動保存し、画面保存時にフロント側で個別登録処理は行わない。
- 取得APIは `GET /api/routings/{routing_id}/history/` とする。
- 保存先テーブルは `t_routing_change_history` とする。

### 使用個数（`usage_quantity`）算出
- APIレスポンスで `routing-steps` の各行に `usage_quantity` を含める。
- 算出優先順位:
  1. `hierarchy_path` から直上親工程を特定し、親工程の `m_routing_step_material` で `component=当該step.output_product` の数量合計
  2. `remark`（親製品コード）で親工程を特定し、同条件で数量合計
  3. 最上位等で親工程が無い場合は、親製品BOM（`m_bom_item`）の `quantity` で補完

## BOM階層図の表示とExcel出力

- BOMマスタの階層図表示（UI）と Excel出力は、同一の行生成ロジックを使用する。
- UI表示用API: `GET /api/boms/{id}/tree_excel_rows/`
- Excel出力API: `GET /api/boms/{id}/export_excel/`
- 共通列は以下の順序で固定する。  
  `BOM ID / 親製品 / 部番表示 / 製品名 / 階層 / 数量 / 工程 / ライン / 仕入先 / リードタイム(日) / 所要時間(分)`

## BOM取込仕様（CSV / Excel）

### 対象API
- テンプレートCSV: `GET /api/boms/import_template_csv/`
- テンプレートExcel: `GET /api/boms/import_template_xlsx/`
- 取込前チェック: `POST /api/boms/import_check/`
- 取込実行: `POST /api/boms/import_csv/`

### 入力形式
- 取込ファイルは `CSV(.csv)` または `Excel(.xlsx/.xlsm)` を許可する。
- Excelは先頭シート（入力用）を取り込む。
- 必須ヘッダー: `親品番, 子品番, 数量, 調達区分`
- `完成品`列は任意（画面入力で補完可能）。

### 画面入力（取込モーダル）
- `完成品（画面入力）` は必須。
- 行の `完成品` と画面入力が両方ある場合、不一致はエラー。
- 行の `完成品` が空の場合は画面入力値で補完。

### 取込前チェック（import_check）
- 最初に `完成品/親品番/子品番` を `M_PRODUCT`（`Product`）へ照合し、未登録が1件でもあればエラー返却。
- その後、区分別必須チェック・数値チェック・マスタ照合（工程/ライン/仕入先）・既存BOM重複チェックを行う。
- 既存BOM重複チェックは `parent_product × version × valid_from` の一致を対象とする。

### 区分別チェック（import_check / import_csv 共通）
- `MAKE`:
  - `工程コード` 必須
  - `ラインコード` 必須
  - `時間単位` 必須（`分` or `日`）
  - `時間単位=分` の場合 `所要時間(分) > 0` 必須
  - `時間単位=日` の場合 `リードタイム(日) > 0` 必須
- `BUY`:
  - `仕入先コード` 必須
  - `時間単位=日` 必須
  - `リードタイム(日) > 0` 必須
  - `工程コード` は入力値を使わず **PURCHASE** に強制する
  - `ラインコード` は入力値を使わず **仕入先に紐づく購買ライン** に強制する
- `SUBCON`:
  - `仕入先コード` 必須
  - `時間単位=日` 必須
  - `リードタイム(日) > 0` 必須
  - `工程コード` 空欄時は `G` に自動補完

### BOM画面の購買明細入力ルール（2026-08-24追加）

- BOM子部品で調達区分に `購買` を選んだ場合、保存時は次を自動補完する。
  - 工程: **PURCHASE**
  - ライン: **選択した仕入先に紐づく購買ライン**
- 仕入先未選択の購買明細は保存不可とする。
- 目的は、BOM起点で生成されるルーティングや需要に `process_id=NULL` / `line_id不整合` を残さないためである。

### 数値チェック
- `数量`: 数値かつ `> 0`
- `リードタイム(日)`: 整数かつ `>= 0`（区分条件により `> 0` を追加要求）
- `所要時間(分)`: 整数かつ `>= 0`（区分条件により `> 0` を追加要求）

### Excelテンプレート仕様
- シート構成:
  - `入力用`
  - `使用説明`
  - `工程`（DB一覧）
  - `ライン`（DB一覧）
  - `仕入先`（DB一覧）
- 入力用シートのプルダウン:
  - 調達区分（G列）: `外注 / 購買 / 自社製造`
  - 時間単位（K列）: `分 / 日`

## 変更履歴

### 2026-08-24: 購買時の工程・ライン強制ルールを追加
- ルーティング工程の手動追加で、調達区分が `BUY` の場合は工程を **PURCHASE** に強制する仕様を追加した。
- BOM子部品追加・取込で、調達区分が `BUY` の場合は工程を **PURCHASE**、ラインを **仕入先に紐づく購買ライン** に強制する仕様を追加した。
- これにより、購買データ起点の `process_id=NULL` を新規に作らない運用へ統一した。

### 2026-08-18: BOM明細削除時の削除対象表示を明確化
- BOM明細削除確認で、関連ルーティング工程を `自動削除対象` と `手動確認対象` に分けて表示する仕様を追加した。
- `source_bom_item_id` 一致の工程だけを、利用者チェック時に `BOMItem` 削除と同時に自動削除するよう整理した。
- 推定一致工程は一覧表示のみとし、自動削除対象に含めないことを明記した。

### 2026-07-25: BOM別バージョン作成を追加
- BOM詳細画面に `別バージョン作成` ボタンを追加し、同一親製品のまま `版` と `有効開始日` を変えた新BOMを作成できるようにした。
- `POST /api/boms/{id}/duplicate_version/` を追加し、BOMヘッダと明細一式を複製できるようにした。
- `BOMをコピー` は引き続き「別の親製品へのコピー」専用とし、改版用途とは分離した。

### 2026-07-24: ルーティング変更履歴の保存・表示を追加
- ルーティングヘッダ / ルーティング工程の作成・更新・削除時に、`t_routing_change_history` へ変更履歴を自動保存するようにした。
- `/masters/routing` に `変更履歴` ボタンを追加し、選択中ルーティングの履歴をモーダルで確認できるようにした。
- `GET /api/routings/{routing_id}/history/` を追加し、記録日時・操作・対象・変更者・変更内容を返すようにした。
