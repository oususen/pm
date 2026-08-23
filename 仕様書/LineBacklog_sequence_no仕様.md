# LineBacklog sequence_no 管理ルール仕様書

## 概要

`LineBacklog` モデルの `sequence_no` フィールドは、生産計画の順序管理と在庫計算の基礎データ管理において重要な役割を果たします。
本仕様書では、`sequence_no` の値による役割の違いと、データ操作時の取り扱いルールを定義します。

## sequence_no の役割と定義

### 制約（2026-03-08更新）
- `NOT NULL` かつ **デフォルト0** とする。
- `sequence_no = 0` は基礎データの代表行として扱う。
- **生産計画**・**購買計画**ともに `sequence_no = 0` を計画行として使わない（計画は `sequence_no > 0`）。
- **購買計画**では `sequence_no = 1` 固定（同日複数ロット管理なし）。`plan_qty` は必ず seq=1 に保存する。
- `sequence_no > 0` は計画レコード専用。`plan_qty` / `sequence_no` を持つロットは必ず1以上。
- `sequence_no = 0` のレコードは削除禁止。計画削除時も温存する。
- 可能なら DB 側に `CHECK (sequence_no >= 0)` を追加する。

### データ区分

| sequence_no | 役割 | 用途 | 削除可否 |
|------------|------|------|---------|
| **0** | 基礎データレコード | 在庫・需要・実績・仕損・進度・調整など計画以外の情報を一元管理 | ❌ **削除禁止 / plan_qty は常に0** |
| **1**（購買） | 計画レコード（固定） | 購買計画の仕入れ数量（1ロット固定） | ✅ **削除可能** |
| **1, 2, 3...**（生産） | 計画レコード | 生産計画の順序（人間が採番） | ✅ **削除可能** |

### 詳細説明

#### 1. sequence_no = 0（基礎データレコード）
- **用途**: 在庫計算の基礎となるデータを一元管理
  - 在庫数（stock_qty）
  - 需要数（order_qty）
  - **実績数（actual_qty）** ← 実績もここに保存
  - 仕損数（scrap_qty）
  - 調整数（adjust_qty）
  - その他計画に依存しない固定データ

- **特徴**:
  - 計画変更時も保持される
  - 在庫計算ロジックの基準となる
  - 日付・ライン・製品・工程ごとに1レコードのみ存在

- **作成タイミング**:
  1. **需要取り込み時** (`pickup` アクション)
     - 最終品の受注データから `order_qty` を設定
     - `LineBacklog.objects.update_or_create(..., sequence_no=0, defaults={'order_qty': ...})`

  2. **購買需要展開時** (`pickup_purchase` アクション)
     - 購買・外注部品の需要を展開
     - 親製品の `plan_qty` × BOM個数 で需要を計算
     - `BUY` は `PURCHASE`、`SUBCON` は `G` / 外作工程で `process_id` を決定
     - 需要は「仕入先ラインからの出庫需要」を意味し、同一仕入先ライン・同一製品・同一日付の需要行は1つに保つ
     - 別工程行が同日に共存していても、業務上の別需要とはみなさず誤展開として補正対象にする
     - `LineBacklog.objects.update_or_create(..., sequence_no=0, defaults={'order_qty': ...})`

  3. **中間品需要展開時** (`pickup` アクション内)
     - 後工程（RoutingStep）またはBOMから需要を逆算
     - 後ラインの `plan_qty` × BOM個数 で需要を計算
     - `LineBacklog.objects.update_or_create(..., sequence_no=0, defaults={'order_qty': ...})`

  4. **実績記録時** (`ProcessRealtime`)
     - 工程作業記録から `actual_qty` を設定
     - `LineBacklog.objects.get_or_create(..., sequence_no=0, defaults={'actual_qty': ...})`
     - 既存レコードがあれば `actual_qty` を加算

- **更新ルール**:
  - **需要展開時**: `order_qty` と `demand_qty_plan` のみ更新
    - `pickup` / `pickup_purchase` は `plan_qty` を更新しない（既存の計画入力値を保持）
  - **実績記録時**: `actual_qty` のみ更新（加算）
  - `plan_qty` は **sequence_no=0 には保存しない**。購買計画は seq=1、生産計画は seq≥1 に保存する。
  - `stock_qty`・`planned_stock_qty`・`progress_qty`・`planned_progress_qty` は在庫計算処理が seq=0 に書き込む
  - 常に `get_or_create` または `update_or_create` で既存レコードを更新または新規作成

- **削除タイミング**: **削除禁止** - データ整合性維持のため常に保持
- **例外**:
  - 誤ったルーティング作成や誤展開により不要な基礎データ行が作成された場合に限り、保守用API `POST /api/line-backlogs/delete-progress-group/` で削除を許可する。
  - 対象は `line_id + process_id + product_id + 表示期間` で一致する `sequence_no=0` 行のみ。
  - 想定用途は「進度のみ」画面での誤展開データ除去であり、通常運用の計画削除・需要再計算では使用しない。

#### 2. sequence_no = 1（購買計画レコード）

- **用途**: 購買品の仕入れ計画数量を管理（1ロット固定）
  - 同日複数ロット管理なし → 常に `sequence_no = 1`

- **特徴**:
  - `plan_qty` と `plan_id` のみ保持（在庫・需要・実績は seq=0 に保存）
  - フロントエンド（`PurchasePlanInput.vue`）が `sequence_no: 1` を明示的に送信
  - 計画変更時は seq=1 レコードのみ削除・再作成。seq=0 は保護される

- **作成タイミング**: 仕入れ計画保存時（`save` エンドポイント）
  - フロントから `sequence_no=1` を受け取り `update_or_create`
  - `plan_id` = `{product_code}_{YYYYMMDD}_{qty}_1`

- **削除タイミング**:
  - `plan_qty=0` で保存 → `filter(plan_id=old_plan_id).delete()` で seq=1 のみ削除
  - `plan_qty` 変更時 → 旧 `plan_id` の seq=1 レコードを削除し新規作成

#### 3. sequence_no = 1, 2, 3...（生産計画レコード）

- **用途**: 生産計画の順序を管理
  - 同じ日に同じ製品を複数回作る場合、各ロットを区別
  - 例: 1/14に製品Aを午前（sequence_no=1）と午後（sequence_no=2）に生産

- **特徴**:
  - **sequence_no は人間が採番**（自動採番ではなくユーザーが順序を指定）
  - 計画数量（plan_qty）を持つ
  - ガントチャート生成の基礎データ
  - 在庫計算時は `ORDER BY plan_date, sequence_no` でソート

- **作成タイミング**: 生産計画保存時（`LinePlan.save`）
  - ユーザーが入力した計画データから生成

- **削除タイミング**: 計画変更時に削除・再作成が可能
  - 計画保存時に `sequence_no > 0` のレコードを削除
  - 新しい計画データで再作成

## データベース制約

### unique_together
```python
unique_together = [('plan_date', 'process', 'product', 'line', 'sequence_no')]
```

この制約により、同じ日付・工程・製品・ラインで、異なる `sequence_no` を持つ複数レコードが共存できます。
ただし、`pickup_purchase` の業務仕様では **同一仕入先ライン・同一製品・同一日付の基礎需要行を複数工程に分けて共存させてはならない**。
`process_id` は購買需要行の所属工程属性であり、同一需要を二重化する理由にはならない。

## 実装上の注意事項

### 1. 生産計画保存時（LinePlan.save）

- `sequence_no > 0` のみを削除・再作成する。`sequence_no = 0` は決して削除しない。
- 入力値が空/0/未指定の場合は自動採番し、最小値は1とする（0は採番しない）。

**処理フロー**:
```python
# 1. 該当範囲のLinePlanを削除
LinePlan.objects.filter(
    line_id=line_id,
    plan_date__in=affected_dates,
    product_id__in=affected_products
).delete()

# 2. 該当範囲のLineGanttPlanを削除
LineGanttPlan.objects.filter(
    line_id=line_id,
    plan_date__in=affected_dates,
    product_id__in=affected_products
).delete()

# 3. 該当範囲のLineBacklogを削除（計画レコードのみ）
LineBacklog.objects.filter(
    line_id=line_id,
    plan_date__in=affected_dates,
    product_id__in=affected_products,
    sequence_no__gt=0  # 重要: sequence_no > 0 のみ削除
).delete()

# 4. 新規作成
# 自動採番機能付き
def get_next_sequence(plan_date_obj):
    """自動採番: 日付ごとに連番を生成"""
    cache_key = (line_id, plan_date_obj)
    if cache_key not in next_seq_cache:
        next_seq_cache[cache_key] = 1
    next_seq = next_seq_cache[cache_key]
    next_seq_cache[cache_key] = next_seq + 1
    return next_seq

# sequence_no未指定時の処理
seq_in = it.get('sequence_no')
if seq_in in (None, '', 0):
    # sequence_noが指定されていない場合は自動採番
    if plan_qty_value > 0:
        sequence_no = get_next_sequence(plan_date_obj)
    else:
        # plan_qty = 0 の場合はスキップ（削除扱い）
        continue
else:
    # sequence_noが指定されている場合はそのまま使用
    sequence_no = int(seq_in)

LinePlan.objects.create(..., sequence_no=sequence_no)
```

**重要**:
- `sequence_no__gt=0` により、基礎データレコード（sequence_no=0）を保護
- 計画レコード（sequence_no > 0）のみ削除・再作成
- sequence_no=0 のレコードには需要・実績・在庫データが保存されているため削除禁止

**自動採番の利点**:
- ユーザーがsequence_noを指定し忘れても保存可能
- 日付ごとに自動的に1から連番を採番
- 手動で順序を指定したい場合は明示的に指定可能

### 2. 工程作業実績記録時（ProcessRealtime）

```python
# 実績は sequence_no=0 の基礎データレコードに保存
backlog, created = LineBacklog.objects.get_or_create(
    line=line,
    process=process,
    product=product,
    plan_date=plan_date,
    sequence_no=0,  # 実績は sequence_no=0 に保存
    defaults={
        'actual_qty': int(qty),
    }
)

if not created:
    # 既存レコードに実績を加算
    backlog.actual_qty = (backlog.actual_qty or 0) + int(qty)
    backlog.save(update_fields=['actual_qty'])
```

**重要**:
- 実績は `sequence_no=0` のレコードに保存
- 需要データ（order_qty）と実績データ（actual_qty）が同じレコードで管理される
- レコードが存在しない場合は自動作成

### 3. 在庫計算時

- 基礎行（sequence_no=0）を代表行として必ず使用する。存在しない場合は新たに sequence_no=0 を作成してから計算に用いる（計画行を代表にしない）。
- 進度・在庫・計画在庫・実績出庫などの計算・保存は **必ず sequence_no=0** に行う。
- 対象期間の日付に行自体が無い場合も、日次連続性を保つため `sequence_no=0` の基礎行を補完してから計算する。
- 日付欠損を補完する際の `process_id` は、既存 `sequence_no=0` 行の工程を優先し、無ければ直前に存在した日の工程を引き継ぐ。
- **在庫・計画在庫・進度の格納先**: 日付ごとに補完または既存の `sequence_no=0` 基礎データレコードへ格納する。

```python
# 日付とsequence_noでソート
backlogs = LineBacklog.objects.filter(
    line_id=line_id,
    product_id=product_id,
    plan_date__range=[start_date, end_date]
).order_by('plan_date', 'sequence_no', 'id')

# 日付ごとにグループ化
by_date = {}
for backlog in backlogs:
    by_date.setdefault(backlog.plan_date, []).append(backlog)

# 同じ日の複数レコードを集計
for plan_date in sorted(by_date.keys()):
    rows = by_date[plan_date]
    plan_total = sum(r.plan_qty or 0 for r in rows)
    actual_total = sum(r.actual_qty or 0 for r in rows)
    # ...
```

## データ例

### 正常な状態（1/14の製品111）

| id | plan_date | product_id | sequence_no | plan_qty | actual_qty | order_qty | 説明 |
|----|-----------|------------|-------------|----------|------------|-----------|------|
| 100 | 2026-01-14 | 111 | **0** | 0 | 0 | 12 | 基礎データ（需要12） |
| 101 | 2026-01-14 | 111 | **1** | 8 | 0 | 0 | 1番ロット（午前） |
| 102 | 2026-01-14 | 111 | **2** | 4 | 0 | 0 | 2番ロット（午後） |

### 計画変更後（順序入れ替え）

**変更前**:
- 製品111: sequence_no=1
- 製品113: sequence_no=2

**変更操作**:
- 製品111を sequence_no=2 に変更
- 製品113を sequence_no=1 に変更

**処理**:
1. sequence_no > 0 のレコードを削除（id=101, 102削除）
2. sequence_no = 0 のレコードは保持（id=100保持）
3. 新しい順序で再作成

## トラブルシューティング

### 問題: ガントチャートが重複表示される

**原因**: 古い計画レコード（sequence_no > 0）が削除されずに残っている

**解決**:
```sql
-- 該当期間の古い計画レコードを削除
DELETE FROM line_backlog
WHERE line_id = 11
  AND plan_date BETWEEN '2026-01-14' AND '2026-01-14'
  AND product_id = 113
  AND sequence_no > 0;
```

### 問題: 在庫計算が狂う

**原因**: sequence_no = 0 の基礎データレコードが削除された

**解決**: 基礎データレコードを復元（手動または工程展開処理の再実行）

## 変更履歴

| 日付 | 版 | 変更内容 | 変更者 |
|------|-----|----------|--------|
| 2026-01-14 | 1.0 | 初版作成 | Claude Sonnet 4.5 |
| 2026-01-14 | 1.1 | 自動採番機能の説明を追加 | Claude Sonnet 4.5 |
| 2026-02-08 | 1.2 | sequence_no を NOT NULL/デフォルト0とする運用を明記。0は基礎行専用・削除禁止、計画は1以上を使用 | ChatGPT |
| 2026-02-21 | 1.3 | 生産計画と購買計画での `sequence_no=0` 運用差を明記。`pickup_purchase` が `plan_qty` を更新しないことを追記 | Codex |
| 2026-03-08 | 1.4 | 購買計画を seq=1 固定に変更。seq=0 の plan_qty 運用を廃止。生産計画の sequence_no は人間採番であることを明記 | Claude Sonnet 4.6 |
| 2026-06-27 | 1.5 | 誤展開した基礎データ行を進度のみ画面から保守削除できる例外運用（`delete-progress-group`）を追記 | Codex |
| 2026-07-21 | 1.6 | `pickup_purchase` の基礎需要行は同一仕入先ライン・同一製品・同一日付で一意とし、別工程共存を誤展開として補正対象にする運用を追記 | Codex |

## 関連ドキュメント

- `pm_backend/apps/production/models_line_backlog.py` - LineBacklogモデル定義
- `pm_backend/apps/production/views.py` - LinePlan保存処理
- `pm_backend/apps/production/inventory/inventory_calculator.py` - 在庫計算ロジック
- Commit 9b59e0e - sequence_noをunique_togetherに追加した変更
