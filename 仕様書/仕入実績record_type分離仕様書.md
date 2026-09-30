# 仕入実績 record_type 分離仕様書

## 1. 目的

仕入の入荷実績は、生産実績と同じ `t_process_realtime_record`（`production.ProcessRealtimeRecord`）に保存している。
従来は `record_type='PRODUCTION'` で保存し、仕入かどうかは `event_data.source` でしか区別できなかった。
生産数の集計に仕入分が混ざらないよう、仕入実績を `record_type='PURCHASE'` で保存する。

## 2. データ定義

| record_type | 意味 | 入力元（`event_data.source`） |
|---|---|---|
| `PRODUCTION` | 生産完成（社内生産の実績） | 工程実績入力・作業者アクション・手修正など（仕入の入力元以外） |
| `PURCHASE` | 仕入実績（入荷実績） | `PURCHASE_ACTUAL_INPUT`（仕入れ実績入力）、`PURCHASE_RECEIVING`（検収）、`PURCHASE_RECEIVING_MOBILE`（スマホ検収） |

- `PURCHASE` と仕入の入力元は必ず対にする。`ProcessRealtimeCreateSerializer.validate` で次を400エラーにする。
  - `PURCHASE` なのに `event_data.source` が仕入の入力元以外
  - `PURCHASE` なのに `event_data.line_id`（仕入先ライン）が整数でない・未指定
  - `PURCHASE` 以外なのに `event_data.source` が仕入の入力元
- 入力元の一覧は `production.models_process_realtime.PURCHASE_ACTUAL_SOURCES` に定義する。
- 工程は仕入先に関係なく `G`（外作）または `PURCHASE`（購買）で、工程にラインは持たない。仕入先ごとの区別は `event_data.line_id`（仕入先ライン、`line_type='PURCHASE'`）で行う。

## 3. LineBacklog への反映（従来と同じ）

`PURCHASE` も `PRODUCTION` と同じく出来高レコード（`OUTPUT_RECORD_TYPES`）として扱い、反映内容は従来から変えない。

| 保存先 | フィールド | 内容 | 処理 |
|---|---|---|---|
| 仕入先ライン × 工程 × 品番 × 入荷日（`sequence_no=0`） | `actual_qty` | 入荷実績の合計 | `purchase.views._reconcile_purchase_actual_backlog_for_key`（入力・訂正・削除のたびに `record_type='PURCHASE'` のレコード合計で再集計） |
| BOM子品目（`sequence_no=0`） | `actual_shipment_qty` | 入荷数 × BOM員数を加算 | `update_line_backlog_actual_shipment` |
| 工程のライン（`sequence_no=0`） | `actual_qty` | 工程 `G`／`PURCHASE` はラインを持たないため反映なし | `update_line_backlog_production` |

連産品（仮想セット品番）の子実績を展開する場合、子実績の `record_type` は親と同じ値にし、仕入の場合は `source`・`supplier_id`・`line_id`・`arrival_date` を引き継ぐ。

## 4. 参照箇所

| 画面・処理 | 条件 |
|---|---|
| 仕入入力後の actual_qty 再集計、仕入れ実績照会、実績訂正・削除、検収履歴 | `record_type='PURCHASE'` |
| スマホ検収の確認一覧・確認済み更新 | `record_type='PURCHASE'` かつ `event_data.source='PURCHASE_RECEIVING_MOBILE'` |
| 計画から登録した実績の登録済み数・未納残数（`purchase/services/actual_plan.py`） | `record_type='PURCHASE'` |
| 納入実績整合チェック | `record_type='PURCHASE'`（入力元3種すべて） |
| 生産実績整合チェック | `record_type='PRODUCTION'` |
| 社内AI 生産数集計（`ai/services/chat_service.py`） | `record_type='PRODUCTION'` |
| 社内AI 入荷ビュー `v_ai_purchase_receipt`（`ai/0013`） | `record_type='PURCHASE'` |

## 5. 既存データの移行（本番）

既存の仕入実績（`record_type='PRODUCTION'` かつ仕入の入力元）を `PURCHASE` へSQLで更新する。
コードと既存データの record_type が食い違う間に仕入を入力すると、再集計で仕入先ラインの `actual_qty` が上書きされるため、次の順序を必ず守る。

1. 仕入の入力（仕入れ実績入力・検収・スマホ検収）を止める。
2. 移行前の確認（6章の①②）を実行して結果を控える。
3. `git push` → 本番で pull・ビルド。
4. `docker exec -it pm-backend python manage.py migrate`（`ai.0013` で `v_ai_purchase_receipt` を作り直す）。
5. 直ちに次のSQLを実行する。

```sql
-- 実行前の件数（この件数を控える）
SELECT COUNT(*) cnt, SUM(qty) qty FROM t_process_realtime_record
WHERE record_type='PRODUCTION'
  AND JSON_UNQUOTE(JSON_EXTRACT(event_data,'$.source')) IN ('PURCHASE_ACTUAL_INPUT','PURCHASE_RECEIVING','PURCHASE_RECEIVING_MOBILE');

START TRANSACTION;
UPDATE t_process_realtime_record SET record_type='PURCHASE'
WHERE record_type='PRODUCTION'
  AND JSON_UNQUOTE(JSON_EXTRACT(event_data,'$.source')) IN ('PURCHASE_ACTUAL_INPUT','PURCHASE_RECEIVING','PURCHASE_RECEIVING_MOBILE');
-- PURCHASE の件数・数量が実行前と同じで、PRODUCTION 側に仕入の入力元が残っていないこと
SELECT record_type, COUNT(*) cnt, SUM(qty) qty FROM t_process_realtime_record
WHERE JSON_UNQUOTE(JSON_EXTRACT(event_data,'$.source')) LIKE 'PURCHASE%'
GROUP BY record_type;
COMMIT;   -- 一致しなければ ROLLBACK;
```

6. 移行後の確認（6章の①②③）を実行し、移行前と一致したら仕入の入力を再開する。

## 6. 移行前後の確認

UPDATE は `t_process_realtime_record.record_type` だけを変更し、`line_backlog` は変更しない。

```sql
-- ① LineBacklog の実績合計（移行前後で同じであること）
SELECT l.line_type, SUM(b.actual_qty) actual_qty, SUM(b.actual_shipment_qty) actual_shipment_qty, COUNT(*) cnt
FROM line_backlog b JOIN m_line l ON l.id=b.line_id
WHERE b.sequence_no=0
GROUP BY l.line_type;

-- ② 仕入れ実績照会と同じ対象の件数・数量（移行前は PRODUCTION＋入力元、移行後は PURCHASE で同じ値になること）
SELECT DATE_FORMAT(timestamp,'%Y-%m') ym, COUNT(*) cnt, SUM(qty) qty
FROM t_process_realtime_record
WHERE JSON_UNQUOTE(JSON_EXTRACT(event_data,'$.source')) IN ('PURCHASE_ACTUAL_INPUT','PURCHASE_RECEIVING','PURCHASE_RECEIVING_MOBILE')
GROUP BY ym ORDER BY ym;

-- ③ 移行後：生産実績に仕入の入力元が残っていないこと（0件）
SELECT COUNT(*) FROM t_process_realtime_record
WHERE record_type='PRODUCTION'
  AND JSON_UNQUOTE(JSON_EXTRACT(event_data,'$.source')) IN ('PURCHASE_ACTUAL_INPUT','PURCHASE_RECEIVING','PURCHASE_RECEIVING_MOBILE');
```

あわせて、設定 → スケジュールタスクから「納入実績整合チェック」「生産実績整合チェック」を比較モードで移行前後に1回ずつ実行し、差分件数が増えていないことを確認する。
在庫・進度の再計算は `line_backlog` を入力とするため、①が一致していれば再計算結果も変わらない。
