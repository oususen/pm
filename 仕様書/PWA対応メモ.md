# PWA対応メモ（開発PC向け）

## 目的
Android Chromeで「アプリをインストール」を表示し、アドレスバー無しで起動できるようにする。

## 追加/変更した内容
- `pm-ui/public/manifest.webmanifest`
- `pm-ui/public/sw.js`
- `pm-ui/src/registerServiceWorker.js`（本番ビルド時のみSW登録）
- `pm-ui/src/main.js`（SW登録を追加）
- `pm-ui/index.html`（manifest/link/meta追加）
- `pm-ui/public/icons/icon-192.png`, `pm-ui/public/icons/icon-512.png`
- `pm-ui/vite.config.js`（HTTPS対応）
- `pm-ui/.env`（`VITE_HTTPS=true`）
- `pm-ui/scripts/generate-dev-certs.ps1`（IP自動反映の証明書生成）

## 開発PCでのHTTPS/PWA手順
1) 証明書を生成  
   - `pm-ui/scripts/generate-dev-certs.ps1` を実行  
   - `pm-ui/certs/pm-ui-ca.crt`（CA）  
   - `pm-ui/certs/pm-ui.crt` / `pm-ui/certs/pm-ui.key`（サーバ用）  
   - `.env.local` に `VITE_HTTPS_KEY` / `VITE_HTTPS_CERT` を自動設定

2) ビルドとプレビュー  
   - `npm run build`  
   - `npm run preview`

3) Androidでアクセス  
   - `https://<開発PCのIP>:8501/` にアクセス  
   - メニューに「アプリをインストール」が出るか確認

## Android側の注意点
- 端末に画面ロックが無いと「CA証明書のインストール」メニューが出ない場合がある。  
- 自己署名のHTTPSは、CAを端末に入れないと「保護されていない接続」扱いになる。  
  → この場合、PWAの「インストール」が出ない。

## IP変更時の対応
- IPが変わると証明書SANが一致しないため再発行が必要。  
- `pm-ui/scripts/generate-dev-certs.ps1` を再実行して証明書を作り直す。

## 本番PC（Docker）での設定（実装済み）

### アクセスURL
`https://10.0.1.232:8501`

### 構成
- **nginx**: HTTPS終端（ポート8501）
- **SSL証明書**: 自己署名証明書（`pm-ui/certs/pm-prod.*`）
- **バックエンド**: HTTPのまま（nginx経由でプロキシ）

### 証明書ファイル
| ファイル | 用途 |
|---------|------|
| `pm-ui/certs/pm-prod.crt` | サーバー証明書 |
| `pm-ui/certs/pm-prod.key` | サーバー秘密鍵 |
| `pm-ui/certs/pm-ca.crt` | CA証明書（ブラウザ/端末にインポート） |

### ブラウザ警告回避
`pm-ca.crt` を「信頼されたルート証明機関」としてインポートする。

**Windowsの場合**:
1. `pm-ca.crt` をダブルクリック
2. 「証明書のインストール」→「ローカルコンピューター」
3. 「証明書をすべて次のストアに配置する」→「信頼されたルート証明機関」

**Androidの場合**:
1. `pm-ca.crt` を端末に転送
2. 設定 → セキュリティ → 証明書のインストール → CA証明書

### IP変更時の対応
```bash
cd pm-ui/certs
# pm-prod.ext を編集してIPを追加
vim pm-prod.ext
# 証明書を再生成
bash generate-prod-cert.sh
# Dockerを再起動
docker-compose restart pm-frontend
```

### Django設定
`settings.py` の以下に本番URLを追加済み:
- `CORS_ALLOWED_ORIGINS`: `https://10.0.1.232:8501`
- `CSRF_TRUSTED_ORIGINS`: `https://10.0.1.232:8501`
