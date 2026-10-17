# 中断理由マスタ 単位C-3 実装依頼書（Codex向け）

この文書は、Claude Codeセッションでの調査・BOSSとの確認を経て作成した、Codexへの実装依頼書です。Codexはこの会話の履歴を持たないため、この文書だけで実装に着手できるよう自己完結的に書いています。

## 1. 背景（完了済みの前提）

- 単位B-1（理由マスタ`m_interruption_reason`バックエンド）・B-2（マスタ管理画面）・C-1（`brake_line_record`への理由コード列追加とバックエンド検証）・C-2（ブレーキ・スポット画面`BrakeLineInput.vue`/`SpotLineInput.vue`のフロント改修）はすべて実装済み・evaluator合格済み・コミット済み。
- 理由マスタには、ライン種別1（レーザー）14件・2（ブレーキ・板金スポット）16件・3（その他の一般工程）18件、計48件が投入済み（開発DB）。
- 今回の単位C-3は、**一般の工程（ライン種別`3`）のPC/モバイル入力画面（`DesktopProcessInput.vue`・`MobileProcessInput.vue`）のフロント改修と、対応する`t_process_realtime_record`側のバックエンド（モデル列追加・検証ロジック）** を実装する。
- 表示・集計側（生産実績照会`ProductionRecordInquiry.vue`・CSV/PDF出力`productionRecordExport.js`・AIチャット中断理由集計）の追従は**今回のスコープ外**（別途C-1b相当で対応予定。event_dataの送信ロジックを維持するため表示は壊れない設計）。
- 設備トラブル判定ロジック（固定文字列比較）は**変更しない**（別途、独立単位C-4で対応予定）。

## 2. BOSS決定事項（確定仕様。これに従うこと）

1. 一般の工程の理由コードは**専用列**にする（`event_data`ではない）。列名: `interruption_reason_code`。
2. `DesktopProcessInput.vue`/`MobileProcessInput.vue`は、理由マスタ取得を**`line_category='3'`固定**で行う（ラインセレクタで全ライン選択可能だが、ブレーキ・レーザーは別画面が存在するため、この2画面は一般工程専用という前提）。
3. 「その他」コードの判定は**コード一致**（`3997`=中断、`3998`=強制終了。文字列一致ではない）。
4. 画面の選択肢表示は**表示名のみ**（コード番号は表示しない）。`i18n.js`の`interruptionReason.<コード>`キー経由で表示する（ライン種別3の18件分は既に5言語分`pm-ui/src/i18n.js`に追加済み）。
5. 「その他」選択時は自由記述（remarks）欄を表示し、**未入力では保存不可**（保存ボタン自体を消す実装）。**中断・強制終了どちらの「その他」でも必須**（現状はTEMP_ENDのみ必須でPAUSEは未入力でも保存可能という非対称な既存動作があるが、これをPAUSE側にも必須化するようBOSS承認済み＝既存動作の変更として明示的に実施してよい）。
6. 理由の日本語表記変更を許容する（例: 「部品ショート」→マスタの「部品待ち」、全角「３Ｓ活動」→半角「3S活動」。過去データは変換しない）。
7. 選択肢取得は画面表示・工程選択時にまとめて行い、アクション選択の都度APIを呼ばない。
8. 既存の`event_data.pause_reason`/`operator_action_reason`/`temp_end_reason`（表示用テキスト送信）は維持する。新規の`interruption_reason_code`はトップレベルに追加で送る。
9. 表示・集計側（`ProductionRecordInquiry.vue`等）には今回手を入れない。
10. 設備トラブル判定ロジック（`PAUSE_REASON_EQUIPMENT_TROUBLE`定数、`isEquipmentTroubleReason`関数）は1文字も変更しない。

## 3. 変更対象ファイル

**バックエンド**
- `pm_backend/apps/production/models_process_realtime.py`（列追加）
- `pm_backend/apps/production/migrations/0124_xxx.py`（新規。実装時に実際の最新マイグレーション番号を再確認してから番号を確定すること）
- `pm_backend/apps/production/serializers_process_realtime.py`（検証ロジック・シリアライザ列追加）

**フロントエンド**
- `pm-ui/src/views/production/DesktopProcessInput.vue`
- `pm-ui/src/views/production/MobileProcessInput.vue`
- `pm-ui/src/i18n.js`（新規i18nキー`processInput.pauseRemarksRequiredHint`を5言語分追加のみ。中断理由の52件分キーは既存）

**仕様書**
- `仕様書/ブレーキスポット入力整備実装計画.md`（単位C-3の実装内容・検証結果を追記）

**テスト（推奨）**
- `pm_backend/apps/production/tests_process_realtime.py`（新規テストクラス追加）

## 4. データの流れ

### 理由選択肢の取得元
- 既存API `GET /api/masters/interruption-reasons/?is_active=true&line_category=3`（変更不要、そのまま使う）。
- `m_interruption_reason`に`line_category='3'`の18件が投入済み:
  - PAUSE 12件: 3101設備トラブル／3201治具トラブル／3301品質トラブル／3401 3S活動／3402改善活動／3403工程指導／3404班長/対応者待ち／3901部品待ち／3902段取り替え／3904品番間違い／3921ティーチング／3922ワイヤ交換／**3997その他**
  - TEMP_END 6件: 3102本日設備復旧不可／3202本日治具使用不可／3905他へ製品切り替え／3906材料不足／**3998その他**
- 取得タイミング: 画面表示・工程選択時（`onProcessChange()`）にまとめて1回。アクション切替の都度APIを呼ばない。

### 保存方法・保存場所
- 新規専用列 `ProcessRealtimeRecord.interruption_reason_code`（`CharField(max_length=4, blank=True, default='')`、`BrakeLineRecord.interruption_reason_code`と同型）。
- 保存先レコード: `record_type='OPERATOR_ACTION'`の親レコード（PAUSE/TEMP_ENDの状態記録行）のみ。別途作成される`record_type='PRODUCTION'`の数量行には保存しない。
- 既存の`event_data.pause_reason`等（表示用テキスト）は維持する。

### 計算方法
- 新規計算ロジックなし。検証（バリデーション）のみ追加。

### 既存データの更新方法
- 既存行の`interruption_reason_code`は空のまま。過去データの変換・バックフィルは行わない。

### 入出力
- POST `/process-realtime/` のリクエストボディに `interruption_reason_code`（トップレベル、`remarks`と同じ階層。`event_data`の中ではない）を追加。
- 201レスポンスにも `interruption_reason_code` を追加。

## 5. モデル変更案

`pm_backend/apps/production/models_process_realtime.py` の `ProcessRealtimeRecord` に、既存の `remarks = models.TextField(...)`（78行目付近）の直後へ追加:

```python
interruption_reason_code = models.CharField(max_length=4, blank=True, default='', verbose_name='中断理由コード')
```

DB CHECK制約は追加しない（C-1の`BrakeLineRecord.interruption_reason_code`もDB制約なし。検証はシリアライザ層のみ）。

## 6. マイグレーション構成案

- 調査時点の最新マイグレーションは `0123_progressmonitortarget_monitor_type.py`。新規は `0124_processrealtimerecord_interruption_reason_code.py` と想定しているが、**実装着手時に`apps/production/migrations/`の実際の最新ファイルを確認してから番号を確定すること**（他の並行作業で番号が進んでいる可能性がある）。
- `dependencies`は確認した実際の最新マイグレーションを指すこと。
- `AddField(model_name='processrealtimerecord', name='interruption_reason_code', field=models.CharField(blank=True, default='', max_length=4, verbose_name='中断理由コード'))` のみ。
- 開発DBへの`migrate`は実施してよいが、**本番への`migrate`はBOSSの承認・実行を待つこと**（自分で本番に反映しない）。

## 7. バックエンド検証ロジックの設計案

### 参考にする既存パターン（C-1、変更しないこと）
`pm_backend/apps/production/services/brake_spot_session_sync.py`の`validate_interruption_reason_code(operator_action, reason_code)`（line_category='2'固定）。このファイル・この関数は一切変更しないこと。

### 新規関数（一般工程用）
`pm_backend/apps/production/serializers_process_realtime.py`内に、ほぼ同じロジックの新規関数を追加する（`line_category='3'`固定）:

```python
GENERAL_PROCESS_REASON_CODE_REQUIRED_MESSAGE = '中断・強制終了には理由コードの選択が必要です。'

def validate_general_process_interruption_reason_code(operator_action, reason_code):
    """PAUSE/TEMP_ENDのときだけ、一般工程（line_category='3'）の理由コードを検証する。
    有効ならTrue、無効ならFalse（呼び出し側で400にする）。START/END/RESUME等では常にTrue。
    """
    if operator_action not in ('PAUSE', 'TEMP_END'):
        return True
    if not reason_code:
        return False
    return InterruptionReason.objects.filter(
        code=reason_code, line_category='3', operation=operator_action, is_active=True,
    ).exists()
```
`masters.models`のインポート済みトップレベルimport文に`InterruptionReason`を追加して使うこと。

### シリアライザへの組み込み
1. `ProcessRealtimeCreateSerializer`の宣言フィールドに、`remarks`の直後へ追加:
   ```python
   interruption_reason_code = serializers.CharField(max_length=4, required=False, allow_blank=True, allow_null=True)
   ```
2. `validate(self, attrs)`内、`record_type == 'OPERATOR_ACTION'`のブロック（既存のPAUSE/ENDチェックの後）に追加:
   ```python
   if action in ('PAUSE', 'TEMP_END'):
       if not validate_general_process_interruption_reason_code(action, attrs.get('interruption_reason_code')):
           raise serializers.ValidationError({
               'interruption_reason_code': GENERAL_PROCESS_REASON_CODE_REQUIRED_MESSAGE,
           })
   ```
3. `create(self, validated_data)`: 追加のpop処理は不要。`interruption_reason_code`は実在するモデルフィールドなので、`parent_record = ProcessRealtimeRecord.objects.create(..., **validated_data)`でそのまま保存される（`remarks`・`batch_no`と同じ扱い）。後続で明示的kwargsで作られる`production_record`（PAUSE/END時の数量行）には含めないこと（現状どおり変更不要）。
4. 備考必須チェック（「その他」選択時にremarksが空なら保存不可）は**サーバー側では追加しない**。C-1も同様にサーバー側は「コードが有効か」だけを見ており、remarks必須はフロント側のみの制御（C-2の方針を踏襲）。

### レスポンスへの追加
`ProcessRealtimeRecordSerializer.Meta.fields`の`'remarks',`の直後に`'interruption_reason_code',`を追加。read_onlyにはしない。

## 8. フロント改修内容（Desktop・Mobile共通仕様、各ファイルに同一内容を実装すること）

C-2実装済みの`pm-ui/src/views/production/BrakeLineInput.vue`を参照実装とすること。実装前に必ず両ファイルの該当箇所を自分で再読し、行番号のズレがないか確認してから着手すること（この依頼書作成後にファイルが変更されている可能性がある）。

### 8-1. 選択肢をハードコード配列からマスタAPI取得に変更
- 削除: `pauseReasons`・`tempEndReasons`のcomputed配列（Desktop・Mobile両方）。
- 追加: `reasonMasterOptions = ref([])`（`line_category: '3'`でPAUSE/TEMP_END両方保持）、取得関数（`api.interruptionReasons.getInterruptionReasons({ is_active: true, line_category: '3' })`）。
- 呼び出し箇所: `onProcessChange()`の中で、既存の計画・開始済み品番取得等と並べて呼ぶ（画面表示・工程選択時にまとめて取得。アクション切替の都度は呼ばない）。
- 新規computed:
  ```js
  const pauseReasonOptions = computed(() => reasonMasterOptions.value.filter(r => r.operation === 'PAUSE'))
  const tempEndReasonOptions = computed(() => reasonMasterOptions.value.filter(r => r.operation === 'TEMP_END'))
  const OTHER_REASON_CODES = ['3997', '3998']
  const isOtherReasonCode = (code) => OTHER_REASON_CODES.includes(String(code || ''))
  ```

### 8-2. 選択UIをコード一致ベースに変更
- `record`オブジェクトの初期値に `interruption_reason_code: ''` を追加。
- `<select>`の`v-model`を`record.operator_action_reason`から`record.interruption_reason_code`に変更し、`option`を`pauseReasonOptions`/`tempEndReasonOptions`の`r.code`（value）・`t('interruptionReason.' + r.code)`（表示名のみ）に変更。
- `record.operator_action_reason`（表示用テキスト）は、選択コードから自動導出するwatcherを新設:
  ```js
  watch(() => record.value.interruption_reason_code, (code) => {
    record.value.operator_action_reason = code ? t('interruptionReason.' + code) : ''
  })
  ```
  これにより、既存の設備トラブル判定（`isEquipmentTroubleReason`、絶対に変更しない）と、既存の`event_data.pause_reason`/`operator_action_reason`/`temp_end_reason`送信ロジックはコード変更不要でそのまま動く（`t('interruptionReason.3101')`は`'設備トラブル'`と完全一致することを確認済み）。

### 8-3. 「その他」判定をコード一致に変更（文字列一致をやめる）
- 既存の`isTempEndReasonOtherSelected`（文字列比較ロジック）を、`isOtherReasonCode(record.value.interruption_reason_code)`ベースの判定に置き換える。
- **既存の非対称仕様を修正**: 現状はTEMP_ENDの「その他」選択時のみremarks必須チェックがあり、PAUSE側には無い。BOSS承認済みの通り、PAUSE側にも同じ仕組みを追加すること:
  ```js
  const isOtherReasonSelected = computed(() => isOtherReasonCode(record.value.interruption_reason_code))
  const requiresOtherReasonRemarks = computed(() =>
    requiresOperatorActionReason.value && isOtherReasonSelected.value
  )
  ```
  `canSubmit`内の`requiresTempEndOtherRemarks`参照箇所をすべて`requiresOtherReasonRemarks`に置き換える。

### 8-4. 「その他」時の自由記述→reasonTextへの反映をPAUSE/TEMP_END両方に統一
既存コード（Desktop側、保存処理内）:
```js
let reasonText = (record.value.operator_action_reason || '').trim()
if (submittedOperatorAction === 'TEMP_END' && isTempEndReasonOtherSelected.value) reasonText = (record.value.remarks || '').trim()
data.event_data.operator_action_reason = reasonText
if (submittedOperatorAction === 'PAUSE') { data.event_data.pause_reason = reasonText; moveToEquipmentState = isEquipmentTroubleReason(reasonText) }
else if (submittedOperatorAction === 'TEMP_END') data.event_data.temp_end_reason = reasonText
```
を、PAUSE/TEMP_END共通で「その他」ならremarksを使うよう変更:
```js
let reasonText = (record.value.operator_action_reason || '').trim()
if (isOtherReasonSelected.value) reasonText = (record.value.remarks || '').trim()
data.event_data.operator_action_reason = reasonText
data.interruption_reason_code = record.value.interruption_reason_code
if (submittedOperatorAction === 'PAUSE') { data.event_data.pause_reason = reasonText; moveToEquipmentState = isEquipmentTroubleReason(reasonText) }
else if (submittedOperatorAction === 'TEMP_END') data.event_data.temp_end_reason = reasonText
```
（`data.interruption_reason_code`はトップレベル送信。`event_data`の中に入れない。Mobile側も同様に変更すること。）

### 8-5. UIヒント文言の表示（remarks必須の案内）
- 既存の`processInput.tempEndRemarksRequiredHint`（TEMP_END専用文言）はそのまま残す。PAUSE用に新規キー `processInput.pauseRemarksRequiredHint`（文言例「※ 中断理由が「その他」の場合は備考が必須です。」）をja/pt/th/vi/idの5言語で追加し、「PAUSE かつ その他選択時」にこのヒントを表示する分岐をDesktop・Mobile両方のテンプレートに追加すること。CLAUDE.mdのUI設計方針により、ラベル省略は禁止（何の項目か分かる表示にすること）。

### 8-6. リセット処理への追加
以下すべての箇所で、既存の`operator_action_reason`リセットと同じ場所に`interruption_reason_code: ''`を追加すること:
- `resetForm()`
- `prepareEquipmentStateForm()`
- アクション種別が変わるwatcher
- （Mobileのみ）同一製品再選択時のリセット処理

実装前に、Desktop・Mobile両方で「`operator_action_reason`をリセットしている箇所」を`grep`等で洗い出し、漏れなく対応すること。

### 8-7. 設備トラブル判定ロジック（変更禁止）
- `PAUSE_REASON_EQUIPMENT_TROUBLE = '設備トラブル'`定数と`isEquipmentTroubleReason`関数は**1文字も変更しない**（C-4で別途対応予定）。`reasonText`の算出元が変わるだけで、比較ロジック自体は触らないこと。

## 9. 検証項目（機械的に合否判定できるもの）

1. `python manage.py makemigrations --check --dry-run` で、新規マイグレーション以外の意図しない差分がないこと。
2. DBで`m_interruption_reason`に`line_category='3'`の18件が存在すること。
3. `ProcessRealtimeRecord`に`interruption_reason_code`列が実在すること（マイグレーション適用後に確認）。
4. OPERATOR_ACTION・action=PAUSEで`interruption_reason_code`未送信または無効コード送信時、HTTP 400で`{'interruption_reason_code': [...]}`を含み、`ProcessRealtimeRecord`・`LineBacklog`いずれにも書き込みが無いこと。TEMP_ENDも同様。
5. action=PAUSEで有効な`interruption_reason_code`（例`3101`）を送信した場合、201応答かつ該当レコードの`interruption_reason_code`列に保存されること。
6. action=START/RESUME/END/CANCELでは`interruption_reason_code`が無くても400にならないこと（既存動作の非破壊確認）。
7. `DesktopProcessInput.vue`・`MobileProcessInput.vue`に、ハードコード配列`pauseReasons`/`tempEndReasons`（旧形式）が存在しないこと（`grep`で確認）。
8. 両画面の「その他」判定がコード一致（`'3997'`/`'3998'`）で行われており、`display_name`文字列一致でないこと（コードレビューで確認）。
9. 両画面で、PAUSE「その他」・TEMP_END「その他」のどちらを選んでも、remarks未入力時は保存ボタンが無効化/非表示になること（実機確認）。
10. 選択肢のラベルがコード番号を併記せず表示名のみであること（実機確認）。
11. 理由選択肢の取得が工程選択時にまとめて行われ、アクション切替の都度APIを呼んでいないこと（ネットワークキャプチャで確認）。
12. 保存ペイロードに`interruption_reason_code`（トップレベル）と、従来どおり`event_data.operator_action_reason`/`pause_reason`/`temp_end_reason`の両方が含まれること。
13. `isEquipmentTroubleReason`・`PAUSE_REASON_EQUIPMENT_TROUBLE`の行が、`git diff`に含まれないこと（変更されていないこと）。
14. `npm run build`（pm-ui）が成功すること。
15. 変更・新規ファイルに`toISOString()`の新規使用が無いこと。`timezone.now()`/`timezone.localtime()`の新規使用が無いこと（`datetime.now()`を使うこと、`USE_TZ=False`前提）。
16. 変更差分に新規の上限値（limit/page_size/timeout）・新規のフォールバックが無いこと。
17. 生産実績照会（`ProductionRecordInquiry.vue`）で、PAUSE/TEMP_END記録済みの一般工程データの「中断理由」列が、実装前後で表示が変わらないこと（表示・集計側は今回対象外のため非破壊であることの実機確認）。
18. i18n.jsの新規キー（`processInput.pauseRemarksRequiredHint`）がja/pt/th/vi/idの5言語分追加されていること。

## 10. 実装順の推奨

1. バックエンド（モデル→マイグレーション→シリアライザ）を先に実装し、Djangoのテスト（`tests_process_realtime.py`への追加）で検証。
2. フロント（Desktop→Mobileの順、またはその逆でも可だが**2画面は必ず同時に揃える**こと）。
3. i18nキー追加。
4. `仕様書/ブレーキスポット入力整備実装計画.md`の更新（単位C-3の実装内容・検証結果を、既存の単位A・B-1・B-2・C-1・C-2の記載と同じ構成・粒度で追記すること）。

## 11. 運用ルール（CLAUDE.mdより。遵守すること）

- コミット・push・`migrate`（本番）は、各ステップでBOSSの指示があるまで実行しないこと。
- フォールバックの新設、上限値の新設・変更は行わないこと（本依頼書の範囲にそのような変更は含まれていない）。
- 日時は`datetime.now()`を使うこと（`USE_TZ=False`のため、`timezone.now()`等は使用禁止）。
- フロントの日付処理で`toISOString()`は使用禁止。
- 実装後、完了報告の前に`仕様書/ブレーキスポット入力整備実装計画.md`を必ず更新すること（コード追加だけで検証完了・本番完了と扱わないこと）。
- 不確実な点・判断が必要な点が見つかった場合は、実装を進めず、まずBOSSに確認すること。

## 12. 未確認・スコープ外として明示しておく点

- 表示・集計側（生産実績照会・CSV/PDF出力・AIチャット中断理由集計）の対応は今回のスコープ外（設計上は専用列追加だけでは表示が壊れない想定だが、実機での最終確認は推奨）。
- 設備トラブル判定ロジックのコード一本化（C-4）は別単位。
- 過去データ（既存の`event_data`内の自由文字列）の変換は行わない。
