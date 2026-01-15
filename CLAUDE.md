# PM - 生産管理システム (Production Management System)

## プロジェクト概要

製造業向けの包括的な生産管理システム。受注から出荷までの一連の業務フローをサポート。

## 技術スタック

### フロントエンド (`pm-ui/`)
- **フレームワーク**: Vue 3
- **ビルドツール**: Vite
- **ルーティング**: Vue Router
- **HTTP通信**: Axios
- **開発サーバー**: `http://localhost:8501`

### バックエンド (`pm_backend/`)
- **フレームワーク**: Django 5.2
- **データベース**: MySQL
- **API**: Django REST Framework
- **開発サーバー**: `http://localhost:8081`

## ディレクトリ構造

```
pm/
├── pm-ui/              # Vue.js フロントエンド
│   └── src/
│       ├── views/      # ページコンポーネント
│       ├── components/ # 共通コンポーネント
│       ├── api/        # API呼び出し
│       └── router/     # ルーティング定義
│
├── pm_backend/         # Django バックエンド
│   └── apps/
│       ├── accounts/   # ユーザー管理
│       ├── masters/    # マスターデータ
│       ├── orders/     # 受注・製造指示
│       ├── production/ # 生産計画
│       ├── purchase/   # 購買
│       ├── quality/    # 品質管理
│       └── shipping/   # 出荷
│
├── docs/               # ドキュメント
└── 仕様書/             # 仕様書
```

## 開発コマンド

```bash
# フロントエンド
cd pm-ui
npm run dev      # 開発サーバー起動 (port 8501)
npm run build    # 本番ビルド

# バックエンド
cd pm_backend
python manage.py runserver 8081  # 開発サーバー起動
python manage.py migrate         # マイグレーション実行
```

## コーディング規約

- **言語**: 日本語でコメント・コミットメッセージを記述
- **フロントエンド**: Vue 3 Composition API を使用
- **バックエンド**: Django の規約に従う
- **API**: RESTful な設計を維持

## 主要機能

- 受注管理
- 生産計画（ガントチャート表示）
- 製造指示・工程実績管理
- マスターデータ管理（製品、BOM、ルーティング、工程）
- 在庫管理・引当
- CRP（能力所要量計画）計算
- リードタイム自動計算

## Docker本番環境

### 構成
- **ネットワーク**: `pm_internal`（内部通信）+ `ts_pm_network_v2`（外部MySQL接続）
- **データベース**: 共通MySQLコンテナ（ホスト名: `mysql`）
- **フロントエンド**: nginx + Vue.js ビルド済みファイル（ポート 8501）
- **バックエンド**: gunicorn + Django（ポート 8081）
- **日本語フォント**: IPA Gothic, Takao Gothic（PDF生成用）
- **本番IP**: `10.0.1.232`
- **プロトコル**: HTTPS（PWA対応）
- **SSL証明書**: `pm-ui/certs/pm-prod.crt`

### Dockerコマンド

```bash
# 本番環境起動
docker-compose up -d --build

# ログ確認
docker-compose logs -f

# 停止
docker-compose down

# バックエンドのみ再起動
docker-compose restart pm-backend
```

### 環境変数設定
`.env.example` を `.env` にコピーして設定:
- `DB_HOST`: MySQLホスト名（デフォルト: mysql）
- `DB_PASSWORD`: MySQLパスワード
- `DB_NAME`: データベース名（デフォルト: pm_db）
- `SECRET_KEY`: Django秘密鍵
- `ALLOWED_HOSTS`: 許可するホスト
