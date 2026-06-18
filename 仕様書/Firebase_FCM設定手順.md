# Firebase FCM設定手順

## 目的

Android の `Capacitor` アプリで、待機時の社内通話着信通知をネイティブ Push で受けるために Firebase Cloud Messaging を設定する。

対象日は 2026年6月18日 時点の実装に対応する。

## 今回の実装で前提になっているもの

- Android アプリID: `com.daiso.pm`
- Android 設定ファイル配置先: `pm-ui/android/app/google-services.json`
- Django 環境変数:
  - `FCM_PROJECT_ID`
  - `FCM_SERVICE_ACCOUNT_FILE`
  - または `FCM_SERVICE_ACCOUNT_JSON`

## 先に結論

開発PCで必要なのは次の2つだけ。

1. Firebase から `google-services.json` を取得して `pm-ui/android/app/google-services.json` に置く
2. Firebase のサービスアカウント JSON を取得して `pm_backend/firebase-service-account.json` に置き、`.env` に `FCM_PROJECT_ID` と `FCM_SERVICE_ACCOUNT_FILE` を設定する

## 1. Firebase プロジェクト作成

Firebase コンソールを開く。  
URL: https://console.firebase.google.com/

1. `プロジェクトを追加`
2. 任意のプロジェクト名を入力
3. Google Analytics はひとまず `無効` でよい
4. プロジェクト作成完了まで待つ

## 2. Android アプリを Firebase に登録

Firebase プロジェクト画面で Android アプリを追加する。

入力する値:

- Android package name: `com.daiso.pm`
- App nickname: `DAISO管理システム 開発`
- Debug signing certificate SHA-1:
  - とりあえず空でも登録は可能
  - 後で必要なら追加する

登録後、`google-services.json` をダウンロードする。

保存先:

`pm-ui/android/app/google-services.json`

注意:

- このファイルは Git に入れない
- 既に `.gitignore` で除外済み

## 3. サービスアカウント JSON を取得

Firebase コンソールから歯車 `プロジェクトの設定` を開く。

1. `サービス アカウント` タブを開く
2. `Firebase Admin SDK`
3. `新しい秘密鍵を生成`
4. JSON をダウンロード

配置先例:

`pm_backend/firebase-service-account.json`

このファイルも Git に入れない。

## 4. Django 側 `.env` 設定

`pm_backend/.env` に以下を設定する。

```env
FCM_PROJECT_ID=your-firebase-project-id
FCM_SERVICE_ACCOUNT_FILE=D:/pm/pm_backend/firebase-service-account.json
```

`FCM_SERVICE_ACCOUNT_JSON` を使う場合は次のどちらか一方のみ設定する。

```env
FCM_PROJECT_ID=your-firebase-project-id
FCM_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"..."}
```

通常は `FCM_SERVICE_ACCOUNT_FILE` のほうが運用しやすい。

## 5. Python 依存反映

開発PCまたは本番環境で依存を入れる。

```bash
cd pm_backend
pip install -r requirements.txt
```

今回追加された依存:

- `google-auth`
- `requests`

## 6. DB反映

`NativePushToken` テーブルを作成する。

```bash
cd pm_backend
python manage.py migrate
```

## 7. Android 側同期

```bash
cd pm-ui
npm install
npm run android:prepare:devpc
```

または本番向けなら:

```bash
npm run android:prepare:prod
```

この処理で `@capacitor/push-notifications` と Android プロジェクトが同期される。

## 8. 開発PC用 APK 作成

前提:

- `JAVA_HOME` を設定済み
- Android Studio / Android SDK インストール済み

```bash
cd pm-ui/android
.\gradlew.bat assembleDebug
```

生成先:

`pm-ui/android/app/build/outputs/apk/debug/app-debug.apk`

## 9. 実機確認

1. 開発PC向け APK を Android 端末へインストール
2. アプリ起動
3. ログイン
4. Android の通知許可を `許可`
5. もう一台または Web からその端末ユーザーへ発信

期待結果:

- アプリ前面: 画面内着信 + ネイティブ通知
- 画面消灯/待機: ネイティブ通知が届く

## 10. 確認ポイント

### `google-services.json` が無い

- PushNotifications プラグインは入っていても FCM 登録が動かない

### サービスアカウント JSON が無い

- Django から FCM 送信できない

### `python manage.py migrate` 未実行

- `native_push_tokens` テーブルが無く、端末トークン登録に失敗する

### `JAVA_HOME` 未設定

- APK ビルドが止まる

### Xiaomi / Redmi 系で通知が来ない

- 端末の省電力制御が強い
- 自動起動
- バッテリー最適化除外
- バックグラウンド制限解除
- 通知カテゴリの音許可

を別途確認する

## 11. この実装の制約

- FCM 化で待機時着信はかなり改善する
- ただし電話アプリ並みの確実性は保証しない
- メーカー独自の省電力制御や Doze の影響は残る
- Android で「強制終了済み・制限強め」の場合は取りこぼしがあり得る

## 参考

- Firebase Android FCM 開始手順:
  https://firebase.google.com/docs/cloud-messaging/android/get-started
- Firebase HTTP v1 送信:
  https://firebase.google.com/docs/cloud-messaging/send/v1-api
- Capacitor Push Notifications:
  https://capacitorjs.com/docs/apis/push-notifications
