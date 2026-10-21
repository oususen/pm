# PostgreSQL切替 当夜計画（新PC・2026-10-21 02:00〜04:00）

- 作成日: 2026-10-20
- 位置づけ: `PostgreSQL移行計画書_v3.md` §4-2 の具体化。BOSSと新PCセッション（以下「PCセッション」）で実行する
- 状態: **当夜の切替は延期(2026-10-21 BOSS指示、日付未定)**。リハーサルを2026-10-21夜に実施済み(§9)。使用者の切替は未実施
- 作成者の制約: 本書を作成したクラウドセッションは新PC・PG・MySQLに接続できない。本書の数値は計画書の実測値の転記で、本番の最終実行値ではない

## 1. BOSS決定事項（2026-10-20）

| 項目 | 決定 |
|---|---|
| 切替先 | 新PC。IPは **10.0.1.139 のまま使う**（本番IP 10.0.1.232 への切替は今回の作業に含まない） |
| 停止時間 | 2026-10-21 02:00〜04:00（2時間） |
| 旧PC・旧MySQL | **残す**（戻し先として保持） |
| 方針A | pgloader の指定に `CAST type json to jsonb` を入れる（または 05 で変換） |
| 方針B | デフォルト `[]` の4列は、移行後に `'[]'::jsonb` を付け直す |
| 方針C-1 | スキーマは最初から `public` に作る（Django設定は変えない） |
| 2:00まで | テスト用PG（`pm-pg-q-test` / `pm_pg_q_test`）で検証と突合のリハーサル。BOSSとPCセッションで実施 |

## 2. 役割分担

| 役割 | 担当 |
|---|---|
| 計画・SQL作成（本書、`scripts/pg_cutover/*.sql.txt`。`.gitignore`が`*.sql`を除外するため拡張子は`.sql.txt`） | クラウドセッション（作成済み） |
| 新PCでの実行（pgloader、SQL、アプリ起動） | PCセッション。破壊的・本番影響の操作はBOSSの承認を得てから |
| 完了判定 | evaluator（独立検証）。実行担当の自己判定で「完了」としない（CLAUDE.md） |
| 戻す判断 | BOSS |

## 3. 前提の確認（リハーサルで潰す。未確認のものは「未確認」のまま報告する）

| # | 確認 | 理由 | 状態 |
|---|---|---|---|
| P1 | PG版アプリ（`C:\PST\pm_pg`、`pm_pg`ブランチ）の最新コミットが何か。このリモートには`pm_pg`ブランチがない | 切替に使うコードの特定。未pushなら当夜に失われるリスク | 未確認 |
| P2 | 方針C-1を **pgloader のどの指定で実現するか**（例: `ALTER SCHEMA`・`ALTER TABLE NAMES MATCHING ... SET SCHEMA`）。効かなければ `05` のAで移動 | 計画書では`pm_db`スキーマに作られた事実のみ。解決策は未検証 | 未検証 |
| P3 | `type json to json drop default` と `CAST type json to jsonb` の併用可否 | 計画書に「関係は未検証」とある | 未検証 |
| P4 | **ビューの扱い**。pgloaderはビューを移行しない。AI用ビュー等（migrations内RunSQL）はmigrate済み扱いのため、PGには自動で作られない | MySQL側のビュー数と`04`の5)で比較。差があればビュー再作成が必要。AI分析は本番無効なので、業務画面がビューに依存するかを先に確認 | **未確認・要重要** |
| P5 | トリガー・ストアド・イベントがMySQLにあるか | pgloaderは移行しない可能性 | 未確認 |
| P6 | PG接続のセッションtimezone（`Asia/Tokyo`）が`pm_pg`の settings.py に入っているか。`USE_TZ=False`のため必須 | 棚卸し文書§5。未着手と記載 | 未確認 |
| P7 | 動的SQL（`analysis_data_service.py` のバッククォート）はAI分析専用。AI分析は本番無効のため今夜の対象外 | 計画書 §3-4 | 対象外（BOSS確認） |
| P8 | 大文字小文字だけ違う隠れ重複（unique CharField 約45件）。`03`の最後のSQL等 | PGは区別する。MySQLは区別しない照合が多い | 未確認 |
| P9 | `django_migrations` が移行され、`migrate --plan` が空になること（計画書: showmigrationsで未適用0・適用済み581） | 起動時に誤ってmigrateが走らないこと | 検証用PGでは確認済み。最終データで再確認 |
| P10 | 主キーなしの2表（`bk_purchase_arrival_date_20261007` 41行、`z_tmp_laser_pattern_import` 302行）の値は未照合（BOSS指示） | 件数のみ確認 | 値は未確認のまま |
| P11 | スケジューラ・メール・通知・自動発注・外部連携の停止（PG検証側・切替後も業務再開判断まで） | 二重送信防止 | 計画書 §2-3 |

## 4. リハーサル（〜2:00）: テスト用PG `pm_pg_q_test`

目的は **時間を測りながら当夜と同じ手順を一巡**し、P1〜P11を潰すこと。各ステップの所要時間を記録する。

| # | ステップ | 実行 | 記録するもの |
|---|---|---|---|
| R1 | 現時点のMySQLのバックアップ（または使い捨てMySQLへの投入）。取得日時・コミットを記録 | PC | 取得時間、サイズ |
| R2 | 検証用PGを空にして再作成（**対象は`pm_pg_q_test`のみ**、BOSS承認） | PC | — |
| R3 | `01`→生成SQLを実行し、MySQL側の全表件数を取得（`mysql-counts-before`） | PC | 件数（286表・10,236,508行が基準） |
| R4 | pgloader実行（方針A・B・C-1を反映）。8GiBヒープ指定のイメージを使用 | PC | 所要時間、ExitCode、OOM有無 |
| R5 | `04`を実行し、結果を期待値と照合。必要なら`05`（トランザクション内）→再度`04`→COMMIT | PC | 差分 |
| R6 | `02`と`01`の件数を全表比較 | PC | 不一致表（期待0） |
| R7 | `03`をMySQL・PGで実行し、全項目を比較 | PC | 不一致項目（期待0） |
| R8 | PG版アプリを起動（`migrate`は実行しない）。`showmigrations`で未適用0を確認 | PC | — |
| R9 | 主要フロー確認（§6）。API 200、画面表示、追加登録でシーケンス重複なし | BOSS＋PC | 画面ごとの可否 |
| R10 | R1〜R9の所要時間から当夜の時間配分を確定し、本書§5を更新 | PC→クラウド | — |

リハーサルで不合格・未解決のものは、2:00の時点でBOSSが「当夜実施／延期」を判断する（§7）。

## 5. 当夜タイムライン（案。R10の実測で修正）

| 時刻 | 内容 | 責任 |
|---|---|---|
| 〜2:00 | リハーサル完了、go/no-go判断（§7） | BOSS |
| 2:00 | 利用停止の通知。**PMへの入力・定期処理・外部取込など全書き込み元を停止**（旧PCのPM・新PCのスケジューラ含む）。更新が止まったことを確認 | BOSS＋PC |
| 2:00〜2:20 | 最終バックアップ取得（取得時刻・サイズ記録）。MySQL側の件数（`01`）・集計（`03`）を取得 | PC |
| 2:20〜2:50 | 本番用PGを用意して（※下記）pgloader実行、`05`、`04` | PC |
| 2:50〜3:20 | 件数（`02`）・集計（`03`）突合。不一致が1件でもあれば原因をDBで切り分け（生成ロジックは最後） | PC＋evaluator |
| 3:20〜3:45 | PG版アプリ起動（スケジューラ停止のまま）、主要フロー確認 | BOSS＋PC |
| **3:45** | **合否判定（BOSS）**。不合格なら§7の戻しへ | BOSS |
| 3:45〜4:00 | 合格: スケジューラ・連携をPG側だけで再開、業務再開を通知。不合格: MySQL版へ戻して再開 | BOSS＋PC |

※ 「本番用PG」の置き場所（リハーサルと同じ`pm_pg_q_test`か、新規DBか）は未決定。**BOSS判断が必要**。最終データの投入先は、リハーサルの検証データと混ざらないように必ず空にして行う。

## 6. 主要フロー確認の項目（合否は機械的に判定できるものに限る）

| # | 項目 | 合格基準 |
|---|---|---|
| F1 | ログイン（旧本番ユーザー、`admin`）| 成功。**未確認だった項目** |
| F2 | 受注一覧・受注展開の画面 | エラーなく表示、件数がMySQL版と一致 |
| F3 | 生産計画（ガント）の表示 | 表示でき、同一日の`line_backlog`/`line_plan`の値が`03`と整合 |
| F4 | 在庫・進度の画面（進度監視） | 同一日・同一製品でMySQL版の画面値と一致（DBで確認。推測で一致としない） |
| F5 | スポットライン実績入力の工程一覧 | 200、工程が出る（jsonb対策の確認） |
| F6 | 追加登録（試験データ1件）と削除 | 主キー重複エラーなし（シーケンス）。**試験データは作業後に削除し、削除したことを記録** |
| F7 | 日時の表示 | 8時区切りの「今日」判定、画面の時刻がJSTで正しい（timezone設定の確認） |
| F8 | 文字列検索（製品コード等の大文字小文字） | MySQL版と同じ件数 |
| F9 | NULLを含む並び替え画面 | MySQL版と順序が一致（NULLの並び順の差） |

## 7. go/no-go と戻し方

- **no-go条件（2:00時点）**: R6/R7の不一致が解消できない、P4（ビュー）で業務画面が影響を受け対処できない、P1（コードの所在）が不明、リハーサル所要時間が2時間枠に収まらない見込み。→ **延期し、MySQL運用を継続**（旧環境は無傷）。
- **戻す条件（当夜）**: 突合で重大な不一致が解消できない／主要フロー（F2〜F5）が動かない／3:45までに原因が特定できない。
- **戻し方**: 業務入力再開**前**に戻すのが原則。PG側アプリ・定期処理を停止し、**停止前の状態のMySQL版アプリ・設定を復旧**する。旧PC・旧MySQL（BOSS決定で保持）と、新PCのPM用MySQL（ダンプ投入済み、スケジューラ停止中）が戻し先。PG対応版の接続先だけをMySQLに変えて戻すことはしない。
- **業務入力を再開した後にMySQLへ戻す**には、追加データの逆変換が必要で**未設計・未検証**。再開後の戻しは「即座に戻せる」とは扱わない。
- 戻し先として使うMySQLに、停止後の書き込みがないこと（最終バックアップ取得時点から変更なし）を確認してから戻す。

## 8. 守る規約（CLAUDE.md）

- コミット・push・本番反映・`migrate`・上限値の新設・フォールバックの追加は、BOSSの個別承認が必要。pgloaderの`drop default`等はフォールバックではないが、MySQL/PG両対応の分岐をコードに入れる場合は事前同意
- 数値は必ずDBの実データで確認する。本書の件数・時間は他セッションの実測の転記で、今夜の保証値ではない
- 完了判定はevaluatorだけが行う。未確認項目は「未確認」のまま報告する
- 実装計画書の進捗: 本書と`PostgreSQL移行計画書_v3.md`の双方に、実施結果・検証結果・未完了事項・反映状況を記録する

## 9. 実施記録（PCセッション・BOSSが追記する）

**2026-10-21(夜): 当夜の2:00〜4:00の切替は実施していない。使用者の切替は延期(BOSS指示、日付未定)。ただし「すぐ切り替えられる状態にする」方針で、リハーサルを実施した。**

| 時刻 | ステップ | 結果 | 所要時間 | 備考 |
|---|---|---|---|---|
| 23:19 | R2 リハーサル用DB`pm_pg_rh1`を新規作成(既存`pm_pg_q_test`は触らない) | 成功 | 4秒 | PG: `pm-pg-q-test`コンテナ内 |
| 23:19〜23:21 | R4 pgloader(ソースビルド版v3.6.9、ヒープ8GiB、`type json to jsonb drop default`、`ALTER SCHEMA 'pm_db' RENAME TO 'public'`、`SET MYSQL PARAMETERS time_zone`=+09:00) | 成功(rc=0、ERROR/FATAL 0件)。286表・10,236,508行・2.2GB | pgloader表示2分59.6秒、実経過128秒 | 入力元は使い捨てMySQL(`pm-mysql-q-test`、2026-10-20 23:43ダンプ)。**方針C-1(最初からpublic)・方針A(jsonb)をpgloaderの指定だけで達成**(P2・P3は解決) |
| 23:21 | R5 後処理: デフォルト`'[]'::jsonb`を4列へ付け直し(方針B、トランザクション)、`04`相当の構造確認 | 成功。public 286表、json型0列、jsonb 56列、timestamptz 0列、timestamp(TZなし)422列、PK284・FK537、シーケンス276 | 約1秒 | `pm_db`スキーマは残らない(RENAMEで`public`へ) |
| 23:21 | R6 全表の件数照合(MySQL vs PG、`count(*)`厳密) | **286表すべて一致**(合計10,236,508行) | 約4秒 | 記録: WSL `~/pgq/rh1-mysql-counts.txt`・`rh1-pg-counts.txt` |
| 23:2x | R8 PG版アプリ(`pm_pg`、DB=`pm_pg_rh1`、一時実行)で`showmigrations` | 未適用0件・適用済み581件(`migrate`は未実行)。`django_migrations`は587件 | — | 587と581の差6件はMySQL版と同じ(DBのみにある旧履歴) |
| 23:2x | R9 アプリからの読み取り(DB=`pm_pg_rh1`) | ユーザー104人、`admin`あり。スポットライン工程一覧APIが200(ライン5・工程5・品番58件) | — | **jsonb変換が前提**(pgloaderで達成済み) |

**切替スクリプトの試験(2026-10-22 01:02〜01:10、BOSS承認)**: `pm_pg`リポジトリ(新リポジトリ`oususen/pm_pg`)の`scripts/pg_cutover/run_cutover_pc2.sh`を、旧本番の新ダンプ`pm_db_backup_20261022_004451.sql`(2026-10-22 00:48取得、約2.8GB、末尾に`Dump completed`)で、新DB`pm_pg_rh2`に対して通しで実行。結果は**PASS(所要453秒)**: 使い捨てMySQLへのダンプ投入316秒、pgloader(ソースビルド版、ヒープ8GiB)3分56秒、後処理・検証約3秒。286表・**10,294,085行**の件数が全表一致、`public`286表・`pm_db`スキーマ残り0・json型0・timestamptz0・`django_migrations`587。`pm_pg_rh2`はアプリ未接続の状態で、`03`の集計42項目すべて一致(不一致0)、シーケンス276本は遅れ0、無効な制約・索引0、索引数1,042(MySQLと同数)。稼働中の`mysql`・既存PG DB(`pm_pg_q_test`・`pm_pg_rh1`)には書き込んでいない。日時の全行比較(`pm_pg_rh2`)は実行中。未確認: 主キーなし2表の値、全非日時列の全行比較、他PCからの接続、利用者向けURL・ポート・証明書、旧PCへの戻し方の確認。

**API比較(2026-10-22 03:00〜、BOSS承認。証跡: WSL `~/pgq/evidence-api/`)**: MySQL版(`pm_backend_prod`、新PCのMySQL、10/20ダンプ)とPG版(`pm_backend_pg_pc2`、DB=`pm_pg_ui`、同じダンプ)の各バックエンド内で、`admin`として、パラメータ不要のGET API 314本を同じ条件で呼び(1回の上限120秒・一覧は1ページ目のみ、BOSS承認)、応答を比較。名前に副作用の疑いがある27本は呼んでいない。書き込みなし。
- 初回: 完全一致244本、内容不一致42本、**状態コード不一致1本(PG版のみ500相当の例外)**。
- **問題1(修正済み・検証用DBのみ)**: `/api/order-lines/open-order-audit/`がPG版だけ`ProgrammingError: COALESCE types character varying and t_order_order_type cannot be matched`。原因はpgloaderがMySQLのENUM10列(`t_order.order_type`・`t_order.status`・`t_schedule_detail.status`・`m_bom_item.sourcing_type`・`m_routing_step.step_type`・`time_unit`・`m_routing_step_param.start_trigger`・`stg_order_daily.order_type`・`stg_order_raw.order_type`・`parse_status`)をPGのENUM型にしたこと(Djangoはvarchar扱い)。`pm_pg_ui`で10列を`varchar(30)`に変換し(デフォルト付け直し、ENUM型削除)、10列すべてでMySQLと値の分布・行数が一致、同APIがPG版でも200(応答サイズもMySQL版と同じ27,566,725バイト)。変換は`run_cutover_pc2.sh`の手順4bに組み込み、検証項目(ENUM型0・varchar(30)列10)を追加。
- **問題2(一部修正)**: 並び順未指定の一覧APIで、MySQLは主キー順に近い順で返すがPGは順序を保証せず、一覧の表示順・1ページ目の中身が変わる。`pm_pg`の`project/pagination.py`に「並び順未指定のQuerySetだけ主キー順にする」補完(ページ分け前、および`DEFAULT_FILTER_BACKENDS`)を実装(DISTINCT・GROUP BY・スライス済み・UNION・すでに順序指定ありは対象外)。単体テスト8件合格。補完後、`/api/boms/`は一致に変わった。**残り(約26本)は、`ordering`を明示した一覧で、並び順の値が同じ行(同順位)の並びが不定なことによる差**(例: 受注行`line_no`、生産指示`-scheduled_start_date, priority`、出荷実績`-shipment_date, product_code`)。MySQLも同順位の並びは不定で、PGは加えてページ間で重複・欠落が起きうる。対処案(同順位の最後に主キーを足す)は**未承認・未実装**。MySQLの同順位の順番の完全再現はできない。自前の処理で一覧を作るAPI(`all_users`、`brake-line-plan`、`products/line-final-candidates`、`consumables/movements/workers`)は個別の並び順指定が必要で未対応。
- 問題ではない差: `csrfToken`・`last_update`・`updated_at`・作業時間(現在時刻で変わる値)・Excel/PDF出力(約10本)。`line-backlogs`(440MB)・`line-demands`(189MB)は大きすぎて詳細比較せず(件数・集計はDBで一致を確認済み)。
- 修正後の再実施: 状態コード不一致0、完全一致244本(増加なし)、内容不一致43本(`/api/notifications/`が新たに差。件数51/52でデータの変化か時刻差と見られ、未調査)。
- 切替スクリプトの再試験(ENUM変換追加後): 新DB`pm_pg_rh4`、最新ダンプ、**PASS(485秒)**、286表・10,294,085行一致、ENUM型0、varchar(30)列10。途中の1回(`pm_pg_rh3`)は、私の編集ミス(スペース抜け)でスクリプトが止まった。修正して再試験し合格。
- 未確認: アプリの画面操作(私は画面を操作できない)、書き込み系API、パラメータ付きの条件(絞り込み)でのAPIの挙動、同順位対策後の再比較。
- 注記(ログイン): PG版のログイン失敗(`invalid credentials`)は、全DBで`admin`のパスワードハッシュが同一(データの問題ではない)であり、ブラウザの自動入力による入力違いの可能性が高い(確定ではない)。

**追加検証(2026-10-22 0:50頃、`pm_pg_rh1`に対する読み取り検証。証跡: WSL `~/pgq/evidence-rh1/`)**
- 日時の全行比較(Codexのツールを`pm_pg_rh1`・スキーマ`public`用に写して実行、主キーあり284表): 不一致は計20件で、**すべてPG版アプリ(`pm_pg`、DB=`pm_pg_rh1`)の使用で説明がつく**: `auth_user.last_login`1件(2026-10-22 00:15のログイン)、`django_session`にPG側のみ1件、`brake_line_record`にPG側のみ2件(id 28245・28246、2026-10-22 00:15:36・00:15:52、BOSSがブレーキ画面で実績入力を試した)・`t_process_realtime_record`にPG側のみ1件(id 32117、2026-10-22 00:16:02、`record_type=EQUIPMENT_STATE`・`equipment_state=BREAKDOWN`・process_id=11・`operator_login_id=admin`。**PRODUCTION種別の行ではなく、ブレーキの生産実績は`t_process_realtime_record`に保存されていない**。`BrakeLineInput.vue`は設備トラブルで中断すると設備状態入力画面(`/production/mobile-process-input`、record_type=EQUIPMENT_STATE)へ遷移する実装で、その画面からの登録。BOSSが設備トラブルを記録したことを確認済み=想定どおりの動作)、`notifications`4・`notifications_target_users`7・`notification_reads`4件がPG側で削除済み(アプリの動作。同じ削除は手を付けていない`pm_pg_q_test`にも出ている)。zero→NULLは0件。上記以外の日時セルは全行一致。
- 集計(`03`): `line_backlog`の13項目の合計(件数533,203、demand_qty_plan・order_qty・order_qty_actual・plan_qty・actual_qty・stock_qty・planned_stock_qty・adjust_qty・scrap_adjust_qty・scrap_qty・actual_shipment_qty・progress_qty・planned_progress_qty)は、**MySQLと手を付けていない`pm_pg_q_test`で全て一致**。`pm_pg_rh1`では7項目が不一致(366行・PGの統計で23,971回のUPDATE)だが、これはBOSSの実績入力に伴う在庫・実績の再計算の結果で、移行の誤りではない(`pm_pg_q_test`はUPDATE 0件)。`t_line_demand`・`line_plan`・`m_product`の集計と大文字小文字重複0・`sequence_no=0`の`plan_qty`≠0が0件・`django_migrations`587は一致。
- シーケンス276本: 最大IDより遅れているものは0(空テーブル61)。無効な制約0・無効な索引0・索引数1,042(MySQLと同数)。ビューはPG 0件(MySQL 23件はAI用`v_ai_*`のみ、業務コードは不使用)。
- **運用上の教訓**: 検証(件数・集計・日時比較)は、**PG版アプリを接続する前に実施する**。アプリを接続して実績入力などを行うとデータが書き換わり、移行の検証と区別できなくなる。`pm_pg_rh1`はアプリで書き込み済みのため、以降の移行検証の基準には使わない(使い捨て)。
- 未実施: 主キーなし2表の値の照合、全非日時列の値の全行比較(今回は`line_backlog`のみ詳細比較)。

**未実施・未確認(リハーサルの範囲外)**: `03`の集計比較(合計・最小・最大・NULL件数)、日時全行比較(Codexの検証では`json`型時点・`pm_pg_q_test`で実施済みだが今回の`pm_pg_rh1`では未実施)、主キーなし2表の値、画面でのF2〜F9の確認、シーケンスのずれ確認、ビュー23件(`v_ai_*`、AI分析用で業務画面は不使用のためPGには作らない方針で未作成)、他PCからの接続(ESET・経管の件が未解決)、最終データ(最新ダンプ)での再実施、HTTPS証明書、利用者が使うURL/ポート(PG版`18501`は経管申請の対象外)。コミット・push・本番反映は未実施。

## 10. 未決定（BOSSの判断待ち）

1. 本番用PGの置き場所（§5の注記）
2. P4（ビュー）の対処方針
3. `pm_pg`ブランチをこのリモート（`oususen/pm`）へpushしてよいか（PCセッションが参照するため。P1）
4. 当夜の主要フロー確認で、BOSSが追加したい項目
