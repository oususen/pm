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
├── pm-ui/                  # Vue.js フロントエンド
│   ├── public/
│   │   └── manual/         # ユーザーマニュアル（md）
│   │       ├── 生産/       # 生産系マニュアル
│   │       ├── 受注/       # 受注系マニュアル
│   │       ├── 出荷/       # 出荷系マニュアル
│   │       ├── マスタ/     # マスタ系マニュアル
│   │       ├── 設定/       # 設定系マニュアル
│   │       └── 共通/       # 共通操作マニュアル
│   └── src/
│       ├── views/          # ページコンポーネント
│       ├── components/     # 共通コンポーネント
│       ├── api/            # API呼び出し
│       ├── router/         # ルーティング定義
│       ├── utils/          # ユーティリティ
│       └── manual/         # マニュアル表示用コンポーネント
│
├── pm_backend/             # Django バックエンド
│   └── apps/
│       ├── accounts/       # ユーザー管理・権限
│       ├── masters/        # マスターデータ
│       ├── orders/         # 受注・製造指示
│       ├── production/     # 生産計画・ガント・在庫・進度
│       ├── purchase/       # 購買
│       ├── quality/        # 品質管理・仕損
│       ├── shipping/       # 出荷
│       ├── notifications/  # 通知
│       └── proposals/      # 提案
│
├── scripts/                # 運用スクリプト
├── 仕様書/                 # 仕様書
└── 予備資料/               # スキーマ定義等の参考資料
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
## チャート規約

- 私のことをBOSSって呼ぶ

## コーディング規約

- **言語**: 日本語でコメント・コミットメッセージを記述
- **依頼対応**: 依頼を受けたら、作業を始める前にまず理解した内容を回答して確認を取る
- **フロントエンド**: Vue 3 Composition API を使用
- **バックエンド**: Django の規約に従う
- **API**: RESTful な設計を維持


## デプロイとデータベース管理

### Git コミット時の注意事項

コミット作成時は、以下を確認すること：

1. **マイグレーションの確認**: モデル変更があった場合、`python manage.py makemigrations --dry-run` で新規マイグレーションの有無を確認
2. **本番データベースへの影響**: マイグレーションやデータ変更がある場合、本番環境で必要なSQL文の実行を明示
3. **デプロイ手順**: 本番環境へはGit PUSHでデプロイ。データベース変更が必要な場合はユーザーに通知すること

### 本番デプロイフロー

```bash
# 1. 開発環境でコミット
git add .
git commit -m "変更内容"

# 2. マイグレーション確認（必要に応じて）
cd pm_backend
python manage.py makemigrations
python manage.py migrate

# 3. 本番環境へPUSH
git push origin main

# 4. 本番環境でマイグレーション実行（必要な場合）
# Docker環境で実行
docker exec -it pm-backend python manage.py migrate
```

## ドキュメント保存ルール

- **仕様書**: `仕様書/` フォルダに保存
- **マニュアル**: `pm-ui/public/manual/` フォルダに保存

## 主要機能

- 受注管理
- 生産計画（ガントチャート表示）
- 製造指示・工程実績管理
- マスターデータ管理（製品、BOM、ルーティング、工程）
- 在庫管理・引当
- CRP（能力所要量計画）計算
- リードタイム自動計算

## 業務ルール

### 日替わり時刻（8時）

弊社では**日替わり時刻を8:00**としています。

- **1月19日 7:59** → **1月18日**として扱う
- **1月19日 8:00** → **1月19日**として扱う

コード内で「今日」を判定する際は、この8時区切りを考慮する必要があります。

### 進度計算の需要データソース

進度は「顧客需要に対して実績が遅れているか先行しているか」を表す指標。
**ラインの計画とは関係なく**、顧客の需要（計需/実需）に対する実績の状況を示す。

そのため、進度計算の需要（内示/確定）は必ず **LineDemand** を使用すること。
LineBacklog の `order_qty` や `demand_qty_plan` をフォールバックとして使ってはならない。

## Docker本番環境

### 構成
- **ネットワーク**: `pm_internal`（内部通信）+ `ts_pm_network_v2`（外部MySQL接続）
- **データベース**: 共通MySQLコンテナ（ホスト名: `mysql`）
- **フロントエンド**: nginx + Vue.js ビルド済みファイル（ポート 8501）
- **バックエンド**: gunicorn + Django + WhiteNoise（ポート 8081）
- **静的ファイル**: nginx が `/static/`, `/media/` を直接配信
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

### 本番データベース管理
- **管理ツール**: Adminer（開発PCからアクセス可能）
- **本番MySQL**: 開発PCから直接接続可能
