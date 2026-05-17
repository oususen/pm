# FB外作管理仕様書

フランスベッド株式会社（以下FB）からの受注品を外作先で加工する業務フローを管理するシステム。

---

## 1. 背景・既存との違い

| 項目 | 既存3社（Tiera/Rieden/Kubota） | FB |
|------|-------------------------------|-----|
| 生産方式 | 社内ライン生産 | **外作**（コンプ加工） |
| 発注パターン | 毎日・定番品・少量 | **大ロット・不定期** |
| スケジュール主体 | 弊社（計画生成） | **外作先主導**（分割計画） |
| 材料 | 社内在庫から消費 | **弊社が購入→外作先へ無償支給** |
| キャパ制約 | 社内ラインで吸収 | **外作先の日キャパ超え→分割** |

---

## 2. 全体フロー

```
① FB受注取込（CSV）
   └→ 案件自動生成（1品目×1数量×1塗装日 = 1案件）
        │
        ▼
② 外作先展開Excel出力
   └→ 制約条件を計算して記載：
       ・最遅完了日 = 塗装日 - 運送LT（顧客納入）
       ・最早着手日 = 今日 + 材料調達LT + 支給運送LT
       → Excelを外作先へ送付
       → 外作先がこの枠内で分割計画を記入して返却
        │
        ▼
③ 分割計画取込（外作先記入済みExcel）
   └→ 各分割の加工日・数量を登録
        │
        ▼
④ 材料所要量展開
   └→ 分割計画 × BOM → 材料別・支給日別の必要数量算出
        │
        ▼
⑤ 進捗管理
   └→ 材料支給 / 加工完了 / 出荷 のステータス更新
```

---

## 3. 制約条件（タイムライン）

外作先は「最早着手日〜最遅完了日」の間で自由に分割計画を立てる。

```
        材料調達LT    支給運送LT         加工期間           運送LT
発注日 ────┼───────────┼──────────── ？ ──────────────┼─────────── 塗装日
          材料発注     材料支給          外作先が          完成品出荷
                     （最早着手日）     この区間を        （最遅完了日）
                                      分割計画で埋める
```

- **最早着手日** = 発注日 + MAX(BOM内各材料の調達LT) + 支給運送LT
- **最遅完了日** = 塗装日 - 運送LT（顧客納入）
- 外作先はこの枠内で、自社の他案件状況に応じて分割する
- ※材料調達LTは材料ごとに異なるため、最も長いLTの材料がボトルネックになる

---

## 4. 管理単位

**案件（Case）= 1受注品目**

CSVの1行 = 1案件として管理。案件番号 = 塗装日＋品目コード。

```
例: 20260609-B850070311091
    品目: B850070311091 FBR-ﾒｲﾝﾌﾚｰﾑRﾌﾞｸﾐ
    数量: 150個
    塗装名: FBR GY（顧客情報）
    塗装日: 2026/6/9（顧客指定）
```

---

## 5. データモデル

### 5.1 マスタ系

#### Subcontractor（外作先マスタ）

| フィールド | 型 | 説明 |
|-----------|------|------|
| id | AutoField | PK |
| name | CharField | 外作先名 |
| daily_capacity | IntegerField | 日キャパ（参考値） |
| transport_lt_supply | IntegerField | 支給運送LT（日数） |
| transport_lt_delivery | IntegerField | 完成品運送LT（日数） |
| notes | TextField | 備考 |

※ 現時点では1社固定だが、マスタ化しておく。

#### OutsourceItem（外作品目マスタ）

| フィールド | 型 | 説明 |
|-----------|------|------|
| id | AutoField | PK |
| item_code | CharField | 品目コード（B850070311091等） |
| product_number | CharField | 品番（自動導出: B852950421091→852950-4210） |
| item_name | CharField | 品目名称 |
| subcontractor | FK(Subcontractor) | 外作先 |
| customer_delivery_lt | IntegerField | 顧客納入LT（運送日数） |
| is_active | BooleanField | 有効フラグ |

**品番自動導出ルール:** item_codeの先頭Bを除去し、先頭6桁-次4桁（例: `B852950421091` → `852950-4210`）。save時に自動設定。

#### OutsourceBOM（外作BOM）

| フィールド | 型 | 説明 |
|-----------|------|------|
| id | AutoField | PK |
| item | FK(OutsourceItem) | 親品目 |
| material_code | CharField | 材料コード |
| material_name | CharField | 材料名称 |
| quantity_per | DecimalField | 員数（親1個あたり） |
| unit | CharField | 単位 |
| supplier | FK(m_supplier) | 調達先（既存仕入先マスタ参照） |
| supplier_name | CharField | 調達先名（save時に自動同期） |
| procurement_lt | IntegerField | 材料調達LT（日数）※材料ごとに異なる |

### 5.2 トランザクション系

#### OutsourceOrder（外作受注 = 案件）

| フィールド | 型 | 説明 |
|-----------|------|------|
| id | AutoField | PK |
| case_no | CharField | 案件番号（塗装日+品目コード: 20260609-B850070311091） |
| item | FK(OutsourceItem) | 品目 |
| order_qty | IntegerField | 受注数量 |
| painting_name | CharField | 塗装名（顧客情報） |
| painting_date | DateField | 塗装日（顧客指定納期） |
| earliest_start | DateField | 最早着手日（自動計算） |
| latest_finish | DateField | 最遅完了日（自動計算） |
| status | CharField | ステータス（後述） |
| imported_at | DateTimeField | CSV取込日時 |
| notes | TextField | 備考 |

**ステータス遷移:**
```
IMPORTED → SENT_TO_SUB → SPLIT_REGISTERED → IN_PROGRESS → COMPLETED
（取込済）  （展開送付済） （分割計画登録済）  （加工中）     （完了）
```

#### OutsourceSplit（分割計画）

| フィールド | 型 | 説明 |
|-----------|------|------|
| id | AutoField | PK |
| order | FK(OutsourceOrder) | 案件 |
| sequence | IntegerField | 分割連番 |
| process_date | DateField | 加工予定日 |
| qty | IntegerField | 分割数量 |
| material_supplied | BooleanField | 材料支給済フラグ |
| process_completed | BooleanField | 加工完了フラグ |
| shipped | BooleanField | 出荷済フラグ |

#### MaterialRequirement（材料所要量）

| フィールド | 型 | 説明 |
|-----------|------|------|
| id | AutoField | PK |
| split | FK(OutsourceSplit) | 分割計画 |
| material_code | CharField | 材料コード |
| material_name | CharField | 材料名称 |
| supplier_name | CharField | 調達先名 |
| required_qty | DecimalField | 必要数量 |
| supply_date | DateField | 支給予定日（加工日 - 支給運送LT） |
| ordered | BooleanField | 発注済フラグ（材料メーカーへ発注したか） |
| ordered_at | DateField | 発注日 |
| supplied_qty | DecimalField | 支給済数量 |
| supplied | BooleanField | 支給完了フラグ（外作先へ支給したか） |

**2つの状態の違い:**

- `ordered`: 材料メーカーへの発注状態（材料手配画面で管理）
- `supplied`: 外作先への支給状態（材料所要量画面で管理）

テーブル名: `outsource_material_requirement`

#### SubcontractorDelivery（外作先納入＝受入記録）

外作先から弊社への完成品納入を記録する。1分割に対して複数回の分納を記録可能。

| フィールド | 型 | 説明 |
|-----------|------|------|
| id | AutoField | PK |
| split | FK(OutsourceSplit) | 分割計画 |
| delivery_date | DateField | 納入日 |
| qty | IntegerField | 受入数量 |
| inspector | CharField | 検収者 |
| notes | TextField | 備考 |
| created_at | DateTimeField | 登録日時 |

テーブル名: `outsource_subcontractor_delivery`

**自動ステータス更新:** 受入数量合計 ≥ 分割数量 → `split.process_completed = True`

#### CustomerShipment（顧客出荷記録）

弊社からお客様（FB）への出荷を記録する。1分割に対して複数回の分納を記録可能。

| フィールド | 型 | 説明 |
|-----------|------|------|
| id | AutoField | PK |
| split | FK(OutsourceSplit) | 分割計画 |
| shipment_date | DateField | 出荷日 |
| qty | IntegerField | 出荷数量 |
| person | CharField | 担当者 |
| notes | TextField | 備考 |
| created_at | DateTimeField | 登録日時 |

テーブル名: `outsource_customer_shipment`

**自動ステータス更新:** 出荷数量合計 ≥ 分割数量 → `split.shipped = True`

### 5.3 テーブル関連図

```
Subcontractor ─┐
               │ 1:N
OutsourceItem ─┤
  │            │
  │ BOM(1:N)   │
  ▼            │
OutsourceBOM   │
               │
OutsourceOrder ◄── FK(item)
  │
  │ 1:N
  ▼
OutsourceSplit
  │
  ├─ 1:N ──► MaterialRequirement（材料所要量）
  │
  ├─ 1:N ──► SubcontractorDelivery（外作先→弊社の納入記録）
  │
  └─ 1:N ──► CustomerShipment（弊社→顧客への出荷記録）
```

### 5.4 全テーブル一覧

| テーブル名 | モデル名 | 区分 | 説明 |
|-----------|---------|------|------|
| outsource_subcontractor | Subcontractor | マスタ | 外作先マスタ |
| outsource_item | OutsourceItem | マスタ | 外作品目マスタ |
| outsource_bom | OutsourceBOM | マスタ | 外作BOM（品目→材料） |
| outsource_order | OutsourceOrder | トランザクション | 受注案件 |
| outsource_split | OutsourceSplit | トランザクション | 分割計画 |
| outsource_material_requirement | MaterialRequirement | トランザクション | 材料所要量 |
| outsource_subcontractor_delivery | SubcontractorDelivery | トランザクション | 外作先納入記録 |
| outsource_customer_shipment | CustomerShipment | トランザクション | 顧客出荷記録 |

---

## 6. 画面仕様

### 6.0 共通UI仕様

- **塗装日期間フィルタ**: 全画面に共通で設置。初期値は当月（月初〜月末）
- **前月/次月ボタン**: 塗装日フィルタの左右に配置。クリックで月単位切替＋自動リロード

### 6.1 FB受注一覧画面

**機能:**

- 受注案件一覧表示（ステータス/塗装日/品目コード・名称で検索）
- CSV取込画面への導線
- 塗装日期間フィルタ（当月初期値＋前月/次月ボタン）

### 6.1.1 CSV取込画面

**機能:**

- CSVファイル選択・アップロード
- プレビュー表示（取込前確認）
- 案件自動生成（品目マスタ未登録の場合は警告）

**CSVフォーマット:**
```
品目コード,品目名称,塗装名,塗装日,数量
B850070311091,FBR-ﾒｲﾝﾌﾚｰﾑRﾌﾞｸﾐ,FBR GY,2026/6/9,150
```

### 6.2 外作先展開Excel出力画面

**機能:**

- 案件選択（未送付案件一覧）
- 制約条件自動計算（最早着手日・最遅完了日）
- Excel出力（外作先が分割計画を記入するテンプレート）
- 送付済みステータス更新
- 塗装日期間フィルタ（当月初期値＋前月/次月ボタン）

**Excel出力内容:**
| 案件No | 品目コード | 品目名称 | 数量 | 最早着手日 | 最遅完了日 | 加工日1 | 数量1 | 加工日2 | 数量2 | ... |
|--------|-----------|---------|------|-----------|-----------|---------|-------|---------|-------|-----|
| FB-2026-001 | B850070311091 | FBR-ﾒｲﾝﾌﾚｰﾑR | 150 | 2026/5/20 | 2026/6/6 | (記入欄) | (記入欄) | ... | ... | ... |

### 6.3 分割計画取込画面

**機能:**

- 外作先記入済みExcel取込
- 分割内容プレビュー・確認
- 制約違反チェック（最早着手日〜最遅完了日の範囲外は警告）
- 数量合計チェック（分割合計 = 受注数量）
- BOM展開実行（材料所要量自動生成）

### 6.4 材料所要量一覧画面

**機能:**

- 3つの表示モード: 案件別（折り畳み式）/ 支給日別 / 材料別集約
- 支給日でソート（直近の支給予定を上位表示）
- 支給実績登録（支給済みチェック）
- 塗装日期間フィルタ（当月初期値＋前月/次月ボタン）

### 6.5 材料手配画面

**機能:**

- メーカ別（調達先別）グループ表示
- 注文書Excel出力（メーカ別）
- 塗装日期間フィルタ（当月初期値＋前月/次月ボタン）

### 6.6 納入・出荷管理画面

**機能:**

- タブ切替: 外作先納入（検収） / 顧客出荷
- 案件別アコーディオン表示（ヘッダーにステータスバッジ・進捗表示）
- 分割ごとにインライン登録（日付・数量・検収者/担当者）
- 数量デフォルト: 残数量、担当者デフォルト: ログインユーザー
- 登録済み実績の一覧表示・削除
- 部分検収・部分納入対応（1分割に対し複数回登録可能）
- 塗装日期間フィルタ（当月初期値＋前月/次月ボタン）

### 6.7 進捗管理画面

**機能:**

- 案件別進捗一覧
- 3列プログレスバー: 支給進捗（青）/ 加工進捗（緑）/ 出荷進捗（オレンジ）
- 進捗自動判定（実績データから）:
  - 材料支給: 該当分割の材料所要量が全て支給完了 → 自動ON
  - 加工完了: 受入数量合計 ≥ 分割数量 → 自動ON
  - 出荷済: 出荷数量合計 ≥ 分割数量 → 自動ON
- 自動判定時はチェックロック＋「自動」タグ表示、部分実績は数量表示（例: 50/100）
- 手動オーバーライド: 自動判定がOFFの場合は従来通り手動チェック可能
- 塗装日期間フィルタ（当月初期値＋前月/次月ボタン）

---

## 7. API設計

| メソッド | エンドポイント | 機能 |
|---------|--------------|------|
| POST | /api/outsource/orders/import-csv/ | CSV取込 |
| GET | /api/outsource/orders/ | 案件一覧（塗装日期間フィルタ対応） |
| GET | /api/outsource/orders/{id}/ | 案件詳細 |
| POST | /api/outsource/orders/{id}/calculate-constraints/ | 制約条件再計算 |
| POST | /api/outsource/orders/export-excel/ | 外作先展開Excel出力 |
| POST | /api/outsource/orders/import-split-excel/ | 分割計画Excel取込 |
| POST | /api/outsource/orders/{id}/explode-materials/ | BOM展開（材料所要量生成） |
| GET | /api/outsource/splits/ | 分割計画一覧（塗装日期間フィルタ対応） |
| PUT | /api/outsource/splits/{id}/ | 分割計画更新 |
| GET | /api/outsource/materials/ | 材料所要量一覧（塗装日期間フィルタ対応） |
| POST | /api/outsource/materials/{id}/supply/ | 支給実績登録 |
| POST | /api/outsource/materials/purchase-order/ | メーカ別注文書Excel出力 |
| GET | /api/outsource/deliveries/ | 外作先納入一覧（塗装日期間フィルタ対応） |
| POST | /api/outsource/deliveries/ | 外作先納入登録 |
| DELETE | /api/outsource/deliveries/{id}/ | 外作先納入削除 |
| GET | /api/outsource/shipments/ | 顧客出荷一覧（塗装日期間フィルタ対応） |
| POST | /api/outsource/shipments/ | 顧客出荷登録 |
| DELETE | /api/outsource/shipments/{id}/ | 顧客出荷削除 |
| GET | /api/outsource/subcontractors/ | 外作先マスタCRUD |
| GET | /api/outsource/items/ | 品目マスタCRUD |
| GET | /api/outsource/bom/ | BOMマスタCRUD |

**共通フィルタパラメータ:**

- `painting_date_from` / `painting_date_to`: 塗装日期間絞込（全画面共通）

---

## 8. フロントエンド構成

### グローバルナビゲーション

FBは**独立したトップレベルメニュー**として追加（既存メニューの子ではない）。

```
受注 | 生産 | 購買 | 出荷 | 在庫 | 品質 | ... | 【FB】 | マスタ | 設定
```

GlobalNavigation.vue の `mainTabs` に追加：

```javascript
{ id: 'outsource', label: 'FB', link: '/outsource/menu', resource: 'outsource' }
```

### ルーティング構成

```
pm-ui/src/router/outsource.js    # 新規ルーター

/outsource/menu                   # FBメニュー（トップ）
/outsource/orders                 # 受注一覧
/outsource/orders/import          # CSV取込
/outsource/orders/:id             # 案件詳細
/outsource/excel-export           # 外作先展開Excel出力
/outsource/splits/import          # 分割計画取込
/outsource/materials              # 材料所要量一覧（案件別/支給日別/材料別集約）
/outsource/procurement            # 材料手配（メーカ別表示＋注文書Excel出力）
/outsource/delivery               # 納入・出荷管理（外作先受入/顧客出荷）
/outsource/progress               # 進捗管理
/outsource/masters                # マスタ管理（外作先/品目/BOMタブ切替）
```

### 画面構成

```
pm-ui/src/views/outsource/
├── OutsourceMenu.vue             # FBメニュートップ
├── OutsourceOrderList.vue        # 受注一覧
├── OutsourceOrderImport.vue      # CSV取込
├── OutsourceOrderDetail.vue      # 案件詳細
├── OutsourceExcelExport.vue      # 外作先展開Excel出力
├── OutsourceSplitImport.vue      # 分割計画取込
├── OutsourceMaterialList.vue     # 材料所要量一覧
├── OutsourceProcurement.vue      # 材料手配（メーカ別＋注文書Excel出力）
├── OutsourceDelivery.vue         # 納入・出荷管理（タブ: 外作先納入/顧客出荷）
├── OutsourceProgress.vue         # 進捗管理
└── masters/
    └── OutsourceMasters.vue      # マスタ管理（外作先/品目/BOMタブ切替）
```

---

## 9. 実装計画

### Phase 1: 基盤（マスタ + CSV取込）

1. Django app `outsource` 新設
2. モデル作成・マイグレーション
3. 外作先マスタ・品目マスタ・BOM登録画面
4. CSV取込機能（案件自動生成）

### Phase 2: 外作先展開

5. 制約条件計算ロジック
6. Excel出力機能（テンプレート生成）
7. ステータス管理

### Phase 3: 分割計画・材料展開

8. 分割計画Excel取込
9. BOM展開→材料所要量生成
10. 材料所要量一覧画面

### Phase 4: 進捗管理

11. 進捗管理画面
12. 支給実績・加工実績登録
13. 遅延アラート

---

## 9. 外作先情報

| 項目 | 値 |
|------|-----|
| 外作先数 | 1社固定 |
| 加工内容 | コンプ加工 |
| 支給方式 | 無償支給 |
| 分割主導 | 外作先（弊社は制約条件を提示） |

---

## 10. 顧客情報

| 項目 | 値 |
|------|-----|
| 略称 | FB |
| 全称 | フランスベッド株式会社 |
| 発注パターン | 大ロット・不定期 |
| CSV提供項目 | 品目コード、品目名称、塗装名、塗装日、数量 |
