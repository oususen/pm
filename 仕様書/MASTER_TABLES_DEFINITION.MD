# MASTER_TABLES_DEFINITION_v3.MD
（段階BOM＋セル工程・時間運用＋ライン既定LT／購買LT 対応／time_unit 追加／m_customer 追加／整合性強化／量産セル流し向けのフロー・並列対応）

## 変更サマリ（v2→v3）
- `m_routing_step` に **`time_unit ENUM('DAY','MINUTE')`** を追加（混在単位の明確化）。
- `m_customer` テーブルを **スキーマ＆ERに正式追加**。
- `m_bom_item` に **調達区分と仕入先の整合チェック**（CHECK制約）を追加。
- `m_line_default` のPKは **line_id 単独** に統一（ER図表現を修正）。
- **受注テーブル (`t_order`, `t_order_line`) と取込ステージング (`stg_order_raw`, `stg_order_daily`) を追加**、`t_schedule_detail.order_id` と連携。
- サンプル: ルーティング `step_no` を **連番** に修正、`time_unit` を明示。
- サイクルタイム参照の基準を**m_routing_step.output_product_id**に統一（連産品はBOMの`is_coproduct`で表現するため`m_routing_step_output`は廃止）。
- 量産セル流し向けに **工程タイプ（FLOW / PARALLEL_POOL）** と **バッファ時間** を追加、サイクルに **yield_rate** を保持。
- `m_product`/`m_process`/`m_line` に管理系カラム（`product_name_halfwidth`, `is_virtual_set`, `is_line_final_product`, `image_url`, `line_id`, `process_id`, `management_unit`, `calendar_id`）を追加。
- `m_bom` に `is_coproduct`、`m_bom_item` に工程/ライン/時間情報を追加。
- `m_routing_step` に階層パス/深さ/並列数を追加。
- 勤務パターン/休憩（`m_work_pattern`, `m_break_time`）と `m_calendar_day.work_pattern_id` を追加。
- 工程別部品/工程別サイクル時間（`m_routing_step_material`, `m_process_cycle_time`）を追加。
- 需要/ガント/リアルタイム系（`t_line_demand`, `t_line_gantt_plan`, `t_line_realtime_record`, `t_line_status`, `t_process_realtime_record`）と製造実行系（`t_stock_allocation`, `t_production_order`, `t_process_actual`, `t_scrap_record_detail`）を追加。
- `t_order.status` に `SUPERSEDED` を追加。
- `stg_order_raw` / `stg_order_daily` に `product_name`, `product_name_halfwidth` を追加。

---

# 0. 全テーブル索引（現行コード基準）

この章は **`pm_backend/apps/**/models*.py` の `db_table` 定義**を基準にした全テーブル索引。  
「どこに説明があるか」を追えるように、テーブル名をアプリ別に列挙する。

## 0.1 masters
- `m_product`
- `m_customer`
- `m_process`
- `m_line`
- `m_supplier`
- `m_calendar`
- `m_work_pattern`
- `m_break_time`
- `m_calendar_day`
- `m_bom`
- `m_bom_item`
- `m_routing`
- `m_routing_step`
- `m_routing_step_material`
- `m_process_cycle_time`
- `m_product_group`
- `m_container_capacity`
- `m_equipment`
- `m_kubota_sakai_truck`
- `m_contacts`

## 0.2 orders
- `t_order`
- `t_order_line`
- `t_kubota_sakai_due_adjustment`
- `t_kubota_sakai_trip_assignment`
- `t_shipping_run`
- `t_shipping_trip`
- `t_shipping_trip_allocation`
- `stg_order_raw`
- `stg_order_raw_tiera`
- `stg_order_raw_rieden`
- `stg_order_raw_kubota`
- `stg_order_daily`
- `kubota_sakai_import_config`

## 0.3 production
- `t_line_demand`
- `line_backlog`
- `line_plan`
- `t_line_gantt_plan`
- `t_line_realtime_record`
- `t_line_status`
- `t_process_realtime_record`
- `t_stock_allocation`
- `t_production_order`
- `t_process_actual`
- `line_daily_schedule_setting`
- `t_line_default_schedule_setting`
- `production_plan_lock_setting`
- `production_plan_change_log`
- `production_schedule_config`
- `production_line_backlog_adjustment`
- `production_record_inquiry_setting`
- `production_routing_migration_log`
- `t_laser_pattern`
- `t_laser_pattern_component`
- `t_laser_pattern_finished`
- `t_laser_actual`
- `t_laser_actual_detail`
- `t_laser_shift_record`
- `brake_line_record`
- `t_gantt_display_product_map`
- `t_process_work_session`
- `t_process_work_session_equipment`
- `t_production_record_confirmation`
- `production_purchase_actual_reconcile_report`
- `production_purchase_actual_reconcile_report_detail`
- `production_production_actual_reconcile_report`
- `production_production_actual_reconcile_report_detail`

## 0.4 quality
- `t_scrap_record`
- `t_scrap_record_detail`
- `quality_equipment_inspection_template`
- `quality_equipment_inspection_item`
- `quality_equipment_inspection_item_attachment`
- `quality_equipment_inspection_record`
- `quality_equipment_inspection_result`
- `quality_equipment_inspection_confirmation`
- `quality_equipment_inspection_task`
- `quality_equipment_inspection_workflow_log`

## 0.5 shipping
- `t_shipment_actual`
- `t_shipment_actual_history`
- `t_delivery_progress`

## 0.6 purchase
- `purchase_plan_lock_setting`
- `supplier_order_schedule`
- `purchase_order_proposal`
- `purchase_order_proposal_line`
- `purchase_order_proposal_approval`
- `purchase_order_approval_config`
- `purchase_order_task`
- `purchase_plan_change_log`
- `engineering_change_case`
- `engineering_change_part`

## 0.7 accounts
- `accounts_department`
- `accounts_userprofile`
- `accounts_unit_line_mapping`
- `accounts_user_smtp_configs`
- `accounts_userpermission`
- `accounts_departmentpermission`
- `accounts_positionpermission`
- `accounts_department_position_permission`

## 0.8 notifications
- `notifications`
- `notification_reads`

## 0.9 overtime
- `t_overtime_application`
- `t_overtime_approval_log`

## 0.10 proposals
- `proposals_department`
- `proposals_employee`
- `proposals_employeepermission`

## 0.11 system_settings
- `system_settings`

## 0.12 参照ルール
- **主要テーブルのカラム説明**: この文書の各章（1〜18）を参照。
- **関係性（FK/多重度）**: [ER_diagram_v3.md](./ER_diagram_v3.md) を参照。
- **業務ロジックまで含む詳細**: 各業務仕様書（例: `受注管理仕様書.md`, `生産計画仕様書.md`, `在庫計算仕様書.md`）を参照。

## 0.13 テーブル別 主参照仕様書

下表は「どのテーブルをどの仕様書で読むべきか」の主参照先。  
テーブル個別説明が薄い場合は、まず同じ行の仕様書を参照し、次に本書各章とER図で補完する。

| テーブル群 | 主参照仕様書 | 補足 |
|---|---|---|
| `m_product`, `m_process`, `m_line`, `m_bom`, `m_bom_item`, `m_routing`, `m_routing_step`, `m_process_cycle_time` | `生産計画仕様書.md`, `リードタイム仕様書.md`, `受注展開仕様書.md` | 製品/工程/LT/展開の中核 |
| `m_calendar`, `m_calendar_day`, `m_work_pattern`, `m_break_time` | `受注管理仕様書.md`, `納入先コード処理実装まとめ.md` | 営業日・勤務パターン |
| `m_customer` | `受注管理仕様書.md`, `出荷指示書機能仕様書.md` | 得意先・カレンダ連携 |
| `m_supplier` | `購買需要計算仕様書.md` | 購買LT・調達関連 |
| `m_product_group`, `m_container_capacity` | `出荷指示書機能仕様書.md` | 出荷帳票用マスタ |
| `m_equipment` | `スポットライン実績入力仕様書.md`, `設備点検表仕様書.md` | 設備実績・点検 |
| `m_kubota_sakai_truck` | `クボタ堺納期調整及び便計画仕様書.md` | 便マスタ |
| `accounts_*` | `権限仕様書.md` | 部署階層/ロール/権限 |
| `t_order`, `t_order_line`, `stg_order_*`, `stg_order_daily` | `受注管理仕様書.md`, `受注展開仕様書.md` | 受注取込〜明細 |
| `t_line_demand`, `line_backlog`, `line_plan`, `t_line_gantt_plan` | `生産計画仕様書.md`, `在庫計算仕様書.md`, `前工程需要計算仕様書.md` | 計画/需要/在庫系トランザクション |
| `t_line_realtime_record`, `t_line_status`, `t_process_realtime_record`, `t_process_work_session*`, `t_production_record_confirmation`, `brake_line_record` | `生産計画仕様書.md`, `スポットライン実績入力仕様書.md`, `レーザー実績入力仕様書.md` | 実績入力・稼働監視 |
| `t_stock_allocation`, `t_production_order`, `t_process_actual` | `生産計画仕様書.md`, `在庫計算仕様書.md` | 製造実行 |
| `production_schedule_config`, `production_plan_lock_setting`, `production_plan_change_log`, `production_record_inquiry_setting` | `自動計画生成タスク仕様書.md`, `システム設定仕様書.md`, `生産計画仕様書.md` | 設定/履歴 |
| `production_line_backlog_adjustment` | `在庫進度調整画面仕様書.md` | 調整入力 |
| `t_laser_pattern*`, `t_laser_actual*`, `t_laser_shift_record` | `レーザー実績入力仕様書.md`, `レーザ月所要材料集計仕様書.md` | レーザー系 |
| `production_*_reconcile_report*` | `生産実績整合チェック仕様書.md`, `納入実績整合チェック仕様書.md` | 整合チェック |
| `t_scrap_record`, `t_scrap_record_detail` | `仕損登録仕様書.md` | 仕損/戻し |
| `quality_equipment_inspection_*` | `設備点検表仕様書.md` | 設備点検ワークフロー |
| `t_shipment_actual`, `t_shipment_actual_history`, `t_delivery_progress` | `出荷進度照会仕様書.md`, `出荷指示書機能仕様書.md` | 出荷実績/進捗 |
| `t_kubota_sakai_due_adjustment`, `t_kubota_sakai_trip_assignment`, `t_shipping_run`, `t_shipping_trip`, `t_shipping_trip_allocation`, `kubota_sakai_import_config` | `クボタ堺納期調整及び便計画仕様書.md` | 堺専用＋共通出荷連携 |
| `purchase_*`, `engineering_change_*` | `購買需要計算仕様書.md`, `自動発注提案仕様書.md`, `設変新規管理仕様書.md` | 購買/設変 |
| `notifications`, `notification_reads` | `通知閲覧.md`, `通知編集.md` | 通知 |
| `t_overtime_application`, `t_overtime_approval_log` | `残業申請仕様書.md` | 残業申請 |
| `proposals_*` | `自動発注提案仕様書.md` | 提案系基盤 |
| `system_settings` | `システム設定仕様書.md` | 全体設定 |

# 1. 製品 `m_product`
| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| product_code | VARCHAR(30) UNIQUE | 品番コード |
| product_name | VARCHAR(100) | 品名 |
| product_name_halfwidth | VARCHAR(100) NULL | 品名半角 |
| category | VARCHAR(20) NULL | 集合/単品/材料/購入品（実運用はENUM想定） |
| unit | VARCHAR(10) | 単位 |
| standard_lt_days | INT NULL | 完成品標準LT（日） |
| image_url | VARCHAR(255) NULL | 画像URL |
| line_id | BIGINT FK NULL | ライン情報 |
| process_id | BIGINT FK NULL | 工程情報 |
| management_unit | VARCHAR(10) NULL | 管理区分（DAY/MINUTE） |
| self_lt_days | INT NULL | 親内オフセット（日） |
| is_final_product | TINYINT(1)| 最終製品 |
| is_line_final_product | TINYINT(1)| ライン最終品 |
| is_phantom | TINYINT(1)| 見なし組立 |
| is_virtual_set | TINYINT(1)| 仮想セット品番 |
| is_active | TINYINT(1)| |
| created_at/updated_at | DATETIME | |

- `category` は製品の状態区分（完成/中間/WIP/材料/購買など）として運用する。
- 受注に載る製品コードは社内最終工程の出力品（ルート末尾の `m_routing_step.output_product_id`）と一致させる前提。

## 主要フィールド詳細

**`standard_lt_days`（標準LT）**

- 完成品標準リードタイム（日数）
- この製品を完成させるのに必要な標準的なリードタイム日数
- 受注から納品までの標準的な所要日数の目安として使用
- **運用上の推奨**: 最終製品（`is_final_product=TRUE`）には設定するが、中間品や部品には通常設定しない

**`self_lt_days`（自工程LT）**

- 親製品内での工程オフセット（日数）
- BOM展開時に、親製品から見たこの子製品の製造にかかる日数
- 親製品の納期から逆算する際に、この日数だけ早く着手する必要があることを示す

**`is_phantom`（見なし組立）**

- ファントム部品フラグ
- TRUE時、「在庫を持たない中間組立品」として扱われる
- BOM展開時に自動的に分解され、構成部品に展開される
- 在庫管理の対象外（仮想的な組立品）
- **該当する例**: 工程内の仮組み品、梱包前のサブアセンブリ、一時的な集合品
- **該当しない例**: ラインで完成する集合品（通常の製品として在庫管理する）

**`is_final_product`（最終製品）**

- 最終製品フラグ
- TRUE時、「顧客に出荷する最終製品」として扱われる
- 受注データに載る製品コードは、通常この最終製品フラグがONのものが対象

**`is_line_final_product`（ライン最終品）**

- ライン内で最後に出力される製品フラグ（次ラインへ渡す中間品を含む）
- ライン別の最終出力品を明示したい場合に使用

**`is_virtual_set`（仮想セット品番）**

- 連産品を表す仮想的なセット品番
- BOMの親に使用し、この品番自体は在庫を持たない

---

# 2. 得意先 `m_customer`（新規・正式追加）
| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| customer_code | VARCHAR(20) UNIQUE | |
| customer_name | VARCHAR(100) | |
| short_name | VARCHAR(40) NULL | |
| calendar_id | BIGINT FK NULL | 稼働カレンダ |
| is_active | TINYINT(1)| |
| created_at/updated_at | DATETIME | |

---

# 3. 工程 `m_process`
| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| process_code | VARCHAR(20) UNIQUE | 工程コード |
| process_name | VARCHAR(50) | 工程名 |
| line_id | BIGINT FK NULL | 所属ライン（ライン直下で管理する場合に使用） |
| is_outsource | TINYINT(1)| 外注フラグ |
| management_unit | VARCHAR(10)| 管理単位（DAY/MINUTE） |
| is_active | TINYINT(1)| |
| created_at/updated_at | DATETIME | |

# 4. ライン `m_line`
| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| line_code | VARCHAR(20) UNIQUE | ラインコード |
| line_name | VARCHAR(50) | ライン名 |
| calendar_id | BIGINT FK NULL | 勤務カレンダ |
| lead_time_days | INT NULL | リードタイム（日） |
| is_active | TINYINT(1)| |
| created_at/updated_at | DATETIME | |

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
| output_product_id | BIGINT FK NULL | 工程の出力品目（連産品はBOMで表現） |
| hierarchy_path | VARCHAR(100)| 工程階層パス |
| hierarchy_depth | INT| 工程階層深さ |
| step_type | ENUM('FLOW','PARALLEL_POOL')| 流し/並列プール |
| **time_unit** | **ENUM('DAY','MINUTE')** | 単位の明示 |
| lead_time_days | INT NOT NULL| 日単位（`time_unit='DAY'`で使用） |
| start_offset_min | INT NULL | 分オフセット |
| duration_min | INT NULL | 分所要（段取り+サイクル×数量） |
| parallel_count | INT| 並列数 |
| parallel_group | INT| 同一step_no内の順序グループ（重複許可用） |
| remark | VARCHAR(200) NULL | |
| created_at/updated_at | DATETIME | |

**ユニークキー**: `(routing_id, step_no, parallel_group)`

---

# 6. 工程出力（`m_routing_step.output_product`）
- ステップ完了で出来上がる **WIP/製品** は `m_routing_step.output_product_id` で管理する。
- 連産品（複数出力）はBOMの`is_coproduct`で親(仮想セット)と子(実品)を表現するため、`m_routing_step_output`は廃止。
- サイクルタイム参照の基準は **この `output_product_id`** を用いる。

---

# 7. サイクルタイム `m_cycle_time`
- 製品×工程×ラインの秒/個 と 段取り（分）、歩留まり（yield_rate）
- 所要時間計算: `setup_time_min + cycle_time_sec * qty / 60` をベースに、`yield_rate` で実行数量を補正

---

## 7.1 工程別サイクル時間 `m_process_cycle_time`
- 製品×工程×ラインの **分/個** と **段取り（分）**、標準ロットサイズを管理
- ライン指定が無い場合は `line_id` を NULL で登録
- 有効期間: `valid_from` / `valid_to`、`is_active`

---

# 8. 工程パラメータ `m_routing_step_param`
- ロット、移送バッチ、着手条件、バッファ数量（target/max）、バッファ時間（前後）、日内時間枠（分）
- `step_type='FLOW'` ではバッファをWIPの緩衝に使い、`'PARALLEL_POOL'` ではプールキャパと組み合わせて所要日数を算出

---

## 8.1 工程別部品消費 `m_routing_step_material`
- 1工程で消費する部品・数量・消費タイミングを保持
- 主な列: `routing_step_id`, `component_id`, `quantity`, `consume_timing(START/END)`, `remark`

---

# 9. 構成 `m_bom` / `m_bom_item`
- 段階BOM
- `m_bom.is_coproduct` は連産品BOMフラグ（親は仮想セット品番）
- `m_bom_item` に `process_id`, `line_id`, `time_unit`, `lead_time_days`, `duration_min` を保持（BOM→ルーティング自動生成に使用）
- `m_bom_item.is_coproduct_driver` は連産品代表品フラグ。連産品BOMの子製品のうち1つに指定し、計画展開のトリガーとする。代表品の`duration_min`が連産品のサイクルタイムとして使用される。
- `m_bom_item.sourcing_type`（MAKE/BUY/SUBCON）と `supplier_id` 整合の **CHECK制約** を追加。

---

# 10. 仕入先 `m_supplier` / `m_supplier_item`
- 仕入先×品目に `purchase_lt_days` を保持（投入日−LT＝手配日）。
- 製品向け購買品を得意先から調達するケースでは、仕入先コードにその得意先コードを流用してよい。
- 得意先を直接仕入先として使えない場合は、その製品専用の擬似仕入先コードを作成して運用してもよい。

---

# 11. カレンダ `m_calendar` / `m_calendar_day`
- `work_minutes` を持ち、日跨ぎ計算を支援。
- `m_calendar_day.work_pattern_id` で勤務パターンを指定可能。
- 勤務パターン: `m_work_pattern`（開始/終了時刻、説明）
- 休憩: `m_break_time`（勤務パターンに対する休憩枠）

---

## 11.1 勤務パターン `m_work_pattern`
| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| pattern_code | VARCHAR(20) UNIQUE | パターンコード |
| pattern_name | VARCHAR(50) | パターン名 |
| start_time | TIME | 開始時刻 |
| end_time | TIME NULL | 終了時刻 |
| description | TEXT NULL | 説明 |
| created_at/updated_at | DATETIME | |

## 11.2 休憩 `m_break_time`
| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| work_pattern_id | BIGINT FK | 勤務パターン |
| break_start | TIME | 休憩開始時刻 |
| break_end | TIME | 休憩終了時刻 |
| order | INT| 順序 |
| created_at/updated_at | DATETIME | |

---

# 12. 主要制約・整合ルール
- **時間単位**：`time_unit='DAY'` → `lead_time_days` 必須、`'MINUTE'` → `duration_min` 必須。
- **工程タイプ**：`step_type='FLOW'` は逐次流し、`'PARALLEL_POOL'` は同一加工を並列に裁くプール。キャパはサイクルタイム×稼働分/日で算出。
- **調達整合**：`sourcing_type='BUY'` ⇒ `supplier_id NOT NULL`。`MAKE/SUBCON` ⇒ `supplier_id IS NULL` を推奨。
- **サイクル参照**：`m_routing_step.output_product_id` を `m_cycle_time.product_id` と紐付けて所要を算出。

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
| status | ENUM('OPEN','CLOSED','CANCELED','SUPERSEDED') | デフォルト OPEN |
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
- `stg_order_raw`：取込ファイルを行単位で保持。`customer_code`, `order_type`, `source_file`, `source_row_no`, `record_token(V1等)`, `start_month`, `due_date`, `product_code`, `product_name`, `product_name_halfwidth`, `quantity`, `raw_payload JSON`, `parse_status(PENDING/PARSED/ERROR)`, `error_message`。
- `stg_order_daily`：日別に正規化した需要。`raw_id`(←`stg_order_raw`), `customer_id`, `order_type`, `version_no`, `product_code`, `product_name`, `product_name_halfwidth`, `due_date`, `quantity`, `plant_code`, `ship_to_code`, `source_system/file`。`t_order`へUPSERTする前段。
- `t_schedule_detail.order_id` は `t_order` とFK連携し、スケジュール結果を受注明細と結合可能にする。
- 受注明細に載る `product_code` は、最終工程の出力品番（ルート末尾の output_product）をそのまま使用する想定。

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

---

# 15. 仕損記録 `t_scrap_record`（当面の暫定テーブル）
| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| line_id | BIGINT FK NULL | 所属ライン（工程から引き継ぎ） |
| process_id | BIGINT FK | 工程 |
| product_id | BIGINT FK NULL | 製品 |
| product_code | VARCHAR(50) | 品番（必須。マスタ未登録時はコードのみ保持） |
| product_name | VARCHAR(100) NULL | 品名 |
| qty | DECIMAL(14,3) | 仕損数量 |
| recorded_at | DATETIME | 記録時刻（auto_now_add） |
| plan_date | DATE NULL | 計画日（任意） |
| disposition_status | VARCHAR(20) | 判定ステータス（PENDING/APPROVED/REJECTED/PARTIAL） |
| return_qty | DECIMAL(14,3) | 戻し数量 |
| decided_at | DATETIME NULL | 判定日時 |
| decided_by | VARCHAR(50) NULL | 判定者 |
| reason | VARCHAR(100) NULL | 理由/区分（サビ, 変形/キズ, ビードずれ, ブローホール, 溶接穴あき, アンダーカット, 精度不良, 欠品/誤組, 素材/仕掛不良, その他） |
| reason_detail | VARCHAR(200) NULL | 理由詳細（「その他」選択時に必須） |
| batch_no | VARCHAR(100) NULL | ロット番号 |
| operator_name | VARCHAR(50) | 記入者（UIで必須。ログインユーザー名を初期セット） |
| remarks | TEXT NULL | 備考 |
| process_record_id | BIGINT NULL | 工程実時間記録（1:1） |
| is_replenished | TINYINT(1)| 補充完了 |
| replenished_at | DATETIME NULL | 補充完了日時 |
| replenished_by | VARCHAR(50) NULL | 補充完了者 |

- 取得元: 工程リアルタイム記録 API の `record_type='SCRAP'` 送信時に同時書き込み。`event_data.reason/reason_detail` を反映。
- 暫定運用: 将来的にライン/工程 backlog 集計へ統合予定。現行はシンプル記録用途で先行稼働。
- インデックス: `(process_id, recorded_at)`, `(line_id, recorded_at)`, `product_code`。

---

## 15.1. 仕損明細 `t_scrap_record_detail`
| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| scrap_record_id | BIGINT FK | 仕損記録 |
| product_id | BIGINT FK NULL | 製品 |
| product_code | VARCHAR(50) NULL | 品番 |
| product_name | VARCHAR(100) NULL | 品名 |
| process_id | BIGINT NULL | 工程ID |
| line_id | BIGINT NULL | ラインID |
| supplier_id | BIGINT NULL | 仕入先ID |
| sourcing_type | VARCHAR(20) NULL | 調達区分 |
| deduct_qty | DECIMAL(14,3)| 減算数量 |
| is_replenished | TINYINT(1)| 補充完了 |
| replenished_at | DATETIME NULL | 補充完了日時 |
| replenished_by | VARCHAR(50) NULL | 補充完了者 |

---

# 16. ライン工程別バックログ `line_backlog`（トランザクションテーブル）

| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| line_id | BIGINT FK | ライン（m_line） |
| process_id | BIGINT FK | 工程（m_process） |
| product_id | BIGINT FK | 製品（m_product） |
| plan_date | DATE | 計画日 |
| source_line_id | BIGINT FK NULL | 元ライン（後工程の場合、前工程のラインID） |
| source_routing_step_id | BIGINT FK NULL | 元ルーティングステップ |
| plan_id | VARCHAR(255) NULL | 計画ID（将来的な計画バージョン管理用） |
| sequence_no | INT NULL | 順序番号（同一日内の優先順位） |
| demand_qty_plan | INT| 需要計画数量 |
| order_qty | INT| 必要数量（最終ラインは受注、中間ラインは後工程からの引当） |
| plan_qty | INT| 計画数量（生産予定） |
| actual_qty | INT| 生産実績数量（このラインでの生産実績） |
| actual_shipment_qty | INT| 出荷実績数量（後工程への引き渡し実績） |
| adjust_qty | INT| 調整数量 |
| scrap_qty | INT| 仕損数量 |
| stock_qty | INT| 実在庫数量 |
| planned_stock_qty | INT| 計画在庫数量 |
| updated_at | DATETIME | 更新日時 |

**ユニークキー**: `(line_id, process_id, product_id, plan_date)`

## 用途

- ライン×工程×製品×日別の計画・実績・在庫を一元管理
- 生産進度照会、在庫照会の基礎データとして使用
- 工程リアルタイム記録（PRODUCTION）から `actual_qty` へ自動反映
- 出荷実績記録から `actual_shipment_qty` へ反映
- 後工程の「確定」値 = 前工程の `actual_shipment_qty`（引き渡し実績）
- 当工程の「実績」値 = 当工程の `actual_qty`（生産実績）

## 更新タイミング

- 計画生成時：`plan_qty`, `planned_stock_qty` 等を更新
- 生産実績登録時：`actual_qty` を加算（工程リアルタイム記録 API経由）
- 出荷実績登録時：`actual_shipment_qty` を更新
- 仕損記録時：`scrap_qty` を加算
- 在庫調整時：`adjust_qty`, `stock_qty` を更新

## インデックス

- `(line_id, process_id, product_id, plan_date)` - ユニークキー兼検索用
- `(plan_date)` - 日付範囲検索用
- `(product_id, plan_date)` - 製品別検索用

---

# 17. ライン需要/ガント/リアルタイム

## 17.1 ライン需要 `t_line_demand`
| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| line_id | BIGINT FK | ライン |
| routing_step_id | BIGINT FK NULL | ルーティング工程 |
| product_id | BIGINT FK NULL | 製品 |
| product_code | VARCHAR(50) | 製品コード |
| plan_date | DATE | 必要日 |
| lead_time_days | INT| リードタイム（日） |
| forecast_qty | DECIMAL(14,3)| 内示数量 |
| firm_qty | DECIMAL(14,3)| 確定数量 |
| plan_qty | DECIMAL(14,3)| 計画数 |
| actual_qty | DECIMAL(14,3)| 実績数 |
| plan_progress | DECIMAL(9,3)| 計画進度 |
| actual_progress | DECIMAL(9,3)| 実績進度 |
| order_numbers | VARCHAR(500)| 展開元受注番号 |
| created_at/updated_at | DATETIME | |

## 17.2 ラインガント計画 `t_line_gantt_plan`
| カラム | 型 | 説明 |
|---|---|---|
| plan_id | VARCHAR(160) PK | 計画ID |
| line_id | BIGINT FK | ライン |
| product_id | BIGINT FK | 製品 |
| plan_date | DATE | 計画日 |
| plan_qty | DECIMAL(14,3)| 計画数量 |
| sequence_no | INT NULL | 順序番号 |
| start_datetime | DATETIME | 開始 |
| end_datetime | DATETIME | 終了 |
| processes_plan | JSON NULL | 工程計画 |
| created_at/updated_at | DATETIME | |

## 17.3 ライン実時間記録 `t_line_realtime_record`
| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| line_id | BIGINT FK | ライン |
| product_id | BIGINT FK NULL | 製品 |
| product_code | VARCHAR(50) NULL | 製品コード |
| product_name | VARCHAR(100) NULL | 品名 |
| timestamp | DATETIME | 記録時刻 |
| record_type | VARCHAR(20) | 記録タイプ |
| qty | DECIMAL(10,3)| 数量 |
| equipment_state | VARCHAR(20) NULL | 設備状態 |
| event_data | JSON NULL | 付帯情報 |
| batch_no | VARCHAR(100) NULL | ロット番号 |
| operator_name | VARCHAR(50) NULL | 作業者名 |
| remarks | TEXT NULL | 備考 |

## 17.4 ライン状態 `t_line_status`
| カラム | 型 | 説明 |
|---|---|---|
| line_id | BIGINT PK | ライン |
| current_state | VARCHAR(20)| 現在状態 |
| today_output | DECIMAL(10,3)| 本日生産数 |
| today_plan | DECIMAL(10,3)| 本日計画数 |
| current_product_code | VARCHAR(50) NULL | 現在生産品番 |
| current_product_name | VARCHAR(100) NULL | 現在生産品名 |
| last_update | DATETIME | 最終更新時刻 |

## 17.5 工程実時間記録 `t_process_realtime_record`
| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| process_id | BIGINT FK | 工程 |
| product_id | BIGINT FK NULL | 製品 |
| product_code | VARCHAR(50) NULL | 製品コード |
| product_name | VARCHAR(100) NULL | 品名 |
| timestamp | DATETIME | 記録時刻 |
| record_type | VARCHAR(20) | 記録タイプ |
| qty | DECIMAL(10,3)| 数量 |
| equipment_state | VARCHAR(20) NULL | 設備状態 |
| event_data | JSON NULL | 付帯情報 |
| batch_no | VARCHAR(100) NULL | ロット番号 |
| operator_name | VARCHAR(50) NULL | 作業者名 |
| remarks | TEXT NULL | 備考 |

---

# 18. 製造実行/在庫/実績

## 18.1 在庫引当 `t_stock_allocation`
| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| product_id | BIGINT FK | 製品 |
| location | VARCHAR(50) | 保管場所 |
| current_stock | DECIMAL(14,3) | 現在庫数 |
| reserved_qty | DECIMAL(14,3)| 引当済数量 |
| min_stock_qty | INT UNSIGNED | 最小在庫数 |
| is_bottleneck | TINYINT(1)| ボトルネック品 |
| created_at/updated_at | DATETIME | |

## 18.2 製造指示 `t_production_order`
| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| order_no | VARCHAR(50) UNIQUE | 製造指示番号 |
| product_id | BIGINT FK | 製品 |
| routing_id | BIGINT FK NULL | ルーティング |
| line_id | BIGINT FK NULL | ライン |
| order_qty | DECIMAL(14,3) | 指示数量 |
| scheduled_start_date | DATE | 予定開始日 |
| scheduled_end_date | DATE | 予定完了日 |
| actual_start_date | DATE NULL | 実績開始日 |
| actual_end_date | DATE NULL | 実績完了日 |
| status | VARCHAR(20)| ステータス |
| allocation_id | BIGINT FK NULL | 在庫引当 |
| priority | INT| 優先度 |
| remark | TEXT NULL | 備考 |
| created_at/updated_at | DATETIME | |

## 18.3 工程別実績 `t_process_actual`
| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| production_order_id | BIGINT FK | 製造指示 |
| routing_step_id | BIGINT FK | ルーティング工程 |
| process_id | BIGINT FK | 工程 |
| line_id | BIGINT FK | ライン |
| completed_qty | DECIMAL(14,3) | 完了数量 |
| actual_duration_min | INT | 実績工数（分） |
| completed_at | DATETIME | 完了日時 |
| operator | VARCHAR(50) NULL | 作業者 |
| remark | TEXT NULL | 備考 |
| created_at/updated_at | DATETIME | |
