# AI分析 結果の記録(評価の蓄積) 実装計画

作成日: 2026-10-09 / 状態: **計画のみ(Codexの意見を反映済み。BOSSの承認待ち。コード・DBは未変更)** / 依頼: BOSS
関連: `仕様書/AI分析基盤仕様書.md`、`仕様書/AI分析基盤実装計画.md`、`仕様書/社内AI運用規約・AI用DB辞書.md`、`仕様書/AI分析_テンプレート参照生成実装計画.md`

## 0. 全体のプランと実装順(2026-10-09、BOSS承認)

「AIがだんだん賢くなる」ための、全体の流れ。**規則(運用規約4.4)を先に決め**、依存の順に進める。

| 順 | 内容 | 依存 | 状態 |
|---|---|---|---|
| ① | 規則とルールを決める(記録の規則・個人評価の禁止・学習利用の境界・保持) | なし | **完了**(社内AI運用規約 4.4。未コミット) |
| ② | ローカルLLMの文脈長の調査(`num_ctx=4096`の実測と対策) | なし | **調査(文字数の実測)完了**。結果: 仕様書/AI分析_ローカルLLM文脈長調査.md。実測(トークン数)は、Ollama起動後 |
| ③ | 結果の記録(段階0→1→2→3。本計画) | ① | 計画済み(段階0の定義表から。BOSSの確認待ち) |
| ④ | 試験の自動化(T1〜T8を、モデル・指示文を変えたときに、自動で比べる) | ③のprompt_version・モデル別の成功率 | 別計画 |
| ⑤ | お手本の自動選択(目的から、近い承認済みテンプレートを自動で選ぶ) | ③の再利用・参考の成功率 | 別計画 |
| ⑥ | 実機での評価とモデルの選定(ローカルと社外APIを、同じ物差しで比べる) | ③④ | 継続 |
| ⑦ | ローカルモデルの学習 | ③⑤⑥と、学習利用の承認 | 将来。別計画 |

このプランは、AI分析の機能の追加・変更を承認するものではない(各項目は、個別の計画と、BOSS承認で進める)。

## 1. 目的

BOSSの目的は、**AIがだんだん賢くなること**。現状のシステムは、モデルそのものを学習させてはおらず、お手本(承認済みテンプレート)・指示文のルール・検査・診断を、**人の手で足して**賢くしている。自動で積み上がる仕組みがない。

そこで、分析案の作成・コード生成・試行・実行・採用の**結果(成功・失敗・失敗の理由コード・採用)**を、**実データ・本文・個人を含まない形**で記録し、次に使う。

| 使い道 | 内容 | 本計画との関係 |
|---|---|---|
| (1) お手本の優先 | 成功率の高いテンプレートを、優先してお手本にする | 本計画の再利用・参考生成の成功率を使う(お手本の自動選択は別計画) |
| (2) 失敗の型の把握 | 多い失敗の理由コードから、指示文・見本・検査を直す優先順位を知る | 本計画の集計 |
| (3) 比較 | モデル・指示文を変えたときの成功率を比べる | 本計画のモデル別・指示文の版別の集計(試験の自動化は別計画) |
| (4) 将来の学習データの選別 | 承認済みの「目的→分析案→コード」から、学習に使うものを選ぶ | 本計画の「採用」の印を使う(本文は、承認済みテンプレートにある。本計画では記録しない。学習は別計画) |

**本計画の範囲は、記録と集計だけ。** お手本の自動選択、試験の自動化、ローカルAIの学習は、別の計画。

## 2. 既存の仕組みと、足りない点(2026-10-09、コードの読み取り。DBの実データは未確認)

### 既にあるもの
- **Redisの一時データ(有効期限で消える)**: 分析案の`codegen`の`attempts`・`history`(各回の時刻・reasons・names)、試行の結果`codegen['trial']`、参考にした生成の`template_reference`。試行は、仕様書で「実行履歴に残さない」とされている。
- **DBの`AIAnalysisRun`**(`ai_analysis_run`): `status`・`reason`・`detail`・`template_id`・`template_version`・`refined_from_run`・各ハッシュ・所要秒。コード・結果・明細の本文は保存しない。例外として、利用者が入力した`refinement_instruction`の原文と`conditions`が入る(**新しい記録へは、絶対に複写しない**)。実行者の`user`を持つ。保存期間は未確定で、削除しない。
- **実行の結果の生成**: `outcome_from_result`・`outcome_from_exception`・`start_run`・`finish_run`・`record_not_run`。例外名は許可リストで制限。履歴の確定に失敗したときは、実行を止める設計。
- **採用に近い情報**: 再利用(`Run.template_id`・`template_version`)、保存(`AIAnalysisTemplate`の状態)、改良(`Run.refined_from_run`)。
- **権限**: 全利用者の履歴の閲覧とテンプレートの承認は、`settings.ai`の編集権限。
- **保持期間の仕組み**: 会話だけにある。`AIAnalysisRun`には無い。

### 足りない点
| 項目 | 現状 | 不足 |
|---|---|---|
| 分析案の作成の成功・失敗 | 例外を送出するだけ。DBに残らない | 記録なし |
| コード生成の各回の結果 | Redisの`history`のみ(分析案の期限で消える) | DBに残らない |
| provider・model | `Run`に列がない | モデル別の成功率が出せない |
| 指示文の版(prompt_version) | **存在しない**。`WRAPPER_VERSION`は外枠のハッシュで、指示文ではない | 定義から必要 |
| 試行の合否・参考にした生成の使用と結果 | Redisのみ | 記録なし |
| 実行されなかった分析案(作成・生成の失敗) | `Run`が作られない | 失敗率の分母がない |

## 3. 記録する項目(仮の表名: `ai_analysis_outcome`。1行=1つの出来事)

| 項目 | 何のため | 個人・実データでない理由 |
|---|---|---|
| id | 主キー | 業務値でない |
| event_key(一意) | 二重記録の防止。コード生成=生成の識別番号、実行=Runのpk、保存=テンプレートのpk など。**plan_idは持たない** | 乱数または内部IDだけ |
| recorded_at | 期間集計・保持。`datetime.now()` | 時刻のみ(粒度は確認事項3) |
| stage | plan(分析案の作成)/codegen/trial/code_approval/run/template_saved/template_reused/refined/reference_used | 固定コード |
| result | 成功・失敗・その他 | 固定コード |
| reasons | 失敗の型の集計(固定コードのリスト) | **許可リストで検証して保存** |
| provider / model | モデル別の比較 | AI設定の許可リスト内の名称 |
| prompt_version | 指示文を変えた前後の比較(指示文のSHA-256の先頭12桁。**新規の定義**) | ハッシュ |
| wrapper_version | 外枠の版 | ハッシュ |
| attempt_no | 何回目で成功したか | 数値 |
| reference_template_id / version | お手本別の、参考にした生成の成功率 | テンプレートの内部ID・版(名称は記録しない) |
| template_id / version / category | お手本別の、再利用の成功率 | 内部ID・版・固定コード |
| is_refinement | 改良の採用 | 真偽 |
| trial_status | passed/failed/unverified | 固定コード |
| run_status / run_reason | 実行の成否 | 固定コード |
| seconds(任意) | 所要時間の傾向 | 数値 |

### reasons の注意
- `ai_unsupported`の**理由文(AIの自由文)は、絶対に記録しない**。コード`ai_unsupported`だけ。
- `reason_names`・`names`(AIが宣言した変数名)は、記録しない。
- **試行のreason**は、コンテナの報告の先頭80文字をそのまま保存している(許可リスト化が未了)。記録するときは、既知のコードだけ保存する(確認事項6)。

### 記録しないもの
目的文・手順・出力案・条件・追加の指示、SQL・Pythonの本文と、個別のコードを特定できるハッシュ(`sql_sha256`等)、実行結果・明細・件数(`approved_counts`等)、期間・利用ビュー・列、**利用者の識別(user・氏名・ユーザー名)・分析案ID・ワーカーID**、テンプレートの名称・品番・顧客コード・登録名称などの値、AIの応答本文・`unsupported`の理由文・例外のメッセージ本文、変数名。

### 個人の評価に使えないようにする方法
- **利用者の識別を持たない**(user・plan_idを列に持たない)。
- 集計の出口を、管理者向けの**集計だけ**にする(行単位の一覧APIは作らない)。
- 少数の集計(N件未満)は、表示しない(Nは確認事項5)。
- 運用規約に「個人の評価・順位付けに使わない」と明記する。

## 4. 記録先の比較と推奨

| | A: `AIAnalysisRun`の列の拡張だけ | B: 新テーブル(推奨) |
|---|---|---|
| メリット | テーブルが1つ。実行の成否・テンプレートID・改良は既にある | 実行に至らない出来事(作成・生成・試行・採用)も記録できる。利用者の識別を最初から持たない設計にできる。Runの保持・閲覧と切り離せる |
| デメリット | 実行されなかった分析案を記録できず、**分母がない**。userとplan_idを持つので、集計を個人別に分解できてしまう。1行1実行で、生成の複数回を表せない | 新しいテーブルとマイグレーション。記録の呼び出し箇所が増える |
| マイグレーション | 列の追加(NULL可) | 新規テーブル。既存データへの影響なし |

**推奨はB**。過去の`Run`からの取り込みは、providerとmodelが無いため、行わない。

## 5. データの流れ

- **取得元**: 処理の中で既に持っている値だけ(分析案の作成: provider・model・参考の識別、コード生成: provider・model・attempt_no・reasons、試行: status、実行: outcomeのstatus・reason・`plan['template']`、採用: `save_template`の新規作成・`create_plan_from_template`・refinement)。新しい外部の取得はしない。
- **保存先**: DBの新テーブル。Redis・ファイルへの出力なし。外部APIへの送信なし。
- **計算**: 記録時は計算しない(固定コードと数値を書くだけ)。集計は`GROUP BY`(成功率=成功÷(成功+失敗))。
- **既存データ**: 更新しない。新しい行を追加するだけ(append-only)。過去分の取り込みなし。

### 記録の設計(処理を壊さない)
- 記録は、**本来の処理が確定した後**に行い、`try/except Exception`で受け止めて、ログ(固定コードだけ)を残す。前例: `analysis_run_service.py`の`mark_unknown_stale`。記録の失敗は、分析・実行を止めない。
- **`_finish`の`apply`の中に置かない**(競合で最大5回再試行されるため、二重になる)。`_finish`が成功を返した後に記録する。
- 二重記録は、`event_key`の一意制約と`get_or_create`(またはIntegrityErrorを無視)で防ぐ。試行は、実行のたびに新しい識別番号。
- `save_template`の`transaction.atomic()`の外で、**新規作成が確定したときだけ**記録する(再送では記録しない)。
- 性能: 各段階でINSERTが1回増えるだけ。インデックスは、`(stage, recorded_at)`・`(provider, model, prompt_version)`程度。

## 6. 変更ファイルと段階

変更ファイル(想定): `models.py`(`AIAnalysisOutcome`)と`0034_...`マイグレーション(`makemigrations`まで自動、`migrate`はBOSS)、新規`analysis_outcome_service.py`(記録・許可リスト検証・集計)、呼び出し箇所(`analysis_planning_service.py`・`analysis_codegen_service.py`・`analysis_run_service.py`・`analysis_template_service.py`・`analysis_template_reuse_service.py`・`analysis_template_review_service.py`)、指示文の版(`SYSTEM_PROMPT`と各ルールのハッシュ。分析案側は、固定部分の切り出しが要る)、集計コマンド`ai_outcome_report`、テスト、仕様書・運用規約・本計画の更新。

| 段階 | 内容 |
|---|---|
| 1 | 記録先と記録の関数(モデル・マイグレーション・許可リスト検証・二重防止・例外の吸収・prompt_versionの定義)。呼び出しなし |
| 2 | 記録の呼び出し(分析案の作成・コード生成の各回・試行・コード承認・実行の確定。採用は、同じ段階か、別に分ける) |
| 3 | 集計(まずは、コマンド・SQLだけ。モデル別・理由コード別・お手本別) |
| 4(任意) | 管理者向けの集計APIと画面(必要になってから。権限はsettings.aiの編集。権限仕様書の更新が要る) |

各段階で、計画→実装→検証(evaluatorまたはCodex)。

## 7. BOSSへの確認事項(推奨つき)

1. **記録先**: B(新テーブル)でよいか。マイグレーション(`makemigrations`まで自動、`migrate`はBOSS)に同意するか。
2. **利用者の識別を持たない方針**(user・plan_idを列に持たない)。推奨: この方針。
3. **日時の粒度**: 秒まで残すか、日単位に粗くするか。推奨: 日単位(個人の特定を避ける)。時間帯別の傾向は見えなくなる。
4. **保持期間**: 推奨は「当面は無期限」(行が小さく、個人情報を含まないため)。削除が必要なら、管理コマンドを新設する(日数の既定値を決めると、新しい上限になる)。
5. **閾値の新設**: 少数の集計を隠す件数N(推奨5件。実データの件数は未確認)。
6. **フォールバック**: 試行のreasonを許可リストに合わせるとき、一致しないものを`other`に丸めるのは、フォールバックに当たりうる。推奨: 丸めずに、`reasons=['unknown_reason']`という固定コードで残す。記録の失敗を吸収して本来の処理を続けるのは、設計上の必要としてBOSSに示す。
7. **権限**: 集計を見られるのは、settings.aiの編集権限を持つ者だけ(推奨)。段階4を作るなら、権限仕様書も更新する。
8. **分母の定義**: 成功率の分母から、中止・期限切れ・状態不明を除く(推奨。除外件数は別に出す)。
9. **過去分の取り込み**: しない(推奨)。
10. **prompt_versionの定義**: 分析案の指示文は関数内で組み立てられている。固定部分の切り出し(既存の指示文に触れる)か、固定の文字列定数をまとめてハッシュするか。
11. **参考にした生成の記録**: コード生成の記録に、参考のテンプレートのid・版を載せる(推奨)。
12. **外部送信**: 記録・集計は、外へ出さない(推奨)。

## 8. リスクと対策

| リスク | 対策 |
|---|---|
| 個人評価への転用 | 利用者の識別を持たない。集計だけが出口。少数の集計を隠す。運用規約に明記 |
| 実データ・本文の混入 | 固定の選択肢と許可リストだけ。自由文の列を作らない。禁止の列が存在しないことを、テストで機械的に検査する |
| 記録の失敗 | 例外を吸収して処理を続ける。ログに本文を出さない。失敗件数をログに残す |
| 二重記録 | `event_key`の一意制約。`_finish`の再試行の外で記録。`save_template`は新規のときだけ |
| 記録の欠落による偏り | Redisの期限切れ・プロセスの中断で記録されない出来事がある。分母は「記録された件数」であり、全件ではないと、仕様書・集計に明記 |
| 試行のreasonの自由文 | 許可リストで検査 |

## 9. 検証項目(合否が機械的に判定できるもの)

1. **列の検査**: `AIAnalysisOutcome`に、user・plan_id・目的・手順・条件・コード・approved_counts・期間・名称・detail・追加の指示に相当する列が存在しない(フィールド名の一覧で検査)。
2. **許可リスト**: reasonsに、未知の文字列(`ai_unsupported`の理由文・AIが作った変数名・例外メッセージ)を渡しても、保存されるのは固定コードだけ。
3. **二重記録**: 同じevent_keyで2回記録しても1行。`_finish`が再試行されても、コード生成の行は1回。`save_template`の再送で、template_savedは1行。
4. **記録の失敗が処理を止めない**: 記録関数が例外を出す(モック)状態で、`generate`・`run_trial`・`run_and_record`・`save_template`・`create_plan`が、従来どおりの結果を返す。「生成中」が残らない。
5. **段階ごとの記録**: 分析案の作成の成功・失敗、コード生成の各回、試行、コード承認、実行(success/failed/cancelled/expired)、テンプレート保存・再利用・改良・参考生成が、それぞれ1行ずつ記録される。
6. **値の一致**: 記録されたprovider・model・attempt_no・reasons・template_id・versionが、planとRunの値と一致する。
7. **日時**: `datetime.now()`由来(`timezone.now()`・`timezone.localtime()`を使っていない)。
8. **集計**: モデル別の成功率・理由コード別の件数・テンプレート別の再利用の成功率が、手計算の期待値と一致する。
9. **権限**(段階4を行う場合): settings.aiの編集権限がない利用者は、集計APIが403。行単位のデータが応答に含まれない。
10. **マイグレーション**: `makemigrations --dry-run`が、モデルとマイグレーションの一致を示す。追加は新規テーブルだけ。
11. **既存の動作**: 既存のAI分析のテスト(`test_analysis_*.py`)が全て合格。既存のAPIの応答が変わらない。
12. **外部送信**: 記録・集計のコードが、外部AIの呼び出しを追加していない。
13. **境界**: `inventory_calculator.py`・`progress_calculator.py`・`stocktake_initializer.py`に差分がない。

## 10. 評価を省略できない変更への該当

- マイグレーションを伴う変更: **該当**(新規テーブル。本番ではSQLの通知が要る)。
- 日時・日付の扱い: **該当**(記録の日時・期間集計)。
- 権限の変更: 段階4を作る場合は該当(段階1〜3は、コマンドだけで該当しない)。
- 進度・在庫・計画在庫・LineBacklog等・棚卸初期化: 該当しない。
- 分析案・コード生成・実行の処理に呼び出しを足すため、既存フローへの影響を、evaluatorまたはCodexが確認する。**評価は省略しない。**

## 11. 不確実な点

- 実データ(`AIAnalysisRun`・`AIAnalysisTemplate`の件数・失敗の理由の分布)は未確認。閾値Nの妥当性は、件数を見て決める。確認用SQLの例: `SELECT status, reason, COUNT(*) FROM ai_analysis_run GROUP BY status, reason;`
- 試行のreasonの値の範囲(コンテナ・launcherが返し得るコード)は未確定。許可リストの元が必要。
- prompt_version: 分析案側の指示文の固定部分と動的部分の境界は、実装時に確認する。
- 保持期間・閾値を、AI設定の列にするか、定数にするかは未定(列にすると、別のマイグレーションになる)。
- 既存の規約に、保持期間の定めがあるかは、未確認。

## 12. Codexの意見(2026-10-09)と、計画への反映

判定: **条件付き賛成**(P1なし)。新テーブルB案・利用者の識別を持たない・未知reasonの固定化・過去分の取り込みなし・外部送信なしには賛成。次を、実装の前に、詰める。

### P2(計画のまま実装した場合のリスク)と、対応
| リスク | 計画への反映(変更) |
|---|---|
| `event_key`にRunのpkを含めると、既存のRun(userを持つ)へ、直接たどれる | **`event_key`に、元レコードの直接のIDを使わない**。非公開のイベント識別子(乱数)、または、段階を含めた鍵付きハッシュにする。鍵の管理・照合の権限も定義する。完全な匿名化の保証ではない、と明記する |
| 少数件の非表示だけでは、推測を防げない(同じ人の繰り返しの利用でも、N件を超える。差分や期間を少しずつ変えると、1件の増減が分かる。任意のSQLでは、非表示が効かない) | **集計の出口を固定する**。コマンドにも、同じ非表示のルールを適用し、任意の細かい期間・多軸の交差集計を出さない。N未満の率だけを隠して件数を出す設計は避ける。合計からの逆算を防ぐ非表示も検討する。「個人評価に使えない」と断定せず、「禁止」と「推測のリスク低減」の両方を、運用規約に明記する |
| 実行結果を早く記録すると、最終結果と食い違う(ワーカーが、中止要求で成功を中止に、結果サイズ超過で失敗に、後から変える) | **実行の確定点を、`analysis_job_service.py`のワーカーの最終確定にする**(`run_and_record`の終了時ではない)。`record_not_run`・`HistoryError`・状態不明の判定・復旧も対象にする。状態不明の後に確定する場合に、append-onlyのどのイベントを集計上採用するかを決める |
| reasonの直接の複写で、本文が混ざる(試行・実行のreasonは、報告の文字列を、そのまま取る) | **許可リストを、`reasons`だけでなく、`run_reason`・各status・provider・modelにも適用する**。記録関数は、plan・history・outcome・例外を丸ごと受け取らず、**専用の引数で、許可項目だけ**を受け取る。未知のreasonは、全経路で`unknown_reason`にし、元の文字列を、ログにも残さない |
| 例外を吸収しても、外側のトランザクションの失敗状態を、壊す(「atomicの外」は、「コミット後」とは限らない) | 必要な箇所は、`transaction.on_commit`などで、**本処理の確定後に記録**し、記録側の失敗を、本処理へ伝播させない。DBの待ち時間による影響も検討する |
| テンプレート保存を、結果の採用と扱うと、評価を誤る(保存は、実行結果の採用を条件にしていない) | **「保存」「管理者承認」「実行の成功」「利用者による結果の採用」は、別の意味**にする。`template_saved`を「正しい結果として採用された」と数えない |

### P3と、計画に足すこと
- **イベントの定義表**(段階1の前の「段階0」): 各stageについて、開始条件・成功/失敗/除外・記録する確定点・重複キー・送信前に拒否された要求の扱いを決める。**「送信前に拒否された要求」と「実際にAIを呼んだ試行」は、分母を分ける**。
- **欠落の扱い**: 完了イベントだけの最小構成なら、「観測できた完了試行の率」と呼ぶ。開始イベントも持つなら、未完了率を示す。
- **prompt_versionと評価条件を分ける**: 指示の版・外枠の版・検査の版・生成設定の変更を区別する。分析案は、固定文・規則・用語対応・公開スキーマを対象にし、目的・期間・参考の本文・変数値は除く。コード生成は、完成したsystem文を対象にできる。**生成時の版を、後の段階でも使い、実行時の最新版で付け直さない**。固定文の切り出しの前後で、送信messagesが一致するテストを足す。
- **集計の指標**: 技術的な成功率(生成の合格率・SQL試行の合格率・実行の成功率・保存率)と、結果の正しさ・有用性は、分ける。中止・期限切れ・状態不明を除いた率と、除外件数を併記する(AIのタイムアウトなどの失敗まで、除外しない)。**モデル比較は、順位と断定しない**(件数・除外件数・カテゴリ・参考の有無・改良の有無・試行回数を併記する。利用者・目的の難しさの偏りは、補正できない)。
- **段階3のアクセス制御**: APIがなくても、コマンド・SQL・出力ファイルから、詳細な集計や生の行を取り出せる。**閲覧者と持ち出しの範囲を、段階3から決める**(段階4だけではない)。管理者の権限は、段階3から対象にする。
- **保持期間**: 「個人情報を含まないから無期限」には、**反対**(照合可能なメタデータが残るため)。**詳細なイベントの保持と、粗くした長期集計の保持を分けて**決める。長期集計への移行・削除・バックアップの扱いも決める。
- **学習データの選別との境界**: テンプレートの正式承認は、「学習利用可」の承認ではない。**学習への自動転用を禁止**し、別計画で、本文・コード・既定値の機密/個人情報の確認と、学習利用の承認を必須にする、という境界を、今、決めておく。
- 日時の粒度は、**日単位**(推奨)。公開の集計は、さらに粗い固定の期間と、限定した軸にする。Nは、候補(5)にとどめ、実際の件数と推測のシナリオを確認して、BOSS承認で決める。

### 計画の段階(修正)
| 段階 | 内容 |
|---|---|
| **0(新設)** | イベントの定義表・確定点・集計の軸・保持・匿名化の限界・アクセス制御を、確定する(計画書の更新だけ。コードなし) |
| 1 | 記録先と記録の関数(許可項目だけの入口、非公開のイベント識別子、prompt_version) |
| 2 | 記録の呼び出し(確定点は、段階0の定義どおり。`analysis_job_service.py`を含む) |
| 3 | 集計(コマンド・SQL。出口の固定・アクセス制御を含む) |
| 4(任意) | 管理者向けの集計API・画面 |

## 13. 進捗

| 段階 | 状態 |
|---|---|
| 計画 | 作成済み(2026-10-09)。Codexの意見を反映(第12節)。BOSSの承認待ち |
| 0 | **素案作成済み(2026-10-10、planner。第14節)**。レビュー(Codex・evaluator)とBOSS判断(14-9)の待ち |
| 1〜4 | 未着手 |

開発・本番の反映状況: 未実装のため、いずれも未反映。

## 14. 段階0: イベントの定義表(素案。2026-10-10、planner調査。実データ未確認・BOSS未承認)

パスは `pm_backend/apps/ai/services/` 以下。行番号は調査時点。

### 14-1. 共通の語彙と列

- result: `success`/`failure`(率の分子・分母)、`excluded`(基盤・状態・利用者操作。分母に入れず件数併記)、`unknown`(状態不明の観測)、`event`(出来事の発生。合否ではない)。
- 共通列(案): `source`(`ai`/`template`)、`provider`/`model`/`prompt_version`/`attempt_no`、`reference_template_id`/`version`、`is_refinement`。
- **`source`が必要な理由**: テンプレート再利用の分析案(`provider='template'`、`analysis_template_reuse_service.py` :80)でも、試行・コード承認・実行が走る。分けないとモデル別の率が汚れる。許可リストに `template` を入れる。
- `reference_used`/`refined` は stage にせず列にする(`plan['template_reference']`、`plan['refinement']` の有無で決まるため。改良は「続けて直したい」であり採用ではない)。

### 14-2. stage ごとの定義

| stage | AIを呼んだとみなす点/開始 | 記録点 | success / failure / excluded | 理由コードの出所 |
|---|---|---|---|---|
| plan | `analysis_planning_service.py` :263 の try 直前に `ai_called=True` | 成功は `store.create` の戻り(:289)直後。失敗は :272-274 を受ける外側1か所 | success=作成まで到達 / failure=`LocalAIError.code`(`ai_timeout`等5種+`ai_request_failed`)、`proposal_invalid`(新設) / excluded=`ai_called`がFalseの拒否 | `chat_service.py` :244-252。:273 は `str(exc)` で code を捨てるため記録側で `exc.code` を読む。`unsupported`と形式不正は区別できない(:122) |
| codegen | `analysis_codegen_service.py` :522 の `store.update(start)` 成功時 | `_finish`(:582)が戻った後に1回。再試行ループ内では記録しない | success=reasons空で generated / failure=reasons非空 / excluded=`late_response_discarded`(新設、409) / unknown=`inflight_released` | `AI_FAILURE_CODES`、`response_invalid`、`ai_unsupported`(**理由文は記録禁止**)、`parameters_*`、`GuardError.code`、`python_empty`等、`python:`+code(合成。完全一致の集合で持つ) |
| codegen_started(任意) | inflight保存直後 | 同左 | 開始のみ。落ちた試行の把握用 | メリット=未完了率が計算できる/デメリット=1試行2行、リンクキーが無く近似 |
| trial | 事前拒否(:620,:625)は記録しない | `store.update(apply)` 成功後(:660) | success=passed / failure=failed(コードは `GuardError.code` のみ。`message`・`step`は記録禁止) / excluded=`unverified`、`trial_discarded`(新設) | `unverified`の理由は launcher 由来。`killed_by_signal_{n}` は可変コード(正規化が要る)。launcher.py・job_main.py の全reason網羅は**未完了** |
| code_approval | 拒否は記録しない | `store.update(apply)` 成功後(:682) | `event`のみ | なし。「承認しなかった」は欠測。保存率は「放棄を含む転換率」 |
| run | 14-3 | `process_job` の `finish` が戻った直後(`analysis_job_service.py` :399)。`finish` 内には書かない(WatchErrorで再実行されるため) | 14-3 | 14-3 |
| template_saved | `created=True` の経路のみ | `save_template` の `transaction.atomic()` を抜けた直後。既存返却(:220,:248)は記録しない | `event` | `category`(固定6種)、`is_correction`。保存は実行成功を条件にしない |
| template_approved/rejected | 拒否・409は記録しない | `approve_template`/`reject_template` の atomic を抜けた後 | `event` | `rejection_reason`(自由文)・`approved_by`は記録禁止。却下は個人評価に転用されやすいので保持を短く |
| template_reused | `create_plan_from_template` | 成功は `store.create` の戻り直後 | success=分析案を作成(**実行の成功ではない**) / failure=テンプレート起因(`stored_hash_mismatch`等、固定値) / excluded=利用者起因(権限・変数値不正) | 再利用の成功率は `run`(`source='template'`)で測る |

記録に混ぜないもの(全stage共通): 目的文、`title`、警告文、`names`、`unsupported`の理由文、`literal_values`、SQL/Python本文、ハッシュ類、各種ID、`worker`、`counts`、`detail`、`rejection_reason`、テンプレート名。

### 14-3. 実行(run)の最終確定点

**最終**とするのは `store.update(job_id, finish, ...)` の戻り値 `completed` の `status`/`reason`(`analysis_job_service.py` :399)。`run_and_record` の終了時点ではない。

| # | 経路 | 最終 status/reason | 記録する result |
|---|---|---|---|
| 1 | 正常成功 | success | success |
| 2 | 成功だが後始末未完了 | failed/`cleanup_pending` | excluded(基盤) |
| 3 | 中止要求が確定より先 | cancelled/`user_cancelled` | excluded |
| 4 | 結果サイズ超過 | failed/`result_too_large` | failure |
| 5・6 | 実行失敗・実行中の例外 | `REASON_TEXT`内コード等 | 14-3b の分類表 |
| 7 | `run_and_record` 内の想定外例外 | Runは `unexpected_error` で確定後、`process_job` が `execution_failed` で上書き | excluded |
| 8・9・10 | 開始前の中止/期限切れ/テンプレート使用不可 | `user_cancelled`/`plan_expired`/`template_unavailable` | excluded |
| 11・12 | `HistoryError`(開始行/確定の保存失敗) | `history_failed` | excluded(Run行が無くても記録) |
| 13 | `finish` 内のRun確定失敗 | running のまま | **記録されない**(後で14・16の観測に頼る) |
| 14・16 | 状態不明(`heartbeat_lost`)/復旧コマンド | unknown | `run_unknown`(率の分母に入れない) |
| 15 | ワーカー消失の検出 | failed/`worker_unknown` | excluded |
| 17〜19 | API応答だけのunknown/後始末の再照合/受付拒否 | 変わらない | 記録しない |

**14-3b. failure と excluded の分類(案。BOSSレビュー)**: failure=コードの出来を示すもの(`child_exit_nonzero`/`result_invalid`/`result_too_large`/`timeout`/`oom_killed`/`column_type_unknown`/`unsupported_value`等)。excluded=基盤・状態・操作(`launcher_*`/`busy`/`cleanup_pending`/`history_failed`/`plan_expired`/`user_cancelled`/`worker_unknown`/`template_unavailable`/`execution_failed`/`unexpected_error`等)。**要判断**: `approved_count_changed`/`fetch_rows_exceeded`/`fetch_count_mismatch`/`refetch_mismatch`/`duplicate_key` はデータ・環境依存でどちらとも言い切れない。固定の `reason→class` 表で持つ。

**状態不明の後に確定した場合**(案A、推奨): `run_unknown` は分母に入れず観測件数として別集計。最終 `run` に `was_unknown`(真偽。`finish` 内の更新前statusから取得)を持たせ、率には含める。未解決の状態不明=`run_unknown`件数−`was_unknown=True`の最終`run`件数。案B(最初の観測だけ採用)は実装が単純だが、後から成功しても unknown のままになる。

**モデルへの帰属**: `run` に生成時の `provider`/`model`/`prompt_version`/`attempt_no` を載せるには、分析案(Redis)に `plan['outcome_meta']`(固定コードと数値のみ。実行の `snapshot` に残る位置)を新設する必要がある(**保存項目の追加。BOSS承認事項**)。メタの無い分析案(導入前に作成済み)は記録しない(「不明」を足すフォールバックはしない)。

### 14-4. 重複キーと主キー

`event_key` は確定点で `uuid4()` を1回だけ生成(元IDを使わない。案A、推奨)。再試行ループの内側では生成しない。同じ事象を2度記録し得る経路(`mark_unknown_stale` :108-121)は、条件付き `update` が1を返したときだけ記録する呼び出し位置の設計で解消する(一意制約は同一呼び出し内のリトライ防止にしか効かない)。主キーも乱数(自動採番は同日内の発生順を漏らす)。

### 14-5. 「採用」の定義

保存・管理者承認・コード承認・実行成功・再利用・改良は、いずれも「結果の採用」ではない(別イベント)。結果の採否を直接示す既存操作は**ない**。案X(推奨): 実行成功の結果に「役に立った/役に立たなかった/使わない」の3択を新設(UI+API。回答率・社会的望ましさの偏りに注意)。案Y: 保存・再利用・承認を代理指標とする(追加実装なし、意味は別)。X は新規の画面操作なので段階2に含めず別計画とする。

### 14-6. 分母と集計

- 分母に入れない: 送信前に拒否された要求(`_planning_input`検証、`resolve_planning_provider`拒否、確認コード不一致、`_reference_for`のQwen拒否、codegen :488-507 の各拒否、権限なし=ビュー層で弾かれる)。**記録もしない**(推奨)。
- 分母に入れる: plan は :263 以降、codegen は :522 以降。
- 生成後にプロセスが落ちた場合は inflight が残り、完了イベントが無い。解除時のみ `inflight_released`。率は「観測できた完了試行の率」と呼ぶ。

| 指標 | 分子 | 分母 |
|---|---|---|
| 生成の合格率 | codegen success | codegen success+failure(`source='ai'`) |
| SQL試行の合格率 | trial success | trial success+failure(`source`で分ける) |
| 実行の成功率 | run success | run success+failure(excludedの件数・理由を併記) |
| 保存率(転換率) | template_saved 件数 | code_approval 件数 |
| 再利用の成功率 | run(`source='template'`) success | 同 success+failure |
| 参考生成の成功率 | codegen(参考あり) success | 同。参考なしと並べる |
| モデル別・失敗の理由別 | 上記を provider/model/prompt_version で分割 / 理由コード別件数 | 順位と断定しない(運用規約4.4-12) |

出してよい軸: stage・result・reasons(単独)・provider・model・prompt_version・wrapper_version・source・category・attempt_no・参考有無・is_refinement・期間(**月単位**)。条件つき(N以上、作成者評価になりうる): template_id/version別、reference_template_id別。**出さない**: 時間帯別・曜日別・日別×モデル・2軸を超える交差・連続期間の差分・秒/分の時刻・挿入順。少数セルは率だけでなく件数も隠すことを検討する。

### 14-7. prompt_version

- 分析案: system は固定リテラル(:248-253,:255)+`PRODUCT_RULE_PLAN`+`WORK_ORDER_PLAN`+`OUTPUT_RULE_PLAN`+`term_guide_text()`+(参考ありのみ)`REFERENCE_RULE_PLAN`+公開スキーマ。ハッシュは固定部分、`reference_rule_version` と `schema_version` は別に持つ。目的文・期間・参考の中身・追加の指示・モデル・温度はuserメッセージ側なので除く。
- コード生成: `SYSTEM_PROMPT`(:153-175)の `sha256[:12]`。参考ありは `REFERENCE_RULE_CODE`(:146)を別版にする。
- 評価条件の分離: 指示の版/外枠の版(`WRAPPER_VERSION`)/検査の版(`validate_generated`の上限は外枠の版に入らない→`check_version`を持つか)/生成設定(温度、`max_tokens`、タイムアウト)。生成時の版を後の段階で付け直さない(`outcome_meta`に固定)。
- 既存動作を壊さない切り出し: ①現行の `create_plan` が送る messages を参考あり・なしの2ケースで捕捉する特性化テストを先に書く ②固定リテラルを1文字も変えずに定数へ移す ③切り出し後も一致を確認 ④部品一覧からversionを計算 ⑤「部品から組み立てたsystem」と「実際に送るsystem」の一致テストを足す。

### 14-8. 保持と匿名化の限界

保持(日数は案。BOSS承認): 詳細イベント A=90日/B=180日/C=365日、月次集計は無期限(軸は2軸まで、N未満は「その他」に統合)。バックアップが詳細より長く残る問題、削除の管理コマンド、日時は `recorded_on`(日付のみ)を推奨。

個人が推測されるシナリオと対策:

| # | シナリオ | 対策 |
|---|---|---|
| 1 | テンプレート別の成功率から作成者が分かり、作成者の評価になる | N以上のみ。長期集計に載せない。作成者別集計を規約で禁止 |
| 2 | 日付・状態・理由の組み合わせがRun履歴の1行に一致する | 日単位の粒度、`run`に`attempt_no`を載せない案、詳細は短期保持 |
| 3 | 少数利用(その日1人だけが使ったモデル・参考生成) | モデル×日の交差を禁止、N未満非表示、月次集計 |
| 4 | 管理者の却下・承認の日付とテンプレート状態の突き合わせ | 却下に`category`を載せない/短期保持、個人評価の使用を禁止 |
| 5 | 自動採番idが発生順を漏らす | 主キーを乱数に |
| 6 | 月次集計を2回出し、1件の増減から1人の行動が分かる | 固定の期間・軸、N未満の統合 |
| 7 | アプリのログ(run_id・時刻)との突き合わせ | ログに本文・IDを出さない方針の維持 |

### 14-9. BOSSへの確認事項(推奨つき)

| # | 事項 | 推奨 |
|---|---|---|
| 1 | 少数集計を隠す件数 N(閾値の新設) | 5。実データの件数確認後に決める |
| 2 | 詳細イベントの保持日数(上限の新設) | 90日か180日 |
| 3 | 月次長期集計の保持 | 無期限、2軸まで |
| 4 | 理由コード列長(上限の新設) | 80(Run.reasonと同じ)。超えるコードは許可リストに入れない |
| 5 | 未知のreasonを`unknown_reason`にする(フォールバックに当たりうる) | `other`に丸めず1種類のみ。provider/model/statusも同規則 |
| 6 | 記録失敗を吸収して本処理を続ける | try/exceptで固定コードのみログ。本処理は止めない |
| 7 | 分析案のメタが無い実行は記録しない | 記録しない。件数をログに残す |
| 8 | `plan['outcome_meta']` を Redis の分析案に追加 | 追加(snapshotに残る位置) |
| 9 | `trial_count` を分析案に追加 | 初回合格率が不要なら見送り |
| 10 | `codegen_started` を持つか | codegen のみ持つ |
| 11 | `reference_used`/`refined` は列にする | 列にする |
| 12 | 実行のreason→class分類表(14-3b) | 案に沿ってレビュー |
| 13 | 送信前拒否を記録するか | 記録しない |
| 14 | 結果の採用の新設(14-5 案X) | 段階2に含めず別計画 |
| 15 | `check_version` を持つか | 持つ(`WRAPPER_VERSION`との関係を整理後) |
| 16 | `event_key`・主キーを乱数に | 乱数 |
| 17 | `plan`で`unsupported`と形式不正を区別するか | 区別しない(現状どおり) |
| 18 | テンプレート別集計の出し方 | N以上のみ、作成者別は禁止 |

### 14-10. 不確実な点

1. 実データ未確認。`SELECT status, reason, COUNT(*) FROM ai_analysis_run GROUP BY status, reason;` で分布と件数を確認する(Nの妥当性もこれで判断)。
2. launcher.py・job_main.py の reason 全集合が未確認(`killed_by_signal_{n}` は可変コード)。
3. `SourceCheckError` の `extra` の全呼び出し元の網羅が未確認。
4. ローカルQwenの `LocalAIError.code` が空の場合 `ai_request_failed` に化ける(codegen :529)。`ai_auth` は送信前(APIキー未設定)と送信後(401/403)の両方で出るため、送信の有無を区別できない。
5. `on_commit` は DB の atomic を使う経路(`save_template`/`approve_template`/`reject_template`/`process_job`のfinish)でのみ意味がある。Redis中心の経路(plan・codegen・trial)は「本処理が戻った後」が確定点。
6. `process_job` の `finish` でDB更新が失敗すると記録が残らず、後続の観測(`mark_unknown_stale`/復旧)に頼る。
7. `mark_unknown_stale` は読み取り経路(`visible_runs` :413)からも呼ばれ、GETが記録を引き起こす。副作用の位置として許容するか要確認。
8. 既存テストが `reasons` 許可リストと実コードの同期をどこまで見ているか未確認。

### 14-11. 段階1の前に確定すること(レビュー観点)

stage/resultの語彙(`event`の分離、`run_unknown`・`codegen_started`の採否)/実行の最終確定点と経路7・`was_unknown`の扱い/理由コード許可リストの網羅(合成・可変コードの扱い、`reason→class`表)/`outcome_meta`の可否とメタ無し実行の非記録/`source`列とテンプレート再利用の率の分離/prompt_versionの対象と切り出し方法/乱数の`event_key`・主キー/保持日数・N・月次軸/テンプレート別集計の出口制限/「結果の採用」を段階2の範囲外にすること。
