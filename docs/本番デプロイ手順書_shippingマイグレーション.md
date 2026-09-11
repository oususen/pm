# 本番デプロイ手順書（全アプリ migration チェック対応）

## 目的
- 本番環境へ安全に反映する。
- migration 不整合と既存テーブル衝突を事前に検知する。

## 前提
- 開発側で `main` に必要なコミットが揃っていること。
- 本番は Docker Compose 構成（`web`/`db` サービス名は環境に合わせて読み替え）。
- 本番作業前に DB バックアップを取得すること。

## 1. 開発側（push 前）
プロジェクトルートで確認:
```bash
git status --short
```

バックエンドで migration 整合チェック:
```bash
cd pm_backend
python manage.py makemigrations --check
python manage.py showmigrations
python manage.py migrate --plan
```

判定:
- `makemigrations --check` が 0 終了（新規 migration 必要なし）。
- `migrate --plan` が想定外の操作を出さないこと。

問題なければ push:
```bash
git push origin main
```

## 2. 本番側（pull 後、反映前チェック）
```bash
git pull origin main
docker compose up -d --build
```

全アプリ migration 状態を確認:
```bash
docker compose exec web python manage.py showmigrations
docker compose exec web python manage.py migrate --plan
```

## 3. DB実体チェック（初回系テーブル衝突回避）
代表例（shipping）:
```bash
docker compose exec db mysql -u root -p -D pm_db -e "SHOW TABLES LIKE 't_shipment_actual'; SHOW TABLES LIKE 't_shipment_actual_history'; SHOW TABLES LIKE 't_delivery_progress'; SHOW TABLES LIKE 'm_ship_to_lead_time';"
```

必要に応じて、今回変更したアプリのテーブルも同様に確認する。

## 4. migration 実行ルール
- 既存テーブルが存在する可能性がある本番では、初回は `--fake-initial` を優先する。
- 完全新規DBで、対象テーブルが確実に未作成の場合のみ通常 migrate を使う。

推奨（本番）:
```bash
docker compose exec web python manage.py migrate --fake-initial
```

新規DB限定:
```bash
docker compose exec web python manage.py migrate
```

## 5. 適用後チェック
```bash
docker compose exec web python manage.py showmigrations
docker compose exec web python manage.py migrate --plan
```

完了条件:
- `showmigrations` で対象 migration が `[X]`。
- `migrate --plan` が `No planned migration operations.`。

## 6. トラブル時の基本方針
- まずエラーログ全文を保存する。
- `showmigrations` と `SHOW TABLES` を再確認し、DB実体と migration 履歴の不一致を特定する。
- その場しのぎの暫定 migration（重複 CREATE/DROP を含むもの）を本線に残さない。

## 7. 今回の shipping 追加チェック（任意）
```bash
docker compose exec web python manage.py showmigrations shipping
docker compose exec db mysql -u root -p -D pm_db -e "SHOW TABLES LIKE 'm_ship_to_lead_time';"
```
