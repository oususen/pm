# PG版PM 画面確認チェックリスト

- 作成日: 2026-10-22
- 目的: PostgreSQL版(`pm_pg`)の画面が、MySQL版と**同じ表示・同じ数値**になることを確認し、切替の可否判断に使う
- 状態: **案(私が作成。優先度は私の推測で、BOSSの判断で変更する)**。まだ1画面も確認していない
- 出典: `pm_pg`リポジトリ `pm-ui/src/router/*.js` の画面定義(redirectのみの定義は除外)。画面名は`pageTitle`

## 1. 確認の進め方

### 1-1. 比較の前提(重要)

| | MySQL版 | PG版 |
|---|---|---|
| URL | `https://10.0.1.139:8501` | `https://10.0.1.139:18501` |
| DB | 新PCのMySQL `pm_db`(**2026-10-20 23:43のダンプ**) | **同じダンプから作った新しいPG DB**(未作成。下記) |

- **同じデータ同士で比べる**ことが前提。MySQL版は10/20 23:43のダンプなので、PG版も**同じダンプ**から、手をつけていない新しいDB(例: `pm_pg_ui`)を作ってつなぐ(切替スクリプトで約8分)。
- `pm_pg_rh1`は実績入力で書き換え済み、`pm_pg_rh2`は別の(10/22取得の)ダンプのため、比較には使わない。
- 日時・計算結果(在庫・進度)は、**画面の数字を目で見て同じと判断せず**、同一日・同一製品の値をDBで確認する(CLAUDE.md)。

### 1-2. 各画面の確認項目(共通)

| 列 | 内容 |
|---|---|
| 表示 | 画面が開く。エラー表示・空白・読み込み続行がない |
| 数値一致 | 同じ条件(日付・工程・製品)で、MySQL版と**件数・数値・並び順**が同じ |
| 登録・更新 | 「書込」が○の画面だけ。試験データ1件を登録→画面に出る→(削除できる画面は)削除。**試験データは作業後に削除し、削除したことを記録** |
| 備考 | 気づいた違い(文言、順序、日付、エラーの内容)を具体的に |

- **「書込」の列は、ルーティングの`permission: edit`の有無だけから自動で付けたもの**で、完全ではない。例えば「進度監視」のように、権限の指定がなくても、画面内の**ボタン(再計算など)がデータを書き換える**画面がある。確認の際は、画面上の登録・更新・削除・再計算・取込・確定のボタンの有無を目で確認し、あれば「登録・更新」の確認を行うこと(「−」は暫定)。
- 結果の記入: ○=問題なし、×=問題あり(備考に内容)、−=対象外/データがなく確認できない。
- 「:id」などを含むパスは、一覧画面から該当データを開いて確認する(直接アドレスを入力しない)。
- **書込を伴う確認は、必ず試験用のPG DBで行い、稼働中のMySQL版(8501)には書き込まない。**

### 1-3. 優先度(私の案)

| 優先度 | 対象 | 理由 |
|---|---|---|
| **A** | 生産・在庫・受注・出荷・購買(仕入)・外作 | 日常業務の中心で、在庫・進度・計画の**計算**を含み、MySQLとPGの差が出やすい。切替当日に使われる |
| **B** | 品質・マスタ・設定・消耗品・残業・シフト・通知・タスク・設変 | 日常的に使うが、計算より、登録・一覧が中心 |
| **C** | AI・OCR・マニュアル | AI分析は本番では無効(計画書の方針)。ビュー(`v_ai_*`)もPGにない |

### 1-4. 必須の確認(切替当夜計画 §6 F1〜F9)

| # | 項目 | 合格基準 | 結果 |
|---|---|---|---|
| F1 | ログイン | `admin`でログインできる | ○(2026-10-21、PG版で確認済み) |
| F2 | 受注一覧・受注展開 | エラーなく表示、件数がMySQL版と一致 | |
| F3 | 生産計画(ガント) | 表示でき、同一日の`line_backlog`/`line_plan`の値が一致 | |
| F4 | 在庫・進度の画面(進度監視) | 同一日・同一製品でMySQL版と一致(DBで確認) | |
| F5 | スポット実績入力の工程一覧 | 200で工程が出る | ○(2026-10-21、jsonb変換後に確認済み) |
| F6 | 追加登録(試験データ1件)と削除 | 主キー重複エラーなし(シーケンス)。試験データは削除 | 一部○(ブレーキ実績入力・設備トラブル記録は成功。削除は未実施) |
| F7 | 日時の表示 | 8時区切りの「今日」判定、JSTで正しい | |
| F8 | 文字列検索(製品コード等の大文字小文字) | MySQL版と同じ件数 | |
| F9 | NULLを含む並び替え画面 | MySQL版と順序が一致(NULLの並び順の差) | |

## 2. 画面一覧 — 優先度 A

### 生産 (`production`、56画面)

| # | 画面 | パス | 書込 | 表示 | 数値一致 | 登録・更新 | 備考 |
|---|---|---|---|---|---|---|---|
| 1 | 生産管理メニュー | `/production/menu` |  | | | − | |
| 2 | 朝礼一覧 | `/production/morning-meetings` |  | | | − | |
| 3 | 朝礼作成 | `/production/morning-meetings/new` | ○ | | |  | |
| 4 | 朝礼編集 | `/production/morning-meetings/:id/edit` ※個別データ | ○ | | |  | |
| 5 | 朝礼実行 | `/production/morning-meetings/:id/run` ※個別データ |  | | | − | |
| 6 | 未使用機能 | `/production/unused` |  | | | − | |
| 7 | ライン需要一覧 | `/production/line-demands` |  | | | − | |
| 8 | ライン勤務カレンダ | `/production/line-calendars` | ○ | | |  | |
| 9 | 進捗管理 | `/production/progress` |  | | | − | |
| 10 | 進度のみ | `/production/progress-only` |  | | | − | |
| 11 | 進度監視 | `/production/progress-monitor` |  | | | − | |
| 12 | 生産計画入力 | `/production/plan-input` | ○ | | |  | |
| 13 | 生産計画変更履歴 | `/production/plan-change-history` |  | | | − | |
| 14 | ガントチャート設定 | `/production/gantt-display-product-map` |  | | | − | |
| 15 | ガントチャート設定 新規 | `/production/gantt-display-product-map/new` |  | | | − | |
| 16 | ガントチャート設定 編集 | `/production/gantt-display-product-map/:id/edit` ※個別データ |  | | | − | |
| 17 | デフォルト開始時刻設定 | `/production/default-start-time` | ○ | | |  | |
| 18 | 在庫 / 残量一覧 | `/production/inventory` |  | | | − | |
| 19 | 構成部品在庫一覧 | `/production/component-inventory` |  | | | − | |
| 20 | 在庫引当一覧 | `/production/stock-allocations` |  | | | − | |
| 21 | 安全在庫一覧 | `/production/safety-stock-list` |  | | | − | |
| 22 | 在庫引当 新規登録 | `/production/stock-allocations/new` |  | | | − | |
| 23 | 在庫引当 編集 | `/production/stock-allocations/:id/edit` ※個別データ |  | | | − | |
| 24 | 製造指示一覧 | `/production/orders` |  | | | − | |
| 25 | 製造指示 新規登録 | `/production/orders/new` |  | | | − | |
| 26 | 製造指示 編集 | `/production/orders/:id/edit` ※個別データ |  | | | − | |
| 27 | 工程実績入力 | `/production/orders/:id/actuals` ※個別データ |  | | | − | |
| 28 | 日次ミックス順序ボード（7品固定運転向け） | `/production/sequence-board` |  | | | − | |
| 29 | ライン稼働監視 | `/production/line-monitor` |  | | | − | |
| 30 | 実績入力（カメラ） | `/production/camera-actual-input` | ○ | | |  | |
| 31 | ライン作業記録 | `/production/mobile-input` |  | | | − | |
| 32 | 工程作業記録 | `/production/mobile-process-input` | ○ | | |  | |
| 33 | 工程作業記録（タブレット） | `/production/tablet-process-input` | ○ | | |  | |
| 34 | １人２工程入力 | `/production/dual-process-input` | ○ | | |  | |
| 35 | 同時加工入力 | `/production/simultaneous-process-input` | ○ | | |  | |
| 36 | 2人1設備入力 | `/production/two-person-one-equipment-input` | ○ | | |  | |
| 37 | レーザー実績入力 | `/production/laser-process-input` | ○ | | |  | |
| 38 | 仕損品記録 | `/production/scrap-record` | ○ | | |  | |
| 39 | 生産実績照会 | `/production/record-inquiry` |  | | | − | |
| 40 | 実績変更 | `/production/record-edit` | ○ | | |  | |
| 41 | 工程ガント | `/production/process-gantt` |  | | | − | |
| 42 | 単独計画 | `/production/single-process-plan` | ○ | | |  | |
| 43 | 仕損履歴 | `/production/scrap-history` |  | | | − | |
| 44 | ブレーキライン実績入力 | `/production/brake-line-input` | ○ | | |  | |
| 45 | 工程別コツ・注意事項管理 | `/production/process-knowledge-manager` | ○ | | |  | |
| 46 | 工程別コツ・注意事項 | `/production/process-knowledge-viewer` |  | | | − | |
| 47 | スポット実績入力 | `/production/spot-line-input` | ○ | | |  | |
| 48 | 工程作業記録（デスクトップ） | `/production/desktop-process-input` | ○ | | |  | |
| 49 | 製品情報編集 | `/production/product-info-editor` | ○ | | |  | |
| 50 | 計画乖離レポート | `/production/plan-deviation-report` |  | | | − | |
| 51 | 負荷計算 | `/production/load-calc-menu` |  | | | − | |
| 52 | 出来高集計 | `/production/actual-cycle-time` |  | | | − | |
| 53 | ラインサイクルタイム入力 | `/production/line-cycle-time` | ○ | | |  | |
| 54 | 長期負荷チャート | `/production/line-load-chart` |  | | | − | |
| 55 | 進度PDF突合 | `/production/progress-pdf-compare` |  | | | − | |
| 56 | トラブル対応（レーザ） | `/production/laser-trouble-response` |  | | | − | |

### 在庫 (`inventory`、10画面)

| # | 画面 | パス | 書込 | 表示 | 数値一致 | 登録・更新 | 備考 |
|---|---|---|---|---|---|---|---|
| 57 | 在庫管理 | `/inventory` |  | | | − | |
| 58 | 在庫調整メニュー | `/inventory/adjustments` |  | | | − | |
| 59 | 棚卸現物入力 | `/inventory/stocktake-input` |  | | | − | |
| 60 | 棚卸結果確認 | `/inventory/stocktake-results` |  | | | − | |
| 61 | 棚卸レイアウト編集 | `/inventory/stocktake-layout` |  | | | − | |
| 62 | 進度調整 | `/inventory/adjustments/progress` |  | | | − | |
| 63 | 在庫調整 | `/inventory/adjustments/stock` |  | | | − | |
| 64 | 計画在庫調整 | `/inventory/adjustments/planned-stock` |  | | | − | |
| 65 | 調整履歴 | `/inventory/adjustments/history` |  | | | − | |
| 66 | 実進度求め | `/inventory/actual-progress` |  | | | − | |

### 受注 (`orders`、9画面)

| # | 画面 | パス | 書込 | 表示 | 数値一致 | 登録・更新 | 備考 |
|---|---|---|---|---|---|---|---|
| 67 | 受注管理メニュー | `/orders/menu` |  | | | − | |
| 68 | クボタ内示変化推移分析 | `/orders/kubota-naiji-analysis` |  | | | − | |
| 69 | 内示分析 | `/orders/naiji-analysis` |  | | | − | |
| 70 | ルーティング未設定の注文品 | `/orders/missing-routing-items` |  | | | − | |
| 71 | 受注お久しぶり製品通知設定 | `/orders/first-article-setting` | ○ | | |  | |
| 72 | 旧OPEN受注洗い出し | `/orders/open-order-audit` |  | | | − | |
| 73 | 手動注文入力 | `/orders/manual-entry` | ○ | | |  | |
| 74 | 受注一覧 | `/orders` |  | | | − | |
| 75 | CSV Upload | `/csv-upload` | ○ | | |  | |

### 出荷 (`shipping`、17画面)

| # | 画面 | パス | 書込 | 表示 | 数値一致 | 登録・更新 | 備考 |
|---|---|---|---|---|---|---|---|
| 76 | 出荷管理メニュー | `/shipping/menu` |  | | | − | |
| 77 | 出荷指示 | `/shipping/instruction` |  | | | − | |
| 78 | 出荷実績照会 | `/shipping/actual` |  | | | − | |
| 79 | 出荷実績登録 | `/shipping/actual-register` |  | | | − | |
| 80 | 出荷情報追跡 | `/shipping/actual-trace` |  | | | − | |
| 81 | 出荷進度照会 | `/shipping/progress` |  | | | − | |
| 82 | 出荷進度管理 | `/shipping/progress-edit` |  | | | − | |
| 83 | 受注展開 | `/shipping/order-expansion` |  | | | − | |
| 84 | 出荷指示書 | `/shipping/order-document` |  | | | − | |
| 85 | 富士商事出荷指示書 | `/shipping/fujishoji-document` |  | | | − | |
| 86 | 枚方集荷依頼書 | `/shipping/hirakata-pickup` |  | | | − | |
| 87 | クボタ堺納期調整 | `/shipping/kubota-sakai-due-adjustment` |  | | | − | |
| 88 | クボタ堺便計画 | `/shipping/kubota-sakai-trip-planning` |  | | | − | |
| 89 | 便確認（出荷担当） | `/shipping/trip-execution` |  | | | − | |
| 90 | 便確認（業務員） | `/shipping/trip-progress` |  | | | − | |
| 91 | 便進捗サマリー | `/shipping/trip-progress-summary` |  | | | − | |
| 92 | 納入地別出荷加算日数 | `/shipping/ship-to-lead-time` |  | | | − | |

### 購買(仕入) (`purchase`、19画面)

| # | 画面 | パス | 書込 | 表示 | 数値一致 | 登録・更新 | 備考 |
|---|---|---|---|---|---|---|---|
| 93 | 仕入れ管理メニュー | `/purchase/menu` |  | | | − | |
| 94 | 仕入れ計画 | `/purchase/plan-input` |  | | | − | |
| 95 | 仕入れ在庫/残量 | `/purchase/inventory` |  | | | − | |
| 96 | 仕入れ進度のみ | `/purchase/progress-only` |  | | | − | |
| 97 | 仕入れ先カレンダ | `/purchase/supplier-calendar` |  | | | − | |
| 98 | 仕入れ検収 | `/purchase/receiving` |  | | | − | |
| 99 | 仕入れ検収（スマホ） | `/purchase/receiving-mobile` |  | | | − | |
| 100 | スマホ検収 確認 | `/purchase/receiving-confirm` |  | | | − | |
| 101 | 納入予定 | `/purchase/delivery-schedule` |  | | | − | |
| 102 | 納入パターン設定 | `/purchase/supplier-order-pattern` |  | | | − | |
| 103 | 外作注文書・進度表比較 | `/purchase/outsource-progress-compare` |  | | | − | |
| 104 | 仕入れ実績入力 | `/purchase/actual-input` |  | | | − | |
| 105 | 納入実績照会 | `/purchase/actual-inquiry` |  | | | − | |
| 106 | 納入実績編集 | `/purchase/actual-edit` |  | | | − | |
| 107 | 外作・購入品注文書一覧 | `/purchase/order-proposals` |  | | | − | |
| 108 | 発注タスク一覧 | `/purchase/order-tasks` |  | | | − | |
| 109 | 外作・購入品注文書詳細 | `/purchase/order-proposals/:id` ※個別データ |  | | | − | |
| 110 | 自動納入リスト送信 | `/purchase/auto-delivery-list` |  | | | − | |
| 111 | 注文書自動送信設定 | `/purchase/auto-order-send` |  | | | − | |

### 外作 (`outsource`、15画面)

| # | 画面 | パス | 書込 | 表示 | 数値一致 | 登録・更新 | 備考 |
|---|---|---|---|---|---|---|---|
| 112 | FB外作管理 | `/outsource/menu` |  | | | − | |
| 113 | FB受注一覧 | `/outsource/orders` |  | | | − | |
| 114 | FB受注取込 | `/outsource/orders/import` | ○ | | |  | |
| 115 | 案件詳細 | `/outsource/orders/:id` ※個別データ |  | | | − | |
| 116 | 外作先展開Excel出力 | `/outsource/excel-export` | ○ | | |  | |
| 117 | 分割計画取込 | `/outsource/splits/import` | ○ | | |  | |
| 118 | 材料支給 | `/outsource/materials` |  | | | − | |
| 119 | 材料検収 | `/outsource/material-receiving` |  | | | − | |
| 120 | 材料在庫 | `/outsource/material-stock` |  | | | − | |
| 121 | 完成品在庫 | `/outsource/product-stock` |  | | | − | |
| 122 | 材料手配 | `/outsource/procurement` |  | | | − | |
| 123 | 納入・出荷管理 | `/outsource/delivery` |  | | | − | |
| 124 | FB外作進捗管理 | `/outsource/progress` |  | | | − | |
| 125 | FB外作マスタ | `/outsource/masters` | ○ | | |  | |
| 126 | FB外作お久しぶり製品通知設定 | `/outsource/first-article-setting` | ○ | | |  | |

## 3. 画面一覧 — 優先度 B

### 品質 (`quality`、13画面)

| # | 画面 | パス | 書込 | 表示 | 数値一致 | 登録・更新 | 備考 |
|---|---|---|---|---|---|---|---|
| 127 | 品質管理メニュー | `/quality` |  | | | − | |
| 128 | 設備点検表 | `/quality/equipment-inspection` |  | | | − | |
| 129 | 点検項目作成 | `/quality/equipment-inspection/master` |  | | | − | |
| 130 | 点検実施 | `/quality/equipment-inspection/operation` |  | | | − | |
| 131 | 月間確認 | `/quality/equipment-inspection/monthly-review` |  | | | − | |
| 132 | 工程一体チェックシート | `/quality/product-checksheet` |  | | | − | |
| 133 | 教育・テスト・認定 | `/quality/training-certification` |  | | | − | |
| 134 | 工程一体チェックシート テンプレート管理 | `/quality/product-checksheet/integrated/templates` |  | | | − | |
| 135 | 工程一体チェックシート チェック実施 | `/quality/product-checksheet/integrated/operation` |  | | | − | |
| 136 | 工程一体チェックシート リーダー・班長確認 | `/quality/product-checksheet/integrated/review` |  | | | − | |
| 137 | 工程一体チェックシート 推移確認 | `/quality/product-checksheet/integrated/weekly-monthly` |  | | | − | |
| 138 | 工程一体チェックシート 傾向確認・分析 | `/quality/product-checksheet/integrated/trend-analysis` |  | | | − | |
| 139 | 工程一体チェックシート 品質問題時ツール | `/quality/product-checksheet/integrated/problem-tools` |  | | | − | |

### マスタ (`masters`、22画面)

| # | 画面 | パス | 書込 | 表示 | 数値一致 | 登録・更新 | 備考 |
|---|---|---|---|---|---|---|---|
| 140 | マスタメンテ | `/masters` |  | | | − | |
| 141 | 製品マスタ | `/masters/product` |  | | | − | |
| 142 | 製品グループマスタ | `/masters/product-group` |  | | | − | |
| 143 | 品番変換マスタ | `/masters/product-code-mapping` |  | | | − | |
| 144 | 容器マスタ | `/masters/container-capacity` |  | | | − | |
| 145 | 設備マスタ | `/masters/equipment` |  | | | − | |
| 146 | 得意先マスタ | `/masters/customer` |  | | | − | |
| 147 | 仕入先マスタ | `/masters/supplier` |  | | | − | |
| 148 | 仕入れ先トラックマスタ | `/masters/supplier-truck` |  | | | − | |
| 149 | 工程マスタ | `/masters/process` |  | | | − | |
| 150 | ラインマスタ | `/masters/line` |  | | | − | |
| 151 | カレンダマスタ | `/masters/calendar` |  | | | − | |
| 152 | 勤務パターンマスタ | `/masters/work-pattern` |  | | | − | |
| 153 | 構成マスタ（BOM） | `/masters/bom` |  | | | − | |
| 154 | ティエラCSV変換 | `/masters/tiera-converter` |  | | | − | |
| 155 | ルーティングマスタ | `/masters/routing` |  | | | − | |
| 156 | 連絡先マスタ | `/masters/contact` |  | | | − | |
| 157 | クボタ堺便マスタ | `/masters/kubota-sakai-truck` |  | | | − | |
| 158 | 逆展開（Where Used） | `/masters/where-used` |  | | | − | |
| 159 | 携帯端末管理 | `/masters/mobile-device` |  | | | − | |
| 160 | 加工先一括変更 | `/masters/sourcing-bulk-change` |  | | | − | |
| 161 | 中断理由マスタ | `/masters/interruption-reason` |  | | | − | |

### 設定 (`settings`、28画面)

| # | 画面 | パス | 書込 | 表示 | 数値一致 | 登録・更新 | 備考 |
|---|---|---|---|---|---|---|---|
| 162 | 設定 | `/settings` |  | | | − | |
| 163 | プロフィール編集 | `/settings/profile` |  | | | − | |
| 164 | ユーザー管理 | `/settings/users` |  | | | − | |
| 165 | ユーザー権限編集 | `/settings/user-permissions` |  | | | − | |
| 166 | 権限テンプレート | `/settings/permission-templates` |  | | | − | |
| 167 | SMTP設定 | `/settings/smtp` |  | | | − | |
| 168 | 仕入計画ロック設定 | `/settings/purchase-plan-lock` |  | | | − | |
| 169 | 生産計画ロック設定 | `/settings/production-plan-lock` |  | | | − | |
| 170 | クボタ堺納期調整ロック設定 | `/settings/kubota-sakai-due-plan-lock` |  | | | − | |
| 171 | 出荷進度再計算日数設定 | `/settings/shipping-progress-horizon` |  | | | − | |
| 172 | 定時タスク設定 | `/settings/scheduled-tasks` |  | | | − | |
| 173 | 取り込み＋在庫進度計算 | `/settings/inventory-task-settings` |  | | | − | |
| 174 | タスク設定 | `/settings/task-settings` |  | | | − | |
| 175 | 承認設定 | `/settings/approval-routes` |  | | | − | |
| 176 | 注文書メール設定 | `/settings/material-order-email-config` |  | | | − | |
| 177 | 自動計画 | `/settings/auto-plan` |  | | | − | |
| 178 | 自動計画順序設定 | `/settings/auto-plan-sequence` |  | | | − | |
| 179 | まとめ生産設定 | `/settings/auto-plan-aggregate` |  | | | − | |
| 180 | 棚卸初期化 | `/settings/stocktake-init` |  | | | − | |
| 181 | 孤立ライン実績メンテナンス | `/settings/orphan-backlog-maintenance` |  | | | − | |
| 182 | 組織管理 | `/settings/departments` |  | | | − | |
| 183 | クボタ堺取り込み通知設定 | `/settings/kubota-import` | ○ | | |  | |
| 184 | クボタ堺便計画設定 | `/settings/kubota-sakai-config` |  | | | − | |
| 185 | 締め日管理 | `/settings/lock-date` |  | | | − | |
| 186 | 文字起こし設定 | `/settings/transcription` |  | | | − | |
| 187 | システム設定 | `/settings/system` |  | | | − | |
| 188 | AI設定 | `/settings/ai` |  | | | − | |
| 189 | Androidアプリ配布 | `/settings/android-app` |  | | | − | |

### 消耗品 (`consumables`、7画面)

| # | 画面 | パス | 書込 | 表示 | 数値一致 | 登録・更新 | 備考 |
|---|---|---|---|---|---|---|---|
| 190 | 消耗品メニュー | `/consumables` |  | | | − | |
| 191 | 消耗品 在庫一覧 | `/consumables/inventory` |  | | | − | |
| 192 | 消耗品 入出庫 | `/consumables/operations` |  | | | − | |
| 193 | 消耗品 発注準備 | `/consumables/requests` |  | | | − | |
| 194 | 消耗品 注文書 | `/consumables/dispatch-orders` |  | | | − | |
| 195 | 消耗品 入出庫履歴 | `/consumables/history` |  | | | − | |
| 196 | 消耗品マスタ | `/consumables/masters` |  | | | − | |

### 残業 (`overtime`、8画面)

| # | 画面 | パス | 書込 | 表示 | 数値一致 | 登録・更新 | 備考 |
|---|---|---|---|---|---|---|---|
| 197 | 勤務管理メニュー | `/overtime/menu` |  | | | − | |
| 198 | 残業申請 | `/overtime/apply` |  | | | − | |
| 199 | 残業申請 編集 | `/overtime/apply/:id` ※個別データ |  | | | − | |
| 200 | 自分の申請一覧 | `/overtime/my` |  | | | − | |
| 201 | 残業申請 一覧 | `/overtime/list` |  | | | − | |
| 202 | 承認待ち一覧 | `/overtime/approvals` |  | | | − | |
| 203 | 月次労働時間統計 | `/overtime/stats` |  | | | − | |
| 204 | 加工費集計 | `/overtime/productivity-stats` |  | | | − | |

### シフト (`shifts`、2画面)

| # | 画面 | パス | 書込 | 表示 | 数値一致 | 登録・更新 | 備考 |
|---|---|---|---|---|---|---|---|
| 205 | シフト管理 | `/shifts/chart` |  | | | − | |
| 206 | シフト確認 | `/shifts/my-line` |  | | | − | |

### 通知 (`notifications`、5画面)

| # | 画面 | パス | 書込 | 表示 | 数値一致 | 登録・更新 | 備考 |
|---|---|---|---|---|---|---|---|
| 207 | 通知一覧 | `/notifications` |  | | | − | |
| 208 | 通信 | `/notifications/communication` |  | | | − | |
| 209 | 通知編集 | `/notifications/sources` |  | | | − | |
| 210 | 社内通話 | `/notifications/calls` |  | | | − | |
| 211 | 通話録音一覧 | `/notifications/recordings` |  | | | − | |

### タスク (`tasks`、1画面)

| # | 画面 | パス | 書込 | 表示 | 数値一致 | 登録・更新 | 備考 |
|---|---|---|---|---|---|---|---|
| 212 | タスク受信箱 | `/tasks` |  | | | − | |

### 設変 (`engineeringChange`、4画面)

| # | 画面 | パス | 書込 | 表示 | 数値一致 | 登録・更新 | 備考 |
|---|---|---|---|---|---|---|---|
| 213 | 設変メニュー | `/engineering-change/menu` |  | | | − | |
| 214 | 設変 - 新規 | `/engineering-change/new` |  | | | − | |
| 215 | 設変タイル | `/engineering-change/change` |  | | | − | |
| 216 | 打ち切り管理 | `/engineering-change/discontinuation` |  | | | − | |

## 4. 画面一覧 — 優先度 C

### AI (`ai`、2画面)

| # | 画面 | パス | 書込 | 表示 | 数値一致 | 登録・更新 | 備考 |
|---|---|---|---|---|---|---|---|
| 217 | 社内AI（管理者） | `/ai/chat` | ○ | | |  | |
| 218 | AI分析 | `/ai/analysis` |  | | | − | |

### OCR (`ocr`、1画面)

| # | 画面 | パス | 書込 | 表示 | 数値一致 | 登録・更新 | 備考 |
|---|---|---|---|---|---|---|---|
| 219 | OCR・文書読取 | `/ocr` |  | | | − | |

### マニュアル (`manual`、1画面)

| # | 画面 | パス | 書込 | 表示 | 数値一致 | 登録・更新 | 備考 |
|---|---|---|---|---|---|---|---|
| 220 | マニュアル | `/manual` |  | | | − | |

## 5. 対象外(画面を持たない定義)

redirectのみの定義 6 件: `/overtime`、`/production/ai-data-analysis`、`/production/ai-search-config`、`/settings/supplier-order-pattern`、`/settings/supplier-order-schedule`、`/shifts`

## 6. 件数の整理

- 画面定義 220 件(redirectのみを除く)。優先度A: 126 件、B: 90 件、C: 4 件
- 書込のある画面: 31 件(`permission: edit`の定義)
- 実際の使用頻度・重要度は未確認。**BOSSが優先度を見直す**こと。

## 未決定・要確認

1. 確認を行う担当者と日程(BOSS・現場の担当者)
2. 優先度の見直し(特に、A以外で、切替当日に必ず使う画面)
3. 同一ダンプのPG DB(`pm_pg_ui`)の作成の承認(切替スクリプトで約8分、稼働中のMySQL・既存PG DBには書き込まない)
4. 権限(`resource`・`permission`)による表示の違いを、一般ユーザーでも確認するか(`admin`は全権限)
