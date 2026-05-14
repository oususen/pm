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

### ルーティング工程の外作先
- `m_routing_step` は `supplier_id`（`m_supplier` へのFK, NULL可）を持つ。
- 丸ごと外作運用では、親ルーティングに外注工程を1行追加し、`supplier_id` で外作先を管理する。

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
  - `工程コード` 入力不可
- `SUBCON`:
  - `仕入先コード` 必須
  - `時間単位=日` 必須
  - `リードタイム(日) > 0` 必須
  - `工程コード` 空欄時は `G` に自動補完

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
