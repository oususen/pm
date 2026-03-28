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
- **仕様書更新**: コード変更後、ロジックやUI以外の仕様変更（データモデル、API仕様、業務ルール等）があった場合、`仕様書/` 内の関連仕様書も更新すること
- **推測禁止**: 数値・データの検証は必ずDBを直接確認してから行うこと。DBを確認せずに推測で数字を提示してはならない。確認できない場合は「DBを確認する必要があります」と明示し、確認用のSQLを提示すること


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

### 棚卸初期化と通常計算の分離

棚卸初期化のために、通常の在庫・計画在庫・進度の計算ファイルを変更してはならない。

- **通常計算**（日次再計算）: `inventory_calculator.py` / `progress_calculator.py` — 触らない
- **棚卸初期化専用**: `stocktake_initializer.py` — 棚卸時のみ使用するロジックはすべてここに書く

棚卸専用の在庫・計画在庫再計算は `stocktake_initializer.py` 内の専用関数で行い、`inventory_calculator.py` の関数を棚卸用に改変・流用しないこと。

### 不整合調査の基本手順（重要）

画面表示・計算・自動計画などで数値不整合が出た場合、いきなりロジック変更しない。必ず以下の順で切り分けること。

1. **DB実データ確認（一次情報）**
   - まず対象日・対象製品のDB実データを確認し、どのテーブルが正かを確定する。
   - 代表: `LineBacklog` / `LineDemand` / `LinePlan`（必要に応じて他テーブルも確認）
2. **画面専用変換ロジック確認**
   - APIレスポンス整形、画面用補正、集計ロジックなどを確認する。
   - 特に営業日判定（日替わり/土日/カレンダ未登録日の扱い）や条件分岐差分を確認する。
3. **生成ロジック修正は最後**
   - 1,2で原因が生成側と確定するまで、需要生成・計画生成・再計算ロジックは変更しない。

補足:
- 社内ラインでは、`sequence_no=0` の行を需要専用行として扱う。この行の `plan_qty` の数量値は必ず `0` とし、計画数を入れてはならない。`sequence_no>0` の行は計画値専用行として扱い、実績値を入れてはならない。`仕様書/LineBacklog_sequence_no仕様.md` の `LineBacklog_sequence_no` 仕様を必ず守ること。

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
