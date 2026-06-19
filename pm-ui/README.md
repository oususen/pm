# Vue 3 + Vite

This template should help get you started developing with Vue 3 in Vite. The template uses Vue 3 `<script setup>` SFCs, check out the [script setup docs](https://v3.vuejs.org/api/sfc-script-setup.html#sfc-script-setup) to learn more.

Learn more about IDE Support for Vue in the [Vue Docs Scaling up Guide](https://vuejs.org/guide/scaling-up/tooling.html#ide-support).

## PWA and HTTPS

- PWA assets live in `public/manifest.webmanifest` and `public/sw.js`.
- `npm run dev` is configured to use HTTPS by default in development.
- HTTPS is controlled by env vars:
  - `VITE_HTTPS=false` to force HTTP on `vite dev`.
  - `VITE_HTTPS=true` to enable HTTPS on `vite dev`/`vite preview`.
  - `VITE_HTTPS_KEY` and `VITE_HTTPS_CERT` to provide a trusted TLS cert.
  - `VITE_TURN_URL`, `VITE_TURN_USERNAME`, `VITE_TURN_CREDENTIAL` to enable TURN for WebRTC calls.
- Trusted cert generation:
  - `powershell -ExecutionPolicy Bypass -File .\scripts\generate-dev-certs.ps1`
  - This writes `pm-ui/.env.local` with the HTTPS settings for the generated cert files.

## Android APK 配布

- `設定 > Androidアプリ配布` 画面で社内向け APK の配布導線を提供する。
- APK のURLは以下で切り替える。
  - `VITE_ANDROID_APP_DOWNLOAD_URL`
  - `VITE_ANDROID_APP_RELEASE_LABEL`
- 未設定時は `public/downloads/app-debug.apk` を参照する。

## Capacitor / Android

- Android ラッパーは `capacitor.config.ts` と `android/` に生成済み。
- アプリIDは `com.daiso.pm`。
- ネイティブ Push は `@capacitor/push-notifications` を利用する。
- APK ビルドには JDK と Android SDK が必要。
- この環境での確認結果:
  - `npm run android:prepare` は成功
  - `.\gradlew.bat assembleDebug` は `JAVA_HOME` 未設定で停止
- 主要コマンド:
  - `npm run android:prepare` : Web ビルド後に Android プロジェクトへ同期
  - `npm run android:prepare:devpc` : 開発PC `https://10.0.1.194:8501` を直接表示する APK 用
  - `npm run android:prepare:prod` : 本番 `https://10.0.1.232:8501` を直接表示する APK 用
  - `npm run android:prepare:bundle` : `dist` を内包する APK 用
  - `npm run android:open` : Android Studio で開く
  - `npm run cap:sync` : 既存 `dist` を Android 側へ再同期
- Debug APK の例:
  - `cd android`
  - `.\gradlew.bat assembleDebug`
- 生成先の例:
  - `android/app/build/outputs/apk/debug/app-debug.apk`
- `CAPACITOR_SERVER_URL` を指定した場合、APK はそのURLのWebアプリを直接開く。

## FCM 着信通知

- Android 待機時の着信通知は Web Push ではなく FCM を使う。
- フロント側前提:
  - `pm-ui/android/app/google-services.json` を配置する
  - `npm install` 後に `npm run cap:sync` または `npm run android:prepare:*` を実行する
- バックエンド側前提:
  - `FCM_PROJECT_ID`
  - `FCM_SERVICE_ACCOUNT_FILE`
  - または `FCM_SERVICE_ACCOUNT_JSON`
- サービスアカウント JSON は Git 管理に入れない。
