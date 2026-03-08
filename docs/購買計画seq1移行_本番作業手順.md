# 購買計画 sequence_no=1 移行 本番作業手順

**作業日**: 2026年3月9日（月）予定
**所要時間**: 約10分
**作業環境**: Adminer（本番DB直接操作）+ git push

---

## 背景

購買計画の `plan_qty` がこれまで `sequence_no=0`（基礎データ行）に保存されていたため、
計画変更時に `adjust_qty` や `actual_shipment_qty` が消えるバグがあった。
修正版コードでは `sequence_no=1` に保存するよう変更したため、既存の本番DBデータも移行が必要。

---

## 作業手順

### Step 1: コードをデプロイ

本番サーバーで以下を実行（またはGitHub経由でPULL）：

```bash
git pull origin main
docker-compose restart pm-backend
```

---

### Step 2: Adminerで移行前の件数を確認

```sql
SELECT COUNT(*)
FROM pm_db.line_backlog lb
JOIN pm_db.m_line ml ON lb.line_id = ml.id
WHERE ml.line_type = 'PURCHASE'
  AND lb.sequence_no = 0
  AND lb.plan_qty > 0;
```

> 件数をメモしておく（移行後の確認に使う）。

---

### Step 3: seq=1 レコードを作成

```sql
INSERT INTO pm_db.line_backlog (
    plan_date, process_id, product_id, line_id,
    sequence_no, plan_qty, plan_id,
    demand_qty_plan, order_qty, actual_qty,
    stock_qty, planned_stock_qty, adjust_qty,
    scrap_adjust_qty, scrap_qty, actual_shipment_qty,
    progress_qty, planned_progress_qty,
    is_stocktake_fix, updated_at
)
SELECT
    lb.plan_date,
    lb.process_id,
    lb.product_id,
    lb.line_id,
    1,
    lb.plan_qty,
    CONCAT(p.product_code, '_', DATE_FORMAT(lb.plan_date, '%Y%m%d'), '_', lb.plan_qty, '_1'),
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    NOW()
FROM pm_db.line_backlog lb
JOIN pm_db.m_line ml ON lb.line_id = ml.id
JOIN pm_db.m_product p ON lb.product_id = p.id
WHERE ml.line_type = 'PURCHASE'
  AND lb.sequence_no = 0
  AND lb.plan_qty > 0
ON DUPLICATE KEY UPDATE
    plan_qty = VALUES(plan_qty),
    plan_id = VALUES(plan_id);
```

---

### Step 4: seq=0 の plan_qty・plan_id をクリア

```sql
UPDATE pm_db.line_backlog lb
JOIN pm_db.m_line ml ON lb.line_id = ml.id
SET lb.plan_qty = 0, lb.plan_id = NULL
WHERE ml.line_type = 'PURCHASE'
  AND lb.sequence_no = 0
  AND lb.plan_qty > 0;
```

---

### Step 5: 移行結果を確認

```sql
-- seq=0 に plan_qty が残っていないことを確認（0件であればOK）
SELECT COUNT(*)
FROM pm_db.line_backlog lb
JOIN pm_db.m_line ml ON lb.line_id = ml.id
WHERE ml.line_type = 'PURCHASE'
  AND lb.sequence_no = 0
  AND lb.plan_qty > 0;

-- seq=1 レコードが存在することを確認（Step2の件数と一致すればOK）
SELECT COUNT(*)
FROM pm_db.line_backlog lb
JOIN pm_db.m_line ml ON lb.line_id = ml.id
WHERE ml.line_type = 'PURCHASE'
  AND lb.sequence_no = 1
  AND lb.plan_qty > 0;
```

---

### Step 6: 画面で動作確認

1. **仕入れ実績入力（一括）** → 仕入先・計画日を指定して計画数が表示されること
2. **仕入れ在庫/残量一覧** → 計画行が正常に表示されること
3. **仕入れ計画入力** → 計画数の入力・保存が正常にできること

---

## 問題が発生した場合

### Step 3 で `Duplicate entry` エラー

既に seq=1 レコードが存在する品番がある。`ON DUPLICATE KEY UPDATE` により上書きされるので通常は問題ない。

### Step 5 確認で seq=0 に残存がある

Step 4 のUPDATE文を再実行する。

---

## 変更されたファイル（参考）

| ファイル | 変更内容 |
| --- | --- |
| `pm_backend/apps/production/management/commands/generate_production_plan.py` | `apply_purchase_plan_to_backlog` を seq=1 保存に変更 |
| `pm_backend/apps/purchase/views.py` | `PurchaseActualBulkItemsView` の取得クエリを seq=1 に変更 |
| `pm-ui/src/views/purchase/PurchasePlanInput.vue` | `savePlan()` に `sequence_no: 1` を追加 |
