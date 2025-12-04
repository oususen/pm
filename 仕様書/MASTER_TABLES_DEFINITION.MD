# MASTER_TABLES_DEFINITION_v3.MD
（段階BOM＋セル工程・時間運用＋ライン既定LT／購買LT 対応／time_unit 追加／m_customer 追加／整合性強化／量産セル流し向けのフロー・並列対応）

## 変更サマリ（v2→v3）
- `m_routing_step` に **`time_unit ENUM('DAY','MINUTE')`** を追加（混在単位の明確化）。
- `m_customer` テーブルを **スキーマ＆ERに正式追加**。
- `m_bom_item` に **調達区分と仕入先の整合チェック**（CHECK制約）を追加。
- `m_line_default` のPKは **line_id 単独** に統一（ER図表現を修正）。
- **受注テーブル (`t_order`, `t_order_line`) と取込ステージング (`stg_order_raw`, `stg_order_daily`) を追加**、`t_schedule_detail.order_id` と連携。
- サンプル: ルーティング `step_no` を **連番** に修正、`time_unit` を明示。
- サイクルタイム参照の基準を**m_routing_step_output.output_product_id**に統一。
- 量産セル流し向けに **工程タイプ（FLOW / PARALLEL_POOL）** と **バッファ時間** を追加、サイクルに **yield_rate** を保持。

---

# 1. 製品 `m_product`
| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| product_code | VARCHAR(30) UNIQUE | 品番コード |
| product_name | VARCHAR(100) | 品名 |
| category | VARCHAR(20) | 集合/単品/材料/購入品（実運用はENUM想定） |
| unit | VARCHAR(10) | 単位 |
| standard_lt_days | INT NULL | 完成品標準LT（日） |
| self_lt_days | INT NULL | 親内オフセット（日） |
| is_final_product | TINYINT(1) DEFAULT 0 | 最終製品 |
| is_phantom | TINYINT(1) DEFAULT 0 | 見なし組立 |
| is_active | TINYINT(1) DEFAULT 1 | |
| created_at/updated_at | DATETIME | |

---

# 2. 得意先 `m_customer`（新規・正式追加）
| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| customer_code | VARCHAR(20) UNIQUE | |
| customer_name | VARCHAR(100) | |
| short_name | VARCHAR(40) NULL | |
| calendar_id | BIGINT FK NULL | 稼働カレンダ |
| is_active | TINYINT(1) DEFAULT 1 | |
| created_at/updated_at | DATETIME | |

---

# 3. 工程 `m_process`（変更なし）

# 4. ライン `m_line`（変更なし）

## 4.1 ライン既定LT `m_line_default`
- PK: `line_id`（単独）

## 4.2 製品×ラインLT `m_line_product_lt`
- 複合PK: `(line_id, product_id)`

> **展開ルール**：初期生成時、`m_routing_step` の `time_unit='DAY'` の行に対して、  
> `m_line_product_lt` があればそれを、なければ `m_line_default` を参照して `lead_time_days` を埋める（下記SQL参照）。

---

# 5. ルーティング `m_routing` / `m_routing_step`
## 5.1 `m_routing`
- 製品×版のヘッダ

## 5.2 `m_routing_step`
| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| routing_id | BIGINT FK | |
| step_no | INT | 連番（1..n） |
| process_id | BIGINT FK | |
| line_id | BIGINT FK NULL | |
| step_type | ENUM('FLOW','PARALLEL_POOL') DEFAULT 'FLOW' | 流し/並列プール |
| **time_unit** | **ENUM('DAY','MINUTE')** | 単位の明示 |
| lead_time_days | INT NOT NULL DEFAULT 0 | 日単位（`time_unit='DAY'`で使用） |
| start_offset_min | INT NULL | 分オフセット |
| duration_min | INT NULL | 分所要（段取り+サイクル×数量） |
| remark | VARCHAR(200) NULL | |
| created_at/updated_at | DATETIME | |

---

# 6. 工程出来高 `m_routing_step_output`
- ステップ完了で出来上がる **WIP/製品** を定義。
- サイクルタイム参照の基準は **この `output_product_id`** を用いる。

---

# 7. サイクルタイム `m_cycle_time`
- 製品×工程×ラインの秒/個 と 段取り（分）、歩留まり（yield_rate）
- 所要時間計算: `setup_time_min + cycle_time_sec * qty / 60` をベースに、`yield_rate` で実行数量を補正

---

# 8. 工程パラメータ `m_routing_step_param`
- ロット、移送バッチ、着手条件、バッファ数量（target/max）、バッファ時間（前後）、日内時間枠（分）
- `step_type='FLOW'` ではバッファをWIPの緩衝に使い、`'PARALLEL_POOL'` ではプールキャパと組み合わせて所要日数を算出

---

# 9. 構成 `m_bom` / `m_bom_item`
- 段階BOM
- `m_bom_item.sourcing_type`（MAKE/BUY/SUBCON）と `supplier_id` 整合の **CHECK制約** を追加。

---

# 10. 仕入先 `m_supplier` / `m_supplier_item`
- 仕入先×品目に `purchase_lt_days` を保持（投入日−LT＝手配日）。

---

# 11. カレンダ `m_calendar` / `m_calendar_day`
- `work_minutes` を持ち、日跨ぎ計算を支援。

---

# 12. 主要制約・整合ルール
- **時間単位**：`time_unit='DAY'` → `lead_time_days` 必須、`'MINUTE'` → `duration_min` 必須。
- **工程タイプ**：`step_type='FLOW'` は逐次流し、`'PARALLEL_POOL'` は同一加工を並列に裁くプール。キャパはサイクルタイム×稼働分/日で算出。
- **調達整合**：`sourcing_type='BUY'` ⇒ `supplier_id NOT NULL`。`MAKE/SUBCON` ⇒ `supplier_id IS NULL` を推奨。
- **サイクル参照**：`m_routing_step_output.output_product_id` を `m_cycle_time.product_id` と紐付けて所要を算出。

# 13. 受注（ヘッダ/明細）＋取込ステージング
## 13.1 受注ヘッダ `t_order`
| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| customer_id | BIGINT FK | `m_customer` |
| order_no | VARCHAR(50) | 受注番号/送付No |
| order_type | ENUM('FIRM','FORECAST') | 確定/内示 |
| version_no | VARCHAR(20) | 版管理（内示差し替え時など、デフォルト`v1`） |
| source_system/source_file | VARCHAR | 取込元識別 |
| order_date | DATE NULL | 受注日など |
| freeze_from | DATE NULL | 凍結開始（必要に応じて使用） |
| status | ENUM('OPEN','CLOSED','CANCELED') | デフォルト OPEN |
| created_at/updated_at | DATETIME | |

## 13.2 受注明細 `t_order_line`
| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| order_id | BIGINT FK | `t_order` |
| line_no | INT | 行番号（ユニーク/受注内） |
| product_id | BIGINT FK NULL | `m_product`（未マスタはNULLでproduct_code保持） |
| product_code | VARCHAR(50) | |
| quantity | DECIMAL(14,3) | 受注明細数量 |
| due_date | DATE | 納期 |
| plant_code/ship_to_code | VARCHAR | 納入先/工場区分など |
| remark | VARCHAR(200) NULL | |
| created_at/updated_at | DATETIME | |

## 13.3 取込ステージング
- `stg_order_raw`：取込ファイルを行単位で保持。`customer_code`, `order_type`, `source_file`, `source_row_no`, `record_token(V1等)`, `start_month`, `due_date`, `product_code`, `quantity`, `raw_payload JSON`, `parse_status(PENDING/PARSED/ERROR)`, `error_message`。
- `stg_order_daily`：日別に正規化した需要。`raw_id`(←`stg_order_raw`), `customer_id`, `order_type`, `version_no`, `product_code`, `due_date`, `quantity`, `plant_code`, `ship_to_code`, `source_system/file`。`t_order`へUPSERTする前段。
- `t_schedule_detail.order_id` は `t_order` とFK連携し、スケジュール結果を受注明細と結合可能にする。

---

# 14. 初期展開SQL（例）
```sql
-- DAY行の lead_time_days を、製品×ラインの例外 → ライン既定 の順で展開
UPDATE m_routing_step rs
JOIN m_routing r ON r.id=rs.routing_id
LEFT JOIN m_line_product_lt lpl ON lpl.line_id=rs.line_id AND lpl.product_id=r.product_id
LEFT JOIN m_line_default ld ON ld.line_id=rs.line_id
SET rs.lead_time_days = COALESCE(lpl.lt_days, ld.default_lt_days, rs.lead_time_days)
WHERE rs.time_unit='DAY';
```
