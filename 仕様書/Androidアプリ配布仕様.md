# Androidアプリ配布仕様

## 概要

社内向け Android アプリの APK 配布窓口を、既存の Web アプリ内に設ける。  
対象画面は `設定 > Androidアプリ配布`（`/settings/android-app`）。

PWA のままでは端末待機中の着信通知・着信音にブラウザ制約が残るため、`Capacitor` などでラップした Android アプリ配布へ進める際の導線として利用する。

## 対象ファイル

- フロント画面: `pm-ui/src/views/settings/AndroidAppDownload.vue`
- ルート: `pm-ui/src/router/settings.js`
- 設定メニュー: `pm-ui/src/views/settings/SettingsMenu.vue`
- Capacitor設定: `pm-ui/capacitor.config.ts`
- Androidプロジェクト: `pm-ui/android/`

## 画面仕様

- 配布対象は Android のみ
- 画面上に以下を表示する
  - APK ダウンロードボタン
  - 配布URLコピー
  - 配布版ラベル
  - インストール手順
  - 運用メモ
  - スマホ向け QR コード

## 配布URLの決定ルール

1. `VITE_ANDROID_APP_DOWNLOAD_URL` が設定されていればその値を使用
2. 未設定の場合は `/downloads/pm-android-latest.apk` を使用

配布版ラベルは `VITE_ANDROID_APP_RELEASE_LABEL` を優先し、未設定時は `latest` と表示する。

## APK配置方法

### 既定パスを使う場合

`pm-ui/public/downloads/pm-android-latest.apk` を配置する。  
ビルド後は `/downloads/pm-android-latest.apk` で配信される。

### 別URLを使う場合

フロントエンド環境変数に以下を設定する。

```env
VITE_ANDROID_APP_DOWNLOAD_URL=https://example.local/downloads/pm-android-v1.0.0.apk
VITE_ANDROID_APP_RELEASE_LABEL=v1.0.0
```

## 権限

- 画面ルートの `meta.resource` は `settings`
- 設定メニューのタイル表示も `settings` 権限で判定する
- 既存の権限体系を増やさず、設定タブ閲覧可能ユーザーを配布対象とする

## 補足

- この画面は APK 自体を生成しない
- `Capacitor` は導入済みで、`android/` プロジェクトを生成済み
- 署名付き本番APKの作成は Android Studio または Gradle で行う
- 待機時着信音の改善には FCM を使用する

## Capacitor構成

- `appId`: `com.daiso.pm`
- `appName`: `DAISO管理システム`
- `webDir`: `dist`
- `CAPACITOR_SERVER_URL` が設定されている場合はそのURLのWebアプリを直接開く
- `CAPACITOR_CLEAR_TEXT=true` の場合のみ `http://` 接続を許可する
- `PushNotifications` の `presentationOptions` は `sound / alert / banner / list`

## APK作成手順

### 前提

- JDK をインストールし、`JAVA_HOME` を設定する
- Android Studio と Android SDK を導入する
- 初回は Android Studio 側で SDK Platform / Build Tools の不足分を補完する

### 1. Web資産を Android へ反映

```bash
cd pm-ui
npm run android:prepare
```

用途別コマンド:

```bash
npm run android:prepare:devpc
npm run android:prepare:prod
npm run android:prepare:bundle
```

- `devpc`: 開発PC `http://10.0.1.194:8501` を表示する検証用APK
- `prod`: 本番 `https://10.0.1.232:8501` を表示する運用向けAPK
- `bundle`: `dist` を内包する単体APK

### 1.5. FCM ファイル配置

- `pm-ui/android/app/google-services.json` に Firebase プロジェクトの Android 用設定ファイルを配置する
- このファイルが無い場合でも APK は作成できることがあるが、ネイティブ Push 登録は動かない

### 1.6. バックエンド環境変数

```env
FCM_PROJECT_ID=your-firebase-project-id
FCM_SERVICE_ACCOUNT_FILE=/absolute/path/firebase-service-account.json
```

または:

```env
FCM_PROJECT_ID=your-firebase-project-id
FCM_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
```

- `FCM_SERVICE_ACCOUNT_FILE` と `FCM_SERVICE_ACCOUNT_JSON` はどちらか片方でよい
- サービスアカウント JSON は Git に含めない

### 2. Android Studio で開く

```bash
cd pm-ui
npm run android:open
```

### 3. Debug APK を作る場合

```bash
cd pm-ui/android
.\gradlew.bat assembleDebug
```

生成先:

- `pm-ui/android/app/build/outputs/apk/debug/app-debug.apk`

### 4. 社内配布ページへ反映

次のどちらかで配布する。

1. `app-debug.apk` または署名済み APK を `pm-ui/public/downloads/pm-android-latest.apk` に配置する
2. 別サーバに置いた APK の URL を `VITE_ANDROID_APP_DOWNLOAD_URL` に設定する

## 注意点

- 端末に配布する本番版は、Debug APK ではなく署名付き Release APK を推奨する
- Push 通知のネイティブ強化は、今後 `Firebase Cloud Messaging` 連携を追加して実施する
- Firebase の具体的な設定手順は `仕様書/Firebase_FCM設定手順.md` を参照する
- `appId` を後から変更すると Android パッケージ名と再配布手順に影響する
- 現在の開発環境確認では `android:prepare` は成功し、`assembleDebug` は `JAVA_HOME` 未設定で停止した
- 開発PC向けAPKをそのまま本番配布してはならない。`android:prepare:prod` で作り直してから配布する
- 着信通知は Android の省電力制御やメーカー独自制御の影響を受けるため、FCM 化しても電話アプリ並みの確実性までは保証できない
