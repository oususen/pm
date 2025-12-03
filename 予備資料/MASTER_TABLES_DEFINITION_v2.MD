# MASTER_TABLES_DEFINITION_v2.MD
（段階BOM＋セル工程・時間運用＋ライン既定LT／購買LT 対応）

## 目的
- 段階BOM（A案）を前提に、ラインは**日**、ライン配下の工程は**分**で運用する。
- 可変サイクル、移送バッチ、バッファ、逐次着手（移送バッチ到達で起動）を表現。
- さらに本版では、**ライン既定LT**・**製品×ラインLT**・**購買LT（仕入先×品目）** を追加。

---

# 1. 製品マスタ `m_product`
| カラム名 | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| product_code | VARCHAR(30) UNIQUE | 品番コード（L0〜L3すべて） |
| product_name | VARCHAR(100) | 品名 |
| category | VARCHAR(20) | 集合/単品/材料/購入品 |
| unit | VARCHAR(10) | 単位 |
| standard_lt_days | INT NULL | 完成品の標準LT（日）※粗い納期 |
| self_lt_days | INT NULL | 親内オフセット（日） |
| is_final_product | TINYINT(1) DEFAULT 0 | 最終製品 |
| is_phantom | TINYINT(1) DEFAULT 0 | 見なし組立（在庫しない） |
| is_active | TINYINT(1) DEFAULT 1 | |
| created_at / updated_at | DATETIME | |

> 能力は m_cycle_time（製品×工程×ライン）で管理。

---

# 2. 得意先 `m_customer`
（変更なし）

---

# 3. 工程 `m_process`
（変更なし）

---

# 4. ライン `m_line`
（変更なし）
# 2. 得意先マスタ `m_customer`
| カラム名 | 型 | 説明 |
|---|---|---|
| id | BIGINT PK |  |
| customer_code | VARCHAR(20) UNIQUE | 得意先コード |
| customer_name | VARCHAR(100) | 名称 |
| short_name | VARCHAR(40) | 略称 |
| calendar_id | BIGINT FK | 使用カレンダ |
| is_active | TINYINT(1) DEFAULT 1 |  |
| created_at / updated_at | DATETIME |  |

---

# 3. 工程マスタ `m_process`
| カラム名 | 型 | 説明 |
|---|---|---|
| id | BIGINT PK |  |
| process_code | VARCHAR(20) UNIQUE | 工程コード |
| process_name | VARCHAR(50) | 工程名（切断/曲げ/溶接 等） |
| is_outsource | TINYINT(1) DEFAULT 0 | 外作工程か |
| is_active | TINYINT(1) DEFAULT 1 |  |
| created_at / updated_at | DATETIME |  |

---

# 4. ラインマスタ `m_line`
| カラム名 | 型 | 説明 |
|---|---|---|
| id | BIGINT PK |  |
| line_code | VARCHAR(20) UNIQUE | ラインコード（レーザ/プレス/溶接 等） |
| line_name | VARCHAR(50) | 名称 |
| is_active | TINYINT(1) DEFAULT 1 |  |
| created_at / updated_at | DATETIME |  |

---
## 4.1 ライン既定LT（任意） `m_line_default`
ラインに共通の粗LT（日）を持たせる初期値テーブル。最終的に計画で使うのは **m_routing_step** に展開した値。

| カラム名 | 型 | 説明 |
|---|---|---|
| line_id | BIGINT PK/FK | 対象ライン |
| default_lt_days | INT NOT NULL | 既定のLT（日） |

## 4.2 製品×ラインLT（任意） `m_line_product_lt`
例外設定。特定製品を特定ラインで処理するときの粗LT。

| カラム名 | 型 | 説明 |
|---|---|---|
| line_id | BIGINT FK | ライン |
| product_id | BIGINT FK | 製品 |
| lt_days | INT NOT NULL | 粗LT（日） |
| PK | (line_id, product_id) | 複合主キー |

> **最終ソースは m_routing_step**。ここは初期計画のテンプレ・上書き用。

---

# 5. ルーティング `m_routing` / `m_routing_step`
## 5.1 `m_routing`
（変更なし：製品×版のルートヘッダ）

## 5.2 `m_routing_step`（工程は分で運用）
| カラム名 | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| routing_id | BIGINT FK | |
| step_no | INT | 工程順 |
| process_id | BIGINT FK | 工程 |
| line_id | BIGINT FK NULL | 標準ライン |
| start_offset_min | INT NULL | 開始オフセット（分） |
| duration_min | INT NULL | 所要（分）＝段取り＋サイクル×数量 |
| lead_time_days | INT DEFAULT 0 | 粗い計画（日）※互換 |
| remark | VARCHAR(200) NULL | |
| created_at / updated_at | DATETIME | |

> ラインの「日LT」は m_routing_step.lead_time_days に反映させて使う。

---

# 6. 工程出来高（WIPの完成物） `m_routing_step_output`
| カラム名 | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| routing_step_id | BIGINT FK | |
| output_product_id | BIGINT FK | 完成するWIP（m_product） |
| yield_rate | DECIMAL(5,3) NULL | 歩留 |
| is_final_stage | TINYINT(1) DEFAULT 0 | 最終完成 |
| remark | VARCHAR(200) NULL | |
| created_at / updated_at | DATETIME | |

---

# 7. サイクルタイム `m_cycle_time`
| カラム名 | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| product_id | BIGINT FK | 対象製品 |
| process_id | BIGINT FK | 工程 |
| line_id | BIGINT FK | ライン |
| cycle_time_sec | DECIMAL(10,2) | 秒/個 |
| setup_time_min | DECIMAL(10,2) | 段取り（分） |
| valid_from | DATE | |
| valid_to | DATE NULL | |
| is_active | TINYINT(1) DEFAULT 1 | |
| created_at / updated_at | DATETIME | |

> 所要分 = setup + (cycle × 数量)/60。

---

# 8. 工程パラメータ `m_routing_step_param`
| カラム名 | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| routing_step_id | BIGINT FK | |
| lot_size | INT NULL | ロットサイズ（未設定＝オーダ数） |
| transfer_batch_qty | INT NULL | 移送バッチ（例：4台） |
| start_trigger | ENUM('on_first_unit','on_transfer_batch','on_complete') | 次工程着手条件 |
| target_buffer_qty | INT NULL | 目標バッファ |
| max_buffer_qty | INT NULL | バッファ上限 |
| daily_time_window_min | INT NULL | 1日時間枠（例：240分） |
| created_at / updated_at | DATETIME | |

---

# 9. 構成（段階BOM） `m_bom` / `m_bom_item`
## 9.1 `m_bom`（ヘッダ）
| カラム名 | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| parent_product_id | BIGINT FK | 親品番 |
| version | VARCHAR(20) | 版 |
| valid_from | DATE | |
| valid_to | DATE NULL | |
| is_active | TINYINT(1) DEFAULT 1 | |
| created_at / updated_at | DATETIME | |

## 9.2 `m_bom_item`（明細）
| カラム名 | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| bom_id | BIGINT FK | |
| child_product_id | BIGINT FK | 子品番 |
| quantity | DECIMAL(12,3) | 使用数量 |
| loss_rate | DECIMAL(5,3) NULL | 歩留 |
| sourcing_type | ENUM('MAKE','BUY','SUBCON') DEFAULT 'MAKE' | 調達区分 |
| supplier_id | BIGINT NULL FK | 仕入先（BUY/SUBCON時） |
| remark | VARCHAR(200) NULL | |
| created_at / updated_at | DATETIME | |

> 段階BOM：各段で追加部品を記載。前段WIPは「1個使用」。

---

# 10. 仕入先・購買LT
## 10.1 仕入先 `m_supplier`
| カラム名 | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| supplier_code | VARCHAR(20) UNIQUE | |
| supplier_name | VARCHAR(100) | |

## 10.2 仕入先×品目 `m_supplier_item`
購買LT（外注含む）の保持先。**投入予定日 − purchase_lt_days = 発注日**。

| カラム名 | 型 | 説明 |
|---|---|---|
| supplier_id | BIGINT FK | 仕入先 |
| product_id | BIGINT FK | 品目 |
| purchase_lt_days | INT NOT NULL | 購買LT（日） |
| min_lot | INT NULL | 最小ロット |
| order_cycle_days | INT NULL | 発注サイクル |
| PK | (supplier_id, product_id) | 複合主キー |

---

# 11. カレンダ `m_calendar` / `m_calendar_day`
`work_minutes` を持ち、分⇄日換算や日跨ぎを扱う。

---

# 12. テーブル相関（要点）
- ルーティング：`m_routing` → `m_routing_step` → `m_routing_step_output` / `m_routing_step_param`
- 能力：`m_cycle_time(product, process, line)`
- ライン粗LT：`m_line_default`（既定）→ `m_line_product_lt`（例外）→ **`m_routing_step.lead_time_days`（最終）**
- 段階BOM：`m_bom` / `m_bom_item(sourcing_type, supplier_id)`
- 購買LT：`m_supplier_item.purchase_lt_days`
- カレンダ：`m_calendar_day.work_minutes`

---

# 13. ルールのまとめ（質問への回答）
**Q1. ラインのLTはどの製品番号にくっつける？**  
→ **製品ではなく `m_routing_step` に置く。** 既定は `m_line_default`、例外は `m_line_product_lt` で初期化し、最終的にステップへ展開。

**Q2. ライン頭工程への投入品のLTは？**  
- **Make品**：その子品目の**自ルーティング**から自動逆算（`duration_min/lead_time_days`）  
- **Buy/外注**：`m_supplier_item.purchase_lt_days` を使って逆算（投入日−LT=発注日）

---

# 14. 実装メモ
- 受注→ロット分割→所要分計算（m_cycle_time）→時間枠割付（m_routing_step_param.daily_time_window_min, m_calendar_day.work_minutes）→移送バッチ到達で次工程起動。  
- 粗い納期は `standard_lt_days` と各ステップ `lead_time_days`。  
- WIP在庫を持たない段は `is_phantom=1`。

