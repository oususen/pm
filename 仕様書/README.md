# 生産管理システム PM

段階BOM・セル工程・時間運用・ライン/購買LT対応の生産管理システム

## 仕様書一覧

- [7アプリ構成仕様書](7アプリ構成仕様書.md)

## プロジェクト構成

```
d:\pm\
├── schema.sql                  # 統合版SQLスキーマ (v3)
├── setup_database.sql          # データベースセットアップSQL
├── setup_database.bat          # データベースセットアップバッチ
├── ER_diagram_v3.md           # ER図
├── MASTER_TABLES_DEFINITION_v3.MD  # マスタテーブル定義
├── scheduling_logic_v3.md      # スケジューリングロジック
├── 弊社生産特徴まとめ.md      # 生産構造理解要約
│
├── pm_backend/                 # Djangoバックエンド
│   ├── manage.py
│   ├── project/               # プロジェクト設定
│   │   ├── settings.py        # DB設定、CORS設定
│   │   └── urls.py            # APIルーティング
│   └── apps/
│       ├── masters/           # マスタ管理アプリ
│       │   ├── models.py      # Djangoモデル
│       │   ├── serializers.py # RESTシリアライザ
│       │   ├── views.py       # ViewSet
│       │   ├── admin.py       # Django Admin設定
│       │   └── urls.py        # APIエンドポイント
│       ├── orders/            # 受注管理アプリ
│       │   ├── models.py      # Order, OrderLine, StgOrderRaw, StgOrderDaily
│       │   ├── serializers.py # RESTシリアライザ
│       │   ├── views.py       # ViewSet + CSV upload/create_orders
│       │   ├── admin.py       # Django Admin設定
│       │   ├── urls.py        # APIエンドポイント
│       │   └── core/services/ # CSV Import Services
│       │       ├── README.md  # インポートサービス仕様書
│       │       ├── base_import.py # 基本クラス
│       │       ├── csv_import.py  # デフォルトサービス
│       │       ├── tiera_naiji_import.py    # ティエラ内示
│       │       ├── tiera_kakutei_import.py  # ティエラ確定
│       │       ├── kubota_sakai_naiji_import.py
│       │       ├── kubota_sakai_kakutei_import.py
│       │       ├── kubota_hirakata_kakutei_import.py
│       │       └── rieden_kakutei_import.py
│       ├── production/        # 生産管理アプリ
│       │   └── inventory/     # 在庫計算ロジック
│       ├── shipping/          # 出荷管理アプリ
│       ├── purchase/          # 仕入れ管理アプリ
│       └── quality/           # 品質管理アプリ
│
├── pm-ui/                      # Vue.js フロントエンド (Vite)
│   ├── src/
│   │   ├── App.vue            # メインアプリ
│   │   ├── main.js
│   │   ├── api/client.js      # APIクライアント (API_BASE_URL をバックエンドに合わせて変更)
│   │   ├── router/
│   │   │   ├── index.js       # ルーター統合
│   │   │   ├── masters.js
│   │   │   ├── orders.js
│   │   │   ├── production.js
│   │   │   ├── purchase.js
│   │   │   └── shipping.js
│   │   ├── views/             # 画面コンポーネント
│   │   │   ├── masters/*.vue  # マスタ類
│   │   │   ├── orders/*.vue   # 受注メニュー・一覧・CSV取込
│   │   │   ├── production/*.vue # 生産メニュー・計画・在庫・進捗など
│   │   │   ├── purchase/*.vue   # 仕入れメニュー・計画
│   │   │   └── shipping/*.vue   # 出荷メニュー・指示・実績
│   │   ├── components/SideMenu.vue
│   │   └── assets/main.css
│   ├── package.json
│   └── vite.config.js
│
└── venv/                       # Python仮想環境

```

## セットアップ手順

### 1. データベースセットアップ (MySQL)

以下のいずれかの方法でセットアップします：

#### 方法1: PowerShellスクリプト（推奨）

```powershell
# PowerShellで実行
.\setup_database.ps1
```

#### 方法2: バッチファイル（英語版）

```cmd
# コマンドプロンプトで実行
setup_db.bat
```

#### 方法3: 直接SQLファイル実行

```bash
# PowerShellまたはコマンドプロンプトで
mysql -u root -p --default-character-set=utf8mb4 < setup_database.sql
```

#### 方法4: MySQL内で手動実行

```bash
# MySQLに直接接続
mysql -u root -p --default-character-set=utf8mb4

# MySQL内で実行
CREATE DATABASE IF NOT EXISTS pm_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE pm_db;
SOURCE schema.sql;
SHOW TABLES;
exit;
```

MySQLのrootパスワードを入力すると、`pm_db`データベースが作成され、schema.sqlが実行されます。

### 2. Djangoバックエンドセットアップ

```bash
# 仮想環境を有効化
venv\Scripts\activate

# .envファイルを設定
cd pm_backend
copy .env.example .env
# .envファイルを開いてDB_PASSWORDにMySQLのrootパスワードを設定

# マイグレーション実行（既存テーブルと同期）
python manage.py migrate

# 管理ユーザー作成
python manage.py createsuperuser

# 開発サーバー起動（必要なら ALLOWED_HOSTS にクライアントIPを追加）
python manage.py runserver 0.0.0.0:8081
```

#### .envファイルの設定例

`pm_backend/.env` ファイルを編集：

```env
# Django Settings
SECRET_KEY=django-insecure-_4wufh_x8tvr3%_0d%!r4b_&uvlgf!nhvl--&(8+%hncxf(9tj
DEBUG=True

# MySQL Database Settings
DB_NAME=pm_db
DB_USER=root
DB_PASSWORD=your_mysql_password_here  # ← ここにMySQLのパスワードを入力
DB_HOST=localhost
DB_PORT=3306
```

バックエンドが http://localhost:8081 で起動します。

### 3. Vue.js フロントエンドセットアップ

```bash
# 別のターミナルで
cd pm-ui
# 依存インストール
npm install

# 開発サーバー起動（デフォルト: http://localhost:8501）
npm run dev
```

API の接続先は `src/api/client.js` の `API_BASE_URL` をバックエンドの URL/ポートに合わせて調整してください（デフォルトは `http://localhost:8081/api`）。

### 開発ポート例
- バックエンド: http://localhost:8081
- フロントエンド (Vite dev): http://localhost:8501

## APIエンドポイント

バックエンドは以下のRESTful APIを提供：

### マスタ管理

- `/api/products/` - 製品マスタ（品名・品名半角対応）
- `/api/customers/` - 得意先マスタ
- `/api/processes/` - 工程マスタ
- `/api/lines/` - ラインマスタ
- `/api/suppliers/` - 仕入先マスタ
- `/api/calendars/` - カレンダマスタ
- `/api/calendar-days/` - カレンダ日マスタ
- `/api/boms/` - BOMヘッダ
- `/api/bom-items/` - BOM明細
- `/api/routings/` - ルーティングヘッダ
- `/api/routing-steps/` - ルーティング工程

### 受注管理

- `/api/orders/` - 受注ヘッダ
- `/api/order-lines/` - 受注明細
- `/api/stg-order-raw/` - 受注取込ステージング（生データ）
  - `POST /api/stg-order-raw/upload_csv/` - CSVアップロード
  - `POST /api/stg-order-raw/create_orders/` - ステージングから受注作成
- `/api/stg-order-daily/` - 受注取込ステージング（日別）

Django Admin: http://localhost:8000/admin/

## 技術スタック

### バックエンド
- Python 3.13
- Django 5.2
- Django REST Framework 3.16
- MySQL 8.0
- mysqlclient 2.2.7
- django-cors-headers 4.9

### フロントエンド
- Vue.js 3.5
- Vue Router 4.6
- Vite 7.2
- Axios

## データベーススキーマ v3の特徴

1. **製品カテゴリENUM化**: `m_product.category`
2. **時間単位の明示化**: `m_routing_step.time_unit` (DAY/MINUTE)
3. **得意先マスタ追加**: `m_customer`
4. **スケジューリング結果テーブル**: `t_schedule_detail`
5. **調達整合性CHECK制約**: `m_bom_item`

## 開発ツール

- Django Admin でマスタデータを管理
- API Browser (http://localhost:8000/api/) でAPIをテスト
- Vue DevTools でフロントエンドをデバッグ

## 実装済み機能

### 受注管理機能

- CSV受注インポート（複数客先フォーマット対応）
  - ティエラ内示・確定
  - クボタ（堺・枚方）内示・確定
  - リーデン確定
- ステージングテーブル（生データ→日別正規化）
- 製品マスタ自動登録（品名・品名半角対応）
- 受注一覧・明細表示
- 多言語対応UI（日本語）
- **内示・確定の優先順位制御**
  - 内示の自動上書き（新しい内示で古い内示を削除）
  - 確定受注による内示の自動無効化
  - スケジューリング用の優先度ロジック
  - 詳細は `仕様書/受注管理仕様書.md` 参照
- **数量集約機能**
  - 同一製品・納期の複数注文明細（10行以上）を集約
  - 個別注文情報を保持しながらスケジューリング用に合計数量を提供
  - 使用例は `pm_backend/apps/production/services/scheduling_example.py` 参照

### CSV Import Service アーキテクチャ

- 客先・受注タイプ・ファイル名による自動サービス選択
- 複数エンコーディング対応（CP932, Shift-JIS, UTF-8）
- カラム位置指定による柔軟なフォーマット対応
- 詳細は `仕様書/受注管理仕様書.md` を参照

### 在庫管理機能

- **在庫計算エンジン** (`pm_backend/apps/production/inventory/inventory_calculator.py`)
  - 仕損数の自動集計（自工程＋後工程展開分）
  - 実績出庫数の自動計算（後工程実績からBOM展開）
  - 実在庫の日次計算
  - 計画在庫の時制考慮計算
    - 過去（実績あり）: 実績生産＋実績出庫ベース
    - 過去（実績なし）: 生産ゼロ＋計画出庫ベース
    - 未来: 計画生産＋計画出庫ベース

- **在庫データモデル** (`LineBacklog`)
  - `adjust_qty`: 調整数（手動調整、棚卸差異）
  - `scrap_qty`: 仕損数（自動集計）
  - `actual_shipment_qty`: 実績出庫数（自動計算）
  - `stock_qty`: 実在庫
  - `planned_stock_qty`: 計画在庫

- **仕損管理** (`ScrapRecord`)
  - `plan_date`: 生産計画日との紐付け
  - 後工程仕損のBOM展開（`ScrapRecordDetail`）
  - 仕損確定ステータス管理

- **在庫一覧画面** (`ProductionInventory.vue`)
  - 日別在庫推移の表示
  - マイナス在庫の赤字強調表示
  - 在庫再計算機能
  - 0値の空白表示

## 次のステップ

1. 未実装画面の追加
   - RoutingMaster.vue（生産マスタ系）
2. スケジューリングロジック実装
   - 逆算ロジック (scheduling_logic_v3.md参照)
   - 日跨ぎ計算
   - 移送バッチ・バッファ制御
3. 受注管理機能拡張
   - 納期回答
   - 受注変更履歴
4. 生産計画機能
   - ガントチャート表示
   - 負荷グラフ
