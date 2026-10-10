# AIマスタビュー確認明細（BOSS確認用）

作成日：2026-10-10 ／ 状態：**BOSSの判断待ち**（コード・DBの変更なし）

[AI用ビュー作成計画](AI用ビュー作成計画.md) §4.1 の原則に従い、元テーブルの**全フィールド**を一覧にした。公開するかどうかはBOSSが決める。ビューに含めるのは、BOSSが「公開」とした列だけとする。

## 凡例と注意

- **型・NULL・項目名**：モデル定義（`models.py`）から取得。
- **行数**：開発DBの現在値（2026-10-10 に `COUNT(*)` で確認）。
- **項目名は、モデルに書かれた名称**。業務上の正確な意味は、個別に未確認。
- **公開案**：私の案。「公開」「非公開」「要判断」の3種類。**BOSS判断**欄は空欄にしてある。
- 公開案の考え方：結合に使うID・コード・名称・分類は「公開」。認証情報・連絡先・権限・自由記述に近い列と、分析に不要な作成・更新日時は「非公開」。個人名など判断が分かれるものは「要判断」。
- 外部キー（`〜_id`）は、他のビューと結合するための列。公開すると、AIがビュー同士を結合できる。

---

## 1. 品番 `m_product`（2,850行）

| 列名 | 型 | 項目名 | 公開案 | BOSS判断 |
|---|---|---|---|---|
| id | 整数 | id | 公開 | |
| product_code | 文字30 | 品番コード | 公開 | |
| product_name | 文字100 | 品名 | 公開 | |
| product_name_halfwidth | 文字100・NULL可 | 品名半角 | 要判断 | |
| category | 文字20・NULL可 | カテゴリ | 公開 | |
| unit | 文字10 | 単位 | 公開 | |
| unit_price | 小数・NULL可 | 単価 | 要判断（金額情報） | |
| standard_lt_days | 整数・NULL可 | 標準LT(日) | 公開 | |
| image_url | 文字255・NULL可 | 画像URL | 非公開（分析に不要） | |
| stock_location | 文字100・NULL可 | 保管場所 | 公開 | |
| processing_area | 文字20・NULL可 | 加工先 | 公開 | |
| line_id | 外部キー・NULL可 | ライン情報 | 公開 | |
| process_id | 外部キー・NULL可 | 工程情報 | 公開 | |
| next_process_id | 外部キー・NULL可 | 後工程 | 公開 | |
| management_unit | 文字10・NULL可 | 管理区分 | 公開 | |
| self_lt_days | 整数・NULL可 | 自工程LT(日) | 公開 | |
| is_final_product | 真偽 | 最終製品 | 公開 | |
| is_line_final_product | 真偽 | ライン最終品 | 公開 | |
| is_phantom | 真偽 | 見なし組立 | 公開 | |
| is_virtual_set | 真偽 | 仮想セット品番 | 公開 | |
| order_lot_min | 整数・NULL可 | 最小発注数 | 公開 | |
| order_lot_multiple | 整数 | 発注倍数 | 公開 | |
| is_special_management_material | 真偽 | 特別管理材料 | 公開 | |
| specific_gravity | 小数・NULL可 | 比重(g/cm³) | 公開 | |
| size_length | 小数・NULL可 | 縦(mm) | 公開 | |
| size_width | 小数・NULL可 | 横(mm) | 公開 | |
| size_thickness | 小数・NULL可 | 厚さ(mm) | 公開 | |
| transfer_destination | 文字10・NULL可 | 移動先 | 公開 | |
| model_name | 文字50・NULL可 | 機種名 | 公開 | |
| identification_code | 文字20 | 識別記号 | 公開 | |
| product_group_id | 外部キー・NULL可 | 製品グループ | 公開 | |
| used_container_id | 外部キー・NULL可 | 使用容器 | 公開 | |
| capacity | 整数・NULL可 | 容器入り数 | 公開 | |
| is_active | 真偽 | 有効 | 公開 | |
| created_at | 日時 | 作成日時 | 非公開 | |
| updated_at | 日時 | 更新日時 | 非公開 | |

## 2. 工程 `m_process`（46行）

| 列名 | 型 | 項目名 | 公開案 | BOSS判断 |
|---|---|---|---|---|
| id | 整数 | id | 公開 | |
| process_code | 文字20 | 工程コード | 公開 | |
| process_name | 文字50 | 工程名 | 公開 | |
| line_id | 外部キー・NULL可 | ライン | 公開 | |
| is_outsource | 真偽 | 外注工程 | 公開 | |
| management_unit | 文字10 | 管理単位 | 公開 | |
| operating_rate | 小数 | 稼働率(%) | 公開 | |
| equipment_count | 整数 | 設備台数 | 公開 | |
| two_person_only | 真偽 | 2人1設備専用 | 公開 | |
| is_active | 真偽 | 有効 | 公開 | |
| created_at | 日時 | 作成日時 | 非公開 | |
| updated_at | 日時 | 更新日時 | 非公開 | |

## 3. ライン `m_line`（57行）

| 列名 | 型 | 項目名 | 公開案 | BOSS判断 |
|---|---|---|---|---|
| id | 整数 | id | 公開 | |
| line_code | 文字20 | ラインコード | 公開 | |
| line_name | 文字50 | ライン名 | 公開 | |
| calendar_id | 外部キー・NULL可 | 勤務カレンダ | 公開 | |
| lead_time_days | 整数・NULL可 | リードタイム（日） | 公開 | |
| line_type | 文字20 | ライン種別 | 公開 | |
| is_active | 真偽 | 有効 | 公開 | |
| use_direct_process | 真偽 | 工程直接展開 | 公開 | |
| created_at | 日時 | 作成日時 | 非公開 | |
| updated_at | 日時 | 更新日時 | 非公開 | |

## 4. 仕入先 `m_supplier`（29行）

別セッションの草案（計画書 §8.3）は、公開を `id`・`supplier_code`・`supplier_name`・`calendar_id`・`supplier_type` の5列としている。

| 列名 | 型 | 項目名 | 公開案 | BOSS判断 |
|---|---|---|---|---|
| id | 整数 | id | 公開 | |
| supplier_code | 文字20 | 仕入先コード | 公開 | |
| supplier_name | 文字100 | 仕入先名 | 公開 | |
| supplier_type | 文字20 | 仕入先区分 | 公開 | |
| contact_person | 文字100 | 担当者名 | 非公開（個人名・連絡先） | |
| phone_number | 文字30 | 電話番号 | 非公開（連絡先） | |
| order_email | 文字254 | 送信メールアドレス | 非公開（連絡先） | |
| calendar_id | 外部キー・NULL可 | 仕入先専用カレンダー | 公開 | |

## 5. 得意先 `m_customer`（3行）

| 列名 | 型 | 項目名 | 公開案 | BOSS判断 |
|---|---|---|---|---|
| id | 整数 | id | 公開 | |
| customer_code | 文字20 | 得意先コード | 公開 | |
| customer_name | 文字100 | 得意先名 | 公開 | |
| short_name | 文字40・NULL可 | 略称 | 公開 | |
| calendar_id | 外部キー・NULL可 | カレンダ | 公開 | |
| is_active | 真偽 | 有効 | 公開 | |
| created_at | 日時 | 作成日時 | 非公開 | |
| updated_at | 日時 | 更新日時 | 非公開 | |

## 6. 稼働カレンダ `m_calendar_day`（8,479行）

| 列名 | 型 | 項目名 | 公開案 | BOSS判断 |
|---|---|---|---|---|
| id | 整数 | id | 公開 | |
| calendar_id | 外部キー | カレンダ | 公開 | |
| target_date | 日付 | 対象日 | 公開 | |
| is_working_day | 真偽 | 稼働日 | 公開 | |
| is_delivery_day | 真偽 | 納入日 | 公開 | |
| is_order_day | 真偽 | 発注日 | 公開 | |
| is_holiday_work | 真偽 | 休日出勤 | 公開 | |
| work_minutes | 整数・NULL可 | 稼働分 | 公開 | |
| work_pattern_id | 外部キー・NULL可 | 勤務パターン | 公開 | |
| note | 文字100・NULL可 | 備考 | 非公開（DB確認済み: 8,479行中7,463行が空。残りは4種で、一部の文字が「?」に見える＝文字化けか表示の問題かは未確認。自由記述を含む） | |
| created_at | 日時 | 作成日時 | 非公開 | |
| updated_at | 日時 | 更新日時 | 非公開 | |

## 7. BOM（ヘッダ）`m_bom`（1,323行）

| 列名 | 型 | 項目名 | 公開案 | BOSS判断 |
|---|---|---|---|---|
| id | 整数 | id | 公開 | |
| parent_product_id | 外部キー | 親製品 | 公開 | |
| version | 文字20 | 版 | 公開 | |
| valid_from | 日付 | 有効開始日 | 公開 | |
| valid_to | 日付・NULL可 | 有効終了日 | 公開 | |
| is_active | 真偽 | 有効 | 公開 | |
| is_coproduct | 真偽 | 連産品BOM | 公開 | |
| created_at | 日時 | 作成日時 | 非公開 | |
| updated_at | 日時 | 更新日時 | 非公開 | |

## 8. BOM明細 `m_bom_item`（3,428行）

| 列名 | 型 | 項目名 | 公開案 | BOSS判断 |
|---|---|---|---|---|
| id | 整数 | id | 公開 | |
| bom_id | 外部キー | BOM | 公開 | |
| child_product_id | 外部キー | 子製品 | 公開 | |
| quantity | 小数 | 数量 | 公開 | |
| loss_rate | 小数・NULL可 | ロス率 | 公開 | |
| sourcing_type | 文字20 | 調達区分 | 公開 | |
| supplier_id | 外部キー・NULL可 | 仕入先 | 公開 | |
| process_id | 外部キー・NULL可 | 工程 | 公開 | |
| line_id | 外部キー・NULL可 | ライン | 公開 | |
| time_unit | 文字10 | 時間単位 | 公開 | |
| lead_time_days | 整数 | リードタイム(日) | 公開 | |
| duration_min | 整数・NULL可 | 所要時間(分) | 公開 | |
| is_coproduct_driver | 真偽 | 連産品代表品 | 公開 | |
| remark | 文字200・NULL可 | 備考 | 非公開（自由記述） | |
| created_at | 日時 | 作成日時 | 非公開 | |
| updated_at | 日時 | 更新日時 | 非公開 | |

## 9. ルーティング（ヘッダ）`m_routing`（540行）

| 列名 | 型 | 項目名 | 公開案 | BOSS判断 |
|---|---|---|---|---|
| id | 整数 | id | 公開 | |
| product_id | 外部キー | 製品 | 公開 | |
| routing_code | 文字30 | ルーティングコード | 公開 | |
| description | テキスト・NULL可 | 説明 | 要判断（DB確認済み: 540行中162行が空。残りは定型文5種。例「bomから自動生成した」330行・「CWL一括作成」37行。個人情報なし） | |
| is_default | 真偽 | 既定 | 公開 | |
| is_active | 真偽 | 有効 | 公開 | |
| valid_from_datetime | 日時・NULL可 | 有効開始日時 | 公開 | |
| valid_to_datetime | 日時・NULL可 | 有効終了日時 | 公開 | |
| created_at | 日時 | 作成日時 | 非公開 | |
| updated_at | 日時 | 更新日時 | 非公開 | |

## 10. ルーティング工程 `m_routing_step`（7,678行）

| 列名 | 型 | 項目名 | 公開案 | BOSS判断 |
|---|---|---|---|---|
| id | 整数 | id | 公開 | |
| routing_id | 外部キー | ルーティング | 公開 | |
| step_no | 整数 | 工程番号 | 公開 | |
| process_id | 外部キー・NULL可 | 工程 | 公開 | |
| line_id | 外部キー・NULL可 | ライン | 公開 | |
| supplier_id | 外部キー・NULL可 | 外作先 | 公開 | |
| output_product_id | 外部キー・NULL可 | 加工後品目 | 公開 | |
| source_bom_item_id | 外部キー・NULL可 | 元BOM明細 | 公開 | |
| hierarchy_path | 文字100 | 工程階層パス | 公開 | |
| hierarchy_depth | 整数 | 工程階層深さ | 公開 | |
| time_unit | 文字10 | 時間単位 | 公開 | |
| lead_time_days | 整数 | リードタイム(日) | 公開 | |
| start_offset_min | 整数・NULL可 | 開始オフセット(分) | 公開 | |
| duration_min | 整数・NULL可 | 所要時間(分) | 公開 | |
| parallel_count | 整数 | 並列数 | 公開 | |
| parallel_group | 整数 | 並列グループ | 公開 | |
| remark | 文字200・NULL可 | 備考 | 要判断（中身は親製品の品番コード。BOSS指摘・DBで確認済み。列名を別名にするかも判断） | |
| created_at | 日時 | 作成日時 | 非公開 | |
| updated_at | 日時 | 更新日時 | 非公開 | |

## 11. ルーティング工程の材料 `m_routing_step_material`（6,421行）

| 列名 | 型 | 項目名 | 公開案 | BOSS判断 |
|---|---|---|---|---|
| id | 整数 | id | 公開 | |
| routing_step_id | 外部キー | 工程 | 公開 | |
| component_id | 外部キー | 部品 | 公開 | |
| quantity | 小数 | 数量 | 公開 | |
| consume_timing | 文字10 | 消費タイミング | 公開 | |
| remark | 文字200・NULL可 | 備考 | 非公開（DB確認済み: 6,421行中294行が空。残りは「Auto from child BOM <番号>」形式の自動生成文745種。品番コードではない。番号の意味は未確認） | |
| created_at | 日時 | 作成日時 | 非公開 | |
| updated_at | 日時 | 更新日時 | 非公開 | |

## 12. ユーザー `auth_user`（98行）

目的：作業者別の実績。個人名を公開する場合は、外部AIへ送る前に一時IDへ置換する。

| 列名 | 型 | 項目名 | 公開案 | BOSS判断 |
|---|---|---|---|---|
| id | 整数 | ID | 公開（結合用） | |
| password | 文字128 | パスワード | **非公開（認証情報。常に非公開）** | |
| last_login | 日時・NULL可 | 最終ログイン | 非公開 | |
| is_superuser | 真偽 | スーパーユーザー権限 | 非公開（権限情報） | |
| username | 文字150 | ユーザー名 | 非公開（ログインID） | |
| first_name | 文字150 | 名 | 要判断（個人名） | |
| last_name | 文字150 | 姓 | 要判断（個人名） | |
| email | 文字254 | メールアドレス | 非公開（連絡先） | |
| is_staff | 真偽 | スタッフ権限 | 非公開（権限情報） | |
| is_active | 真偽 | 有効 | 公開 | |
| date_joined | 日時 | 登録日 | 非公開 | |

## 13. ユーザープロフィール `accounts_userprofile`（98行）

目的：部署別の集計。主キーは `user_id`（`auth_user.id` と1対1）。

| 列名 | 型 | 項目名 | 公開案 | BOSS判断 |
|---|---|---|---|---|
| user_id | 外部キー（主キー） | ユーザー | 公開（結合用） | |
| employee_code | 文字32・NULL可 | 社員コード | 要判断（個人を特定できる） | |
| role | 文字20 | 役割 | 公開 | |
| employment_type | 文字20 | 雇用形態 | 要判断 | |
| department_id | 外部キー・NULL可 | 所属部署 | 公開 | |
| division_id | 外部キー・NULL可 | 事業部 | 公開 | |
| group_id | 外部キー・NULL可 | 係 | 公開 | |
| team_id | 外部キー・NULL可 | 班 | 公開 | |
| unit_id | 外部キー・NULL可 | グループ | 公開 | |
| joined_on | 日付・NULL可 | 入社日 | 要判断 | |
| is_system_admin | 真偽 | システム管理者 | 非公開（権限情報） | |
| created_at | 日時 | 作成日時 | 非公開 | |
| updated_at | 日時 | 更新日時 | 非公開 | |

## 14. 部署 `accounts_department`（39行）

| 列名 | 型 | 項目名 | 公開案 | BOSS判断 |
|---|---|---|---|---|
| id | 整数 | ID | 公開 | |
| name | 文字100 | 部署名 | 公開 | |
| level | 文字20 | 階層 | 公開 | |
| parent_id | 外部キー・NULL可 | 親部署 | 公開 | |
| display_id | 整数 | 表示順 | 公開 | |

---

## BOSS判断の結果（2026-10-10。判断画面の保存内容を転記）

「公開」と決めた列だけをビューに含める。「未決定」の列は、非公開として扱う（BOSSの確認待ち）。

| テーブル | 公開する列 | 非公開と決めた列 | 未決定（＝非公開扱い） |
|---|---|---|---|
| `m_product`（36列すべて判断済み） | 32列（`created_at`・`updated_at`を含む） | `image_url`、`product_name_halfwidth`、`is_phantom`、`self_lt_days` | なし |
| `m_process` | 10列 | なし | `created_at`、`updated_at` |
| `m_line` | 8列 | なし | `created_at`、`updated_at` |
| `m_supplier` | 5列（`id`、`supplier_code`、`supplier_name`、`supplier_type`、`calendar_id`） | なし | `contact_person`、`phone_number`、`order_email` |
| `m_customer` | 6列 | なし | `created_at`、`updated_at` |
| `m_calendar_day` | 9列 | なし | `note`、`created_at`、`updated_at` |
| `m_bom` | 7列 | なし | `created_at`、`updated_at` |
| `m_bom_item` | 13列 | `remark` | `created_at`、`updated_at` |
| `m_routing` | 8列 | `description` | `created_at`、`updated_at` |
| `m_routing_step` | 16列＋`remark` | なし | `created_at`、`updated_at` |
| `m_routing_step_material` | 5列 | なし | `remark`、`created_at`、`updated_at` |
| `auth_user` | `id`、`username`、`first_name`、`last_name`、`is_staff`、`is_active` | なし | `password`、`last_login`、`is_superuser`、`email`、`date_joined` |
| `accounts_userprofile` | 11列（`employee_code`、`employment_type`、`joined_on`、`is_system_admin`を含む。`employee_code`は、BOSS決定 2026-10-10で、ユーザー名と社員コードの両方を公開） | なし | `created_at`、`updated_at` |
| `accounts_department` | 5列すべて | なし | なし |

- **`auth_user.username`**：公開する。チャットのSQL検査（`SENSITIVE_IDENTIFIER`）に当たる列名のため、ビューでは別名 `login_id` で出す（BOSS承認 2026-10-10）。
- **`auth_user` の管理用アカウント**：ビューから除外する（BOSS決定 2026-10-10）。除外の基準は未定（BOSS確認待ち）。
- **`m_routing_step.remark`**：公開する。中身は親製品の品番コードなので、ビューでは別名 `parent_product_code` で出す（BOSS決定）。
- **`m_product.management_unit`**・**`m_process.management_unit`**：`DAY`=日単位管理（マクロ計画）、`MINUTE`=分単位管理（ミクロ実行）。モデル定義より。

## 未確認の事項（BOSSの判断前に、必要に応じて確認する）

1. 各列の**業務上の正確な意味**と**実データの値の分布**（NULLの割合、コードの一意性など）は、未確認。
2. 工程実績の作業者は文字列（`operator_name`）で、ユーザーIDではない。実績とユーザーのビューを確実に結合できるかは、実績ビューの確認時に調べる。
3. `m_calendar`（カレンダのヘッダ）、勤務パターン、製品グループ、容器、部署の階層（事業部・係・班・グループが `accounts_department` を指すか）は、作成対象に入っていない。必要ならBOSSが指示する。
4. 稼働カレンダの日付は暦日で、日替わり8時の「生産日」ではない。

## 次の手順

1. BOSSが、各表の**BOSS判断**欄（または公開案の変更点だけ）を回答する。
2. 回答に基づき、列ごとの業務上の意味と実データの確認結果を追記する。
3. BOSSの承認後、マイグレーション（`CREATE OR REPLACE VIEW`）を作成する。`migrate` はBOSSが実行する。
