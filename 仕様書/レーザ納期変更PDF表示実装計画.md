# レーザ納期変更PDF表示 実装計画

## 初回版の対象と承認（以下は過去記録）

- 2026-10-14、BOSSが仕入先ごとの「納期変更PDFを開く」追加を承認。
- 材料発注の共通欄へ佐藤商事・名成鋼機のボタンを追加し、保存済みPDFを選択して開く。
- 元注文書の操作、納期調整の開始・保存、材料手数・進度、日付処理は変更しない。

## データと入出力

- 既存 `material-order-approval GET` で取得した現在週の `approvals` と、表示期間に重なる他週の `overlapping_approvals` を参照。
- `context.supplier` と選択仕入先が一致し、`context.material_order_adjustment_pdf_files[supplier].url` があるものだけを承認IDで重複排除する。
- 注文書期間は承認の `lock_start_date`・`lock_end_date`、保存日時はPDF metadataの `saved_at`。各承認に保存された最新PDFのみを表示する。
- 「開く」で保存URLを同期的に `window.open(url, '_blank', 'noopener')` へ渡す。既存MEDIA配信を使用し、PDF再生成・POST・新API・DB更新は行わない。
- 保存URLがないときは空状態を表示する。元注文書へのフォールバック、件数上限、全期間履歴の取得は追加しない。
- metadataが残っていて実ファイルが欠落している場合は既存MEDIA配信の404となる。

## 段階と実装内容

1. plannerによる既存取得・保存経路確認: root共有済み。承認ID14の保存URLは開発環境でHTTP200/application/pdf、ID12の欠落は既存404という制約を確認したとの報告を受領。
2. generator実装: Vue共通ボタン・一覧ダイアログ・保存URL直開き、仕様書・手順書の追記、実コンポーネントを使用するAPI差替え回帰テストを追加。
3. 検証コマンド: 下記結果欄へ記録。
4. evaluator独立評価: 条件付き。重大指摘なし。下記独立評価結果を参照。
5. 本番反映: 未反映。コミット・pushは今回未承認のため実施しない。

## 検証項目

- 仕入先分離、現在週と他週承認の選択、承認ID重複排除。
- 調整PDF URLだけを開き、元PDF metadataに代替しない。
- 未保存・metadata欠落・URLなしの空状態。
- 直開きが同期であり、再生成・保存・POSTを行わない。
- 共通ボタン2つと注文書期間・保存日時・空状態のtemplateおよびVueコンパイル。
- 既存ロック回帰テスト、フロントビルド、`git diff --check`。
- evaluatorによる元注文書コード不変・計画適合の独立確認。実ブラウザでの一覧とPDF表示、本番動作は未確認。

## コマンド結果

- `node scripts/test-laser-material-adjustment-pdfs.mjs`: 5件成功、exit 0。初回はテスト側のtemplate正規表現抽出が入れ子の閉じタグで途中終了しコンパイル確認1件失敗。Vue SFC `parse` による抽出へ修正し、再実行で5件成功。
- `node scripts/test-laser-material-order-locks.mjs`: 既存ロック回帰6件成功。
- `git diff --check`: exit 0。既存の改行コード警告のみ。
- `node node_modules/vite/bin/vite.js build`: exit 0、749 modules transformed、2m47s。他作業のフロント変更も含む作業ツリーで実行。
- ソース実装とコマンド結果・独立評価・本番反映は別段階として扱う。

## 独立評価結果（2026-10-14）

- evaluatorの総合判定は **条件付き**。実ブラウザのボタン・一覧レイアウト・PDF表示が未確認で、本番も未反映。重大指摘なし。
- 新規回帰5件・既存ロック回帰6件を独立実行しexit 0、差分check exit 0を確認。generatorのビルド実行記録exit 0も確認。
- 仕入先分離、現在週と他週承認、承認ID重複排除、調整URLのみ、同期直開きとnoopener、空状態、元注文書・Excel・保存・進度・日時・API・DB不変、文書の計画適合は合格。
- 読み取り専用DB検証で、ID14はMEISEI・開始週10/05・注文書期間10/12〜16で、調整URL・保存日時・実ファイルを確認。開発環境 `https://localhost:8501` で保存URLのGETがHTTP200・application/pdf・`%PDF-` であることを確認。
- ID12はmetadataがあるが実ファイルが欠落していることを確認（今回の表示範囲外）。既存MEDIA配信の404となる制約を維持。
- 未確認項目は実ブラウザ操作・表示と本番動作のまま残す。条件付き判定を維持し、開発コードの追加を検証完了・本番完了として扱わない。


## 全期間の注文書期間選択への拡張（2026-10-14）

### 承認と取得元

- BOSSが保存済みPDFの注文書期間を選ぶ方式と、表示週以外も選べることを承認。既存承認contextを参照する読み取り専用GET追加を明示済み。
- `GET /laser-weekly-plans/material-order-adjustment-pdfs/?supplier=MEISEI|SATO` を追加。supplier必須、不正値400。
- `ApprovalRequest` を `route_config__item_key=laser_material_order` と `context__supplier` で絞る。表示週・表示期間・status・route active制限や取得上限・ページングを追加しない。
- 正規の期間・URL・保存日時metadataがあるPDFのみ。注文書期間は `lock_start_date/lock_end_date`、URLとnaive ISO保存日時は `material_order_adjustment_pdf_files[supplier]`。壊れたmetadataの補完なし。
- 同期間は保存日時最大、同日時はID最大。レスポンス `items` は `approval_id/start_date/end_date/saved_at/url` の期間降順。
- plannerの読み取り専用DB確認ではMEISEI ID8（09/28〜10/02）・12（10/05〜09）・14（10/12〜16）、同期間重複なし、SATO候補0との報告を受領。ファイル名は仕入先・期間固定で同期間は上書き保存。ID12の実ファイル欠落は既存404制約を維持。

### 実装と検証項目

1. generator: 全期間GET、API wrapper、ダイアログの期間select・選択PDF保存日時・開くを実装。
2. ダイアログを開くたび取得し未選択で開始。loading・取得失敗・空状態を区別し、未選択/失敗/loadingで開く無効化。
3. 切替・閉じる・再開で候補と選択を消し、request番号で古い成功/失敗応答を破棄。
4. 選択保存URLだけ同期 `window.open(..., '_blank', 'noopener')`。DB更新、保存、PDF再生成、元PDF fallbackなし。元注文書・Excel・ロック・進度・日時処理不変。
5. UIテストを新契約へ更新、backend読み取りAPI用SimpleTestCaseを追加（ORM mock、unittest runner、SQLiteメモリ設定で実DB・テストDB生成・migrateなし）。
6. 仕様書と手順書更新。初回版の評価記録は過去記録として保持。
7. evaluator独立評価: 条件付き、重大不具合なし。拡張版の独立評価結果を参照。実ブラウザ操作・表示、本番動作は未確認。
8. 未コミット、push・本番未反映。対象外の並行変更は触らない。

### コマンド結果（拡張版）

- `node scripts/test-laser-material-adjustment-pdfs.mjs`: 新契約6件成功、exit 0（全期間・仕入先分離・未選択・URL/日時・error/empty/loading・応答競合・template/no POST）。
- `node scripts/test-laser-material-order-locks.mjs`: 既存ロック6件成功、exit 0。
- `DJANGO_SETTINGS_MODULE=project.analysis_test_settings` でdjango.setup後、unittestにより `production.tests_laser_material_adjustment_pdfs` を実行: 7件成功、exit 0（全期間・supplier400・重複最新・正規metadata・無上限・POST405）。DBへの接続/更新・migrateなし。
- `node node_modules/vite/bin/vite.js build`: exit 0、749 modules transformed、56.85s。既存のchunk size警告あり。対象外の並行変更を含む作業ツリーで実行。
- `git diff --check`: exit 0、既存の改行コード警告のみ。
- コマンドの実行結果は独立評価と区別し、generatorだけで完了判定しない。


### 独立評価結果（拡張版・2026-10-14）

- evaluatorの総合判定は **条件付き**。重大不具合なし。実ブラウザ操作・レイアウトと本番動作は未確認。
- UI6件・既存ロック6件・backend7件の合計19件を独立実行して成功、`git diff --check` exit 0。generatorのビルドexit 0・56.85sの記録を確認。
- 読み取り専用の開発DB確認と実GET view実行により、MEISEIはID14（10/12〜16）、ID12（10/05〜09）、ID8（09/28〜10/02）の期間降順3候補、SATOは空で、DB metadataとの一致を確認。
- 保存URLへの独立MEDIA GETでID14・ID8はHTTP200・application/pdf・`%PDF-`を確認。ID12は実ファイルがなくHTTP404。既存の欠落制約を維持しているが、拡張版では期間選択一覧に表示されるため、この期間のPDFは開けない。
- supplier必須/不正400、GETのみ、ページング/件数上限なし、同期間最新保存metadata、選択URLの同期直開き/noopener、古い応答破棄、閉じる/再開時リセット、未選択/取得中/失敗/空状態の区別、元PDF・Excel・保存・ロック・進度不変、新版文書との契約適合は合格。
- DB変更・migrate・コミット・pushは実施していない。本番未反映。条件付き判定と未確認項目をそのまま保持する。

## 配置変更: 「調整後」ブロック（2026-10-14）

- BOSS承認により、佐藤商事・名成鋼機の2つの「納期変更PDFを開く」を共通欄から独立した「調整後」ブロックへ移動。既存の枠・ボタンのスタイルを使用する。
- UIの配置と見出しのみ変更。期間選択・PDF閲覧・API・保存・DB・計算・権限の処理は変更しない。仕様書と手順書の操作場所を更新。
- 検証: Viteビルドは終了コード0（749 modules、1m39s、既存chunk size警告）。対象の差分チェックも終了コード0。独立確認は条件付き・重大指摘なしで、共通/調整後の配置と仕入先別ハンドラ、処理不変、仕様書・手順書の一致を確認。実ブラウザでの配置確認は未実施。
- 開発ソースのみ変更。コミット・push・本番反映は未実施。
