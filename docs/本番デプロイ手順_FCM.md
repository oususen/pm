# Android FCM Push通知 本番デプロイ手順

## 手順

### 1. git pull

```bash
git pull origin main
```

### 2. 環境変数追加

`pm_backend/.env` に以下を追加：

```
FCM_SERVICE_ACCOUNT_JSON=（Firebaseサービスアカウントキーの中身を1行で貼る）
```

### 3. Docker再ビルド・起動

```bash
docker-compose up -d --build
```

※ google-authパッケージ追加のため再ビルド必要

### 4. マイグレーション実行

```bash
docker exec -it pm-backend python manage.py migrate
```

※ マイグレーション `0008_nativepushtoken` が `native_push_tokens` テーブルを作成する

### 5. 確認

```bash
docker exec -it pm-backend python -c "import google.auth; print('OK')"
```

## 注意事項

- `FCM_SERVICE_ACCOUNT_JSON` の値はFirebaseのサービスアカウントキーJSONの中身を**1行で**貼る
- `google-services.json` は本番サーバーには不要（APKに含まれている）
