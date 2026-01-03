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

## 本番PC（Docker）での想定
- 社内CAで正規証明書を発行（固定ドメイン推奨）  
- HTTPS終端はリバースプロキシ（Nginx/Caddy/Traefik）  
- `pm-ui` / `pm-backend` はHTTPで運用し、リバプロで振り分け
