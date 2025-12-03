# master_tables_definition.md（整理版）

## 目的
本ドキュメントは、量産・階層BOM・日単位リードタイム・工程統合を前提とした  
**生産管理システムのマスタ定義（最小構成）** を示す。  
完成品（L0）から部品（L1〜L3）まで、すべての品番を一元管理する。

---

# 1. 製品マスタ `m_product`
製品・中間品・部品すべての基本情報。  
BOM・ルーティングの中核となる。

| カラム名 | 型 | 説明 |
|-----------|----|------|
| id | BIGINT PK | 内部ID |
| product_code | VARCHAR(30) UNIQUE | 品番コード（L0〜L3すべて） |
| product_name | VARCHAR(100) | 品名 |
| category | VARCHAR(20) | 区分：集合（ASSY）／単品／材料／購入品 |
| unit | VARCHAR(10) | 単位（個、kgなど） |
| daily_target_qty | INT | 標準日産数（能力指標） |
| standard_lt_days | INT | 標準LT（完成品基準） |
| self_lt_days | INT | 自身のLT（親基準） |
| is_final_product | TINYINT(1) | 最終製品フラグ（L0のみ1） |
| is_active | TINYINT(1) | 有効/無効 |
| created_at / updated_at | DATETIME | 監査用 |

### 📘 運用ポイント
- L0〜L3すべての品番を登録（中間品・子部品も同じテーブルに）  
- `category` で管理区分を識別  
- 最上位（完成品）には `is_final_product=1`

---

# 2. 得意先マスタ `m_customer`

| カラム名 | 型 | 説明 |
|-----------|----|------|
| id | BIGINT PK |  |
| customer_code | VARCHAR(20) UNIQUE | 得意先コード |
| customer_name | VARCHAR(100) | 名称 |
| short_name | VARCHAR(40) | 略称 |
| calendar_id | BIGINT FK | 使用カレンダ |
| is_active | TINYINT(1) | 有効/無効 |
| created_at / updated_at | DATETIME | 監査用 |

---

# 3. 工程マスタ `m_process`

| カラム名 | 型 | 説明 |
|-----------|----|------|
| id | BIGINT PK |  |
| process_code | VARCHAR(20) UNIQUE | 工程コード |
| process_name | VARCHAR(50) | 工程名 |
| is_outsource | TINYINT(1) | 外作工程か |
| is_active | TINYINT(1) | 有効/無効 |
| created_at / updated_at | DATETIME | 監査用 |

---

# 4. ラインマスタ `m_line`

| カラム名 | 型 | 説明 |
|-----------|----|------|
| id | BIGINT PK |  |
| line_code | VARCHAR(20) UNIQUE | ラインコード |
| line_name | VARCHAR(50) | 名称 |
| is_active | TINYINT(1) | 有効/無効 |
| created_at / updated_at | DATETIME | 監査用 |

---

# 5. ルーティング（工程順序）

## 5.1 ルーティングヘッダ `m_routing`
| カラム名 | 型 | 説明 |
|-----------|----|------|
| id | BIGINT PK |  |
| product_id | BIGINT FK | 対象製品（m_product.id） |
| routing_code | VARCHAR(30) | 識別コード（版数・代替ルート） |
| description | TEXT | 備考 |
| is_default | TINYINT(1) | 標準ルート |
| is_active | TINYINT(1) | 有効/無効 |
| created_at / updated_at | DATETIME | 監査用 |

## 5.2 ルーティング工程明細 `m_routing_step`
| カラム名 | 型 | 説明 |
|-----------|----|------|
| id | BIGINT PK |  |
| routing_id | BIGINT FK | ルートヘッダ |
| step_no | INT | 工程順序 |
| process_id | BIGINT FK | 工程ID |
| line_id | BIGINT FK | 標準ライン |
| lead_time_days | INT | 工程LT（日単位） |
| remark | VARCHAR(200) | 備考 |
| created_at / updated_at | DATETIME | 監査用 |

---

# 6. 構成マスタ（BOM）

## 6.1 BOMヘッダ `m_bom`
| カラム名 | 型 | 説明 |
|-----------|----|------|
| id | BIGINT PK |  |
| parent_product_id | BIGINT FK | 親品番（m_product.id） |
| version | VARCHAR(20) | 版数 |
| valid_from | DATE | 適用開始 |
| valid_to | DATE NULL | 適用終了（NULL＝現行） |
| is_active | TINYINT(1) | 有効/無効 |
| created_at / updated_at | DATETIME | 監査用 |

## 6.2 BOM明細 `m_bom_item`
| カラム名 | 型 | 説明 |
|-----------|----|------|
| id | BIGINT PK |  |
| bom_id | BIGINT FK | 対応BOMヘッダ |
| child_product_id | BIGINT FK | 子品番（m_product.id） |
| quantity | DECIMAL(12,3) | 使用数量 |
| loss_rate | DECIMAL(5,3) | 歩留まり |
| remark | VARCHAR(200) | 備考 |
| created_at / updated_at | DATETIME | 監査用 |

---

# 7. カレンダマスタ `m_calendar`

| カラム名 | 型 | 説明 |
|-----------|----|------|
| id | BIGINT PK |  |
| calendar_code | VARCHAR(20) | カレンダコード |
| calendar_name | VARCHAR(50) | 名称 |
| description | TEXT | 備考 |
| created_at / updated_at | DATETIME | 監査用 |

## 7.2 カレンダ日明細 `m_calendar_day`
| カラム名 | 型 | 説明 |
|-----------|----|------|
| id | BIGINT PK |  |
| calendar_id | BIGINT FK | 対応カレンダ |
| target_date | DATE | 対象日 |
| is_working_day | TINYINT(1) | 稼働/休日 |
| note | VARCHAR(100) | 備考 |
| created_at / updated_at | DATETIME | 監査用 |

---

# 8. ユーザ管理
Django 標準の `auth_user` を使用。  
将来的に `m_user` で拡張可（担当者・権限・所属ライン等）。

---

# 9. テーブル相関（概要）

| 主キー | 参照先 | 関係 |
|--------|--------|------|
| `m_product.id` | `m_bom.parent_product_id` / `m_bom_item.child_product_id` / `m_routing.product_id` | 製品↔構成・工程 |
| `m_process.id` | `m_routing_step.process_id` | 工程定義 |
| `m_line.id` | `m_routing_step.line_id` | ライン紐付け |
| `m_calendar.id` | `m_calendar_day.calendar_id`, `m_customer.calendar_id` | 稼働日関連 |

---

# 10. 運用ルールまとめ
| 項目 | 方針 |
|------|------|
| 製品登録 | L0〜L3すべて m_product に登録 |
| BOM構成 | 親子とも m_product.id を参照 |
| ルーティング | 完成品またはASSY単位に定義 |
| カレンダ | 工場／顧客単位で管理 |
| 有効期間 | BOMとルートに履歴管理対応 |
| 標準ルート | `is_default=1` で区別 |
| 最終製品 | `is_final_product=1` フラグ |
