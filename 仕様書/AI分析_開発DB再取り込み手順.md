# AI分析 開発DB再取り込み手順

## 1. 目的

本番ではAI分析を使わない。開発で試して作ったテンプレート(`ai_analysis_template`)と実行履歴(`ai_analysis_run`)は、開発DBにだけある。本番のダンプを開発DBへインポートすると、開発DBが本番の状態に戻り、これらが消える。インポートの前にJSONへ書き出し、後に元のIDで戻す。BOSS承認 2026-10-12。

## 2. インポートで消えるもの

| 消えるもの | 戻し方 |
|---|---|
| テンプレート(`ai_analysis_template`) | 本手順の書き出し・復元 |
| 実行履歴(`ai_analysis_run`) | 本手順の書き出し・復元 |
| AI用ビュー(`v_ai_*`) | `migrate`(ai の 0034 以降のマイグレーション記録も消えるため、再実行で作り直す) |
| マイグレーション記録(ai の 0034〜) | `migrate` |
| ビューの定義者・列権限 | `setup_ai_views --apply`(`--reader-host`は付けない。開発のreaderはDB全体のSELECTを持つ) |

## 3. 対象と対象外

- 対象: テンプレートと実行履歴の、モデルにある全項目。モデルが保存していない実データ・結果・AIへ送った本文は、新たに集めない。
- 対象外: テンプレートの通知(`AIAnalysisTemplateNotification`)、AIの設定(プロバイダ・ポリシーなど)。インポート後は、通知は空になり、AIの設定は本番ダンプの状態になる。

## 4. コマンド

実装: `pm_backend/apps/ai/services/analysis_backup.py`(DBを使わない純粋な関数群)、`pm_backend/apps/ai/management/commands/export_ai_analysis_data.py`、同`import_ai_analysis_data.py`。

### 4.1 `python manage.py export_ai_analysis_data`(DBは読み取りのみ)

| オプション | 内容 |
|---|---|
| `--output-dir PATH` | 書き出し先。既定は`<リポジトリ>/output/ai_backup`。この下に実行日時のフォルダ(`YYYYmmdd_HHMMSS`)を作って書く |
| `--allow-empty` | テンプレートも履歴も0件のときも書き出す。既定は中止(ダンプのインポート後に誤って実行し、空のバックアップを作らないため) |

書き出すファイル(日時のフォルダ内):

| ファイル | 内容 |
|---|---|
| `templates.json` | テンプレートの全フィールド |
| `runs.json` | 実行履歴の全フィールド |
| `manifest.json` | 書き出し日時(`datetime.now()`)、件数、スキーマの版(フィールド名の一覧のハッシュ)、フィールド名の一覧、書き出し元のDB名、形式の版 |

- 日時はISO文字列、JSONFieldはそのまま、Decimal・UUIDは文字列で書く。復元時はモデルのフィールド型で読み戻す(マイクロ秒を保つ)。
- ユーザーへの外部キー(テンプレートの`approved_by`・`reviewed_by`、履歴の`user`)は、ユーザーIDではなく**ログインID**を`approved_by_username`などのキーで書く。NULLはNULL。
- `refined_from_run_id`・`replaces_id`・履歴の`template_id`は、**元のID**のまま書く。
- 既存のバックアップは上書きも削除もしない(毎回新しい日時のフォルダに書く。同名フォルダがあれば中止)。`manifest.json`は最後に書くため、途中で失敗したフォルダは復元の対象にならない。

### 4.2 `python manage.py import_ai_analysis_data`

| オプション | 内容 |
|---|---|
| `--input-dir PATH` | 読み込み元。`manifest.json`のあるフォルダ、またはその親(その下で名前が最新の`manifest.json`つきフォルダを使う)。既定は`<リポジトリ>/output/ai_backup` |
| `--dry-run` | 書き込まずに、復元できる件数・スキップする件数だけ表示する(DBは読み取りのみ) |
| `--force-merge` | 既存の行があっても、既存のIDと衝突しない行だけを追加する。既存の行は上書きしない |
| `--i-am-on-dev` | 開発DBであることの確認。**書き込むときは必須**(`--dry-run`では不要) |

動作:

1. `--i-am-on-dev`がなければ中止。`settings.DEBUG`が`False`の環境(本番の可能性)でも書き込まず中止する。
2. `manifest.json`の件数とファイルの件数が違えば中止。スキーマの版(フィールド名の一覧のハッシュ)が現在と違えば**必ず中止**し、違う項目名だけを表示する(続行するオプションはない。ファイルにない項目を既定値やNULLで埋める処理もない)。モデルが変わったときは、変更前のコードで書き出し直すか、BOSSと対応を相談する。
3. **既定で、対象テーブルに既存の行が1件でもあれば中止**する(`--dry-run`でも同じ判定)。`--force-merge`のときだけ、衝突しない行を追加する。
4. ユーザーをログインIDで引き当てる。外部キーの依存順(テンプレート→履歴。履歴の`refined_from_run`、テンプレートの`replaces`は参照先を先)に、**元のIDを明示して**INSERTする。作成・更新日時(`auto_now`系)は一時的に止めて、書き出した値のまま戻す。
5. 全体を1つのトランザクションで実行し、エラーなら全体をロールバックする。
6. 復元した件数・スキップした件数と理由(行ごとのIDと理由を含む)を表示する。

## 5. 手順

1. **インポート前**: `scriptsi_backup_before_import.bat`(英語だけの短い呼び出しで`ai_backup_before_import.ps1`を実行し、`export_ai_analysis_data`で書き出して件数と書き出し先を表示)。件数を確認する。
2. **本番ダンプのインポート**(`scriptsestore_pm_db.ps1`など、従来どおり)。
3. **インポート後**: `scriptsi_restore_after_import.bat`(`ai_restore_after_import.ps1`を呼ぶ)。次を順に実行し、失敗したらその場で止まる。
   1. `python manage.py migrate`
   2. `python manage.py setup_ai_views --apply`
   3. `python manage.py import_ai_analysis_data --i-am-on-dev`
   4. `python manage.py setup_ai_views --check`

`ai_restore_after_import.ps1`には`-DryRun`(確認のみ。復元できる件数・スキップ件数を表示して書き込まない)と`-Interactive`(確認→Y/Nの質問→復元)がある。日本語のメッセージとY/Nの質問はPowerShell側に置く。BATは英語だけの短い呼び出しにしてある(初版はBAT内の日本語がコマンドプロンプトで文字化けし、`choice`の質問が壊れて復元がやめになったため、2026-10-12に修正)。

`migrate`は、テーブル・ビューを作り直すため、インポート後は必ず先に行う(`import_ai_analysis_data`は、テーブルがなければ失敗する)。

## 6. 安全のガード

- 本番かどうかを確実に判定できる設定はない(`DEBUG`は環境変数の既定が`True`、`ALLOWED_HOSTS`も環境で追加するだけ)。そのため`--i-am-on-dev`を必須にし、補助として`DEBUG=False`なら書き込まない(上書きできる手段は設けない)。DBのホスト名での判定は、開発DBがローカル以外にある場合を誤って止めるため入れていない。
- 既定で、既存の行があれば中止する。`--force-merge`でも既存の行は上書きしない。
- 書き出しは、既存のバックアップを潰さない。0件の書き出しは既定で中止する。

## 7. スキップの扱い

次の行は、スキップして件数・理由・行のIDを報告する。**代わりのユーザーや値で埋めない(フォールバックなし)**。

| 理由 | 内容 |
|---|---|
| `user_not_found` | ログインIDのユーザーが開発DBにない(詳細に項目とログインIDを表示) |
| `id_conflict` | 同じIDの行が既にある(`--force-merge`のとき) |
| `unique_conflict` | 一意制約(テンプレートの系統ID+版、元の分析案ID+承認版、元の分析案ID+内容ハッシュ)が、既存の行または先に入る行と衝突する |
| `parent_skipped_or_missing` | 参照先(元の実行・置き換え元)がスキップされた、またはどこにもない |
| `missing_field` / `bad_value` | ファイルに必須項目がない/値を型へ変換できない(スキーマの版が同じなら通常は起こらない。既定値では埋めない) |
| `duplicate_id_in_file` | ファイル内に同じIDが複数ある |

履歴の`template_id`は外部キーではないため、参照先のテンプレートがスキップされても値はそのまま復元し、件数を「注意」として表示する。

## 8. 保存先とコミット

書き出し先は`output/ai_backup/`。`.gitignore`に`output/ai_backup/`を追加し、コミットしない。

**注意**: 実行履歴には、ログインID(ユーザー名)、分析目的、結果の改良の追加の指示の原文が含まれる。テンプレートにも承認者のログインIDと分析目的・コードが含まれる。共有フォルダやメールへ置かない。

## 9. 実装記録・検証結果・未確認

- 実装(2026-10-12): 上記3ファイル、手順スクリプト(`scriptsi_backup_before_import.bat`・`.ps1`、`scriptsi_restore_after_import.bat`・`.ps1`)、試験`pm_backend/apps/ai/test_analysis_backup.py`(37件、DBを使わない)。
- 検証(実装者の確認): 新しい試験37件、既存の`ai.test_setup_ai_views`・`ai.test_analysis_planning`・`ai.test_analysis_execution`が成功(計115件、2件は既存のskip)。`makemigrations --dry-run`で差分なし。開発DBに対する`export_ai_analysis_data`の実行(読み取りのみ。scratchpadへ書き出し)と、`import_ai_analysis_data --dry-run`(既存行ありの中止と、`--force-merge`で全件が`id_conflict`になることを確認)。
- 変異試験(実装者): 11種(ログインIDをユーザーIDに変える、代わりのユーザーで埋める、既存行チェックを外す、IDを復元しない、親を先に入れる順序を外す、スキーマ不一致を無視、dry-runでも書く、ID衝突チェックを外す、`auto_now`を止めない、`--i-am-on-dev`不要、ユーザーをIDのまま出す)と、スキーマ不一致でも続行する変異2種が、すべて試験の失敗で検出された。
- 独立検証(evaluator、2026-10-12): **条件付き合格**(重大な不具合なし)。独立の変異試験は22種で、21種を検出し、1種(コマンドが`suspended_auto_now`を呼ばない変異)は未検出だった。指摘と対応:
  1. 試験の穴(上記の未検出1種): 保存の時点で`created_at.auto_now_add`・`updated_at.auto_now`が止まっていることを検証する試験を追加した。`suspended_auto_now`を呼ばない変異と、復元を忘れる変異は、どちらも試験が失敗する(実装者が確認)。
  2. 本書の変異試験の数の記載: 上記のとおり直した。
  3. 本番誤実行の防止は`DEBUG=False`の検出のみ(スクリプトが`--i-am-on-dev`を自動で付けるため、フラグは防止にならない)。**既知の制限**として残す。
  4. MySQLの照合順序が大文字小文字を区別しない場合、一意制約の判定がPython側と食い違い得る。その場合は`IntegrityError`で全体がロールバックされる(安全側)。
  
  上記を反映した再検証(evaluator)は未実施で、評価未了のまま。
- **実機の往復(2026-10-12、BOSSが実施)**:
  1. 書き出し(11:55、テンプレート2件・実行履歴48件)。
  2. 本番ダンプを開発DBへインポート(テンプレート・実行履歴は0件になった)。
  3. `ai_restore_after_import.bat`: migrate=適用なし、`setup_ai_views --apply`=実行するSQLなし、`--check`=要対応0件、`import --dry-run`=復元できる テンプレート2件・実行履歴48件・スキップ0件。
  4. 復元(Y)。
  5. 確認(読み取り): テンプレート2件(最大ID2)、実行履歴48件(最大ID50)。次の自動採番はテンプレート3・実行履歴51(最大ID+1)。作成・更新の日時はマイクロ秒まで元のまま。テンプレートの状態(approved・pending_admin)は元のまま。実行履歴のユーザー結びつきは48件で欠けなし。改良元(`refined_from_run`)を指す履歴3件が復元された。
  
  これにより、MySQLへの実際のINSERT(元のID指定後の自動採番、日時の保持、外部キー)は実機で確認済み。
- 未確認: `--force-merge`と`user_not_found`スキップの実機での動作(試験は偽物のクエリでの確認のみ)。
- 反映状況: コードのみ。DB変更なし(マイグレーションなし)。実行はBOSS。

- 2026-10-12(BOSS承認): `--ignore-schema-mismatch`と、ファイルにない項目を既定値・NULLで埋める処理を削除した。スキーマの版が違えば必ず中止する。`--allow-empty`は残す。
