# 生産管理システム PM

段階BOM・セル工程・時間運用・ライン/購買LT対応の生産管理システム

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
│   ├── pm_backend/            # プロジェクト設定
│   │   ├── settings.py        # DB設定、CORS設定
│   │   └── urls.py            # APIルーティング
│   └── masters/               # マスタ管理アプリ
│       ├── models.py          # Djangoモデル
│       ├── serializers.py     # RESTシリアライザ
│       ├── views.py           # ViewSet
│       ├── admin.py           # Django Admin設定
│       └── urls.py            # APIエンドポイント
│
├── pm-ui/                      # Vue.js フロントエンド
│   ├── src/
│   │   ├── App.vue            # メインアプリ
│   │   ├── main.js
│   │   ├── router/index.js    # ルーティング
│   │   ├── api/client.js      # APIクライアント
│   │   ├── components/        # コンポーネント
│   │   │   └── SideMenu.vue
│   │   ├── pages/             # ページ
│   │   │   ├── MasterMenu.vue
│   │   │   ├── ProductMaster.vue
│   │   │   └── CustomerMaster.vue
│   │   └── assets/main.css    # スタイル
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

# 開発サーバー起動
python manage.py runserver
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

バックエンドが http://localhost:8000 で起動します。

### 3. Vue.js フロントエンドセットアップ

```bash
# 別のターミナルで
cd pm-ui

# 開発サーバー起動
npm run dev
```

フロントエンドが http://localhost:5173 で起動します。

## APIエンドポイント

バックエンドは以下のRESTful APIを提供：

- `/api/products/` - 製品マスタ
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

## 次のステップ

1. 残りのページコンポーネント実装
   - CalendarMaster.vue
   - BomMaster.vue
   - RoutingMaster.vue

2. スケジューリングロジック実装
   - 逆算ロジック (scheduling_logic_v3.md参照)
   - 日跨ぎ計算
   - 移送バッチ・バッファ制御

3. 受注管理機能
   - 受注入力
   - 納期回答

4. 生産計画機能
   - ガントチャート表示
   - 負荷グラフ
