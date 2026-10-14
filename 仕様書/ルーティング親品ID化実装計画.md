# ルーティング親品ID化実装計画

## 承認範囲・状況（2026-10-12）

本節と初期の段階表はコード準備時点の記録。現在の開発／本番移行状況は後段の実移行結果、2026-10-13の承認済みUI/API修正は末尾のレビュー対応節を正とする。

BOSS承認: 親品ID化を先行する。元CSVの33工程に追加3工程を含めた36補正候補を移行準備へ含める。BOM新版保護／更新対象版選択は単位2として保留。2026-10-12のBOSS指示により、コード・移行対応表・検証結果・本計画を親品ID化のローカルコミットとして保存する。DB更新、migrate、push、本番反映は未実行・別途承認が必要。

親品の取得元は品番マスタ、保存先は `m_routing_step.parent_product_id`（ProductへのNULL可・PROTECT FK）。現在コード／品名はFKから取得する。旧 `remark` は物理保持するが親品入力・表示・同期・計算に使わない。親品任意と親品＝加工後品の中間工程を維持し、旧文字列参照フォールバックは追加しない。

## 段階と変更ファイル

| 段階 | 内容 | 状況 |
|---|---|---|
| 1．対象分類 | DB一次照合、実際の直上工程／元BOM／材料／BOMの確認 | 読取照合実施。誤抽出の旧24不一致は対象外。36候補の業務文脈を保存 |
| 2．正規参照 | モデルFK、API ID入力／読取現在コード、生成・同期・数量・管理画面・輸出・受注のID参照 | コード準備。独立再検証1回目は条件付き（下記の未確認を維持） |
| 3．既存移行 | schema追加、全件の既存文字列→IDと36補正の直前再照合・原子的一括更新 | コマンド準備のみ。開発／本番未実行 |
| 4．AI表示 | 既存公開列を維持してFK JOIN、owner新列SELECTとDEFINER再設定 | 新migration／手順SQL準備。開発／本番未実行 |
| 5．検証・切替 | SQLite検証、build、独立評価、保守停止下で移行後に全クライアント切替 | SQLite・build・独立再検証実施。実DB切替は未 |
| 単位2 | BOM新版保護と影響一覧／対象版選択 | BOSS指示で保留。今回は実装しない |

変更箇所:

- `masters/models.py`、`migrations/0087_routingstep_parent_product.py`: 親品FK。
- `masters/serializers.py`: `parent_product` ID入力、`parent_product_code` / `parent_product_name` 読取専用。存在しないIDと旧remark入力を拒否。非自己親で直上工程が実在する場合はその加工後品との不一致を拒否。
- `masters/views.py`: BOMからの生成／再帰追加、BOM同期、手動入力、使用個数、変更履歴、製品出力の親参照をID化。工程create/updateの関連保存はatomic。Product削除のPROTECT拒否はAPI400。
- `masters/admin.py`: 親品選択をFKへ変更、旧remarkを編集対象から除外／読取専用。使用個数とExcel親品コードをFKから取得。
- `masters/management/commands/export_bom_routing_sql*.py`、`export_bom_routing_compare_csv.py`: 親品FKと現在コードを出力。SQL輸出の旧remark列は復旧値保存として残す。
- `production/services/order_expansion.py`: 中間工程の子再配置を親品IDで比較し、優先順位・LT・数量計算を変更しない。
- `RoutingMaster.vue`: POST/PATCHで親品IDを送信、IDで自己親・親工程を比較。表示の検索文字列を編集すると選択IDを解除する。2026-10-13承認修正により画面追加は親品ID選択必須、既存欄の空保存を拒否する。APIの任意NULLは新規作成／元からNULLの既存データだけ維持する。
- `masters/management/commands/migrate_routing_parent_products.py`、`services/routing_parent_approved_mapping.json`: 全件移行の専用コマンドと承認済み36対応表。
- `ai/migrations/0051_routing_parent_product_views.py`、AI説明2箇所、`setup_ai_views.py`: 親品ID JOINで既存33／20公開列・順序・全行公開を維持。旧0042/0043の履歴定義は不変。
- `scripts/routing_parent_ai_views_definer.sql.txt`: 2ビューのowner新列SELECT、DEFINER再設定、旧remark列SELECT取り消し（未実行）。既存33修正SQL／本番全ビューSQLは変更しない。

## 既存データ移行の照合

調査記録は `output/routing_parent_migration_review.json`（2026-10-12 13:46の読取結果）と `output/routing_parent_migration_identity.json`（同13:58の36候補文脈照合）。調査時の件数を適用条件として固定しない。DBは並行操作で変わり得るため、適用直前の現在値を全件再照合する。

対応表は工程ID・ルーティングID／コード／完成品コード・加工後品ID／コード・旧親コード・階層・新親コードを保持する。本番の新親品IDは現在の品番コードから解決し、開発のProduct IDを転用しない。未登録値の補正は36承認候補に限定し、直上親工程・その材料・親子BOMの現存を確認する。既に旧33SQLで候補コードへ直された行も同じ文脈を照合する。元BOMがある行は親と子＝加工後品の両方を照合する。

対応表JSONの取得元は開発DB読取snapshotであり、本番DB由来とは記載しない。補正対象を特定する工程ID／ルーティングID／加工後品IDも一致条件である。本番では2026-10-12に全36工程のIDと業務コード・階層を含む全文脈を直接照合し一致したため適用できた。別のID体系を持つDBへそのまま流用しない。別環境では業務キーから対応する対象を特定した新対応表を別途確認・承認する。新親品ID自体は適用先Productからコードで解決するため、開発の親品IDを転用する方式ではない。

未承認の未登録親品、文脈不一致、元BOM親子の不一致、実在直上親と非自己親の不一致が1件でもあれば一覧を出して全件中止。未確定行をNULL／ゼロで補完しない。元から親品未指定の行だけNULLを維持する。親品／階層不一致の旧誤抽出24行に階層修正を加えない。親工程欠落の既存例外13525／17314、既存階層10の16629は親品を維持し、工程追加／階層変更を行わない。

初回移行（全工程の親品IDが未設定）では、まず承認36全対象の存在・旧親コードが承認旧値または候補値であること・routing/output/階層/品番コードの文脈を必須照合する。承認対象の欠落、空変更、加工後品コード等の別登録済みコードへの変更も全件停止する。元33SQLで候補コードへ直された行は文脈・材料・BOMが一致すれば許可する。

コマンドは既定が読取照合。`--apply`時は全関連行を同一トランザクションでロックして現在値を照合し、全件成功時だけ親品IDを一括保存する。remarkは改変しない。既に親品IDが存在するDBへの適用は部分移行／切替後旧値上書きを防ぐため拒否する。既に親品IDが存在する状態の既定読取は「FK状態読取点検」モードと表示し、新FKの存在・現在コード・BOM／工程文脈を正として行う。NULLも正規値として扱い、旧remarkが残っていてもそこから親品を復元／移行候補へ追加しない。定期スケジュールや自動修復は追加しない。

## リリース手順（BOSS承認後に実施）

1. 対象DB・バックアップ／工程旧値一覧・新FK対応表を確認する。schema／データ／ビュー／API／UIを一体の切替として扱う。ルーティングや品番・BOMを更新する画面、バッチ、スケジューラを停止し、利用者操作を保守停止する。ロックだけで新規行追加・別クライアント操作を完全に防ぐものではない。
2. 新アプリを公開せず `masters 0087` までschema追加。現コードで専用コマンドを実行するための環境は準備するが、新API／UI／スケジューラを起動しない。通常 `migrate` 全体ではai0051も先行するため、段階を指定する。
3. `python manage.py migrate_routing_parent_products` で現在値と対象全件を照合し出力を保存。問題があれば旧方式のまま停止して原因を確認する。元CSVの33修正SQLとこの移行を同時並行適用しない。
4. BOSS承認後に同コマンド `--apply` でロック後の再照合と全件更新。工程数不変、対象36候補と全既存登録コードの新FK、未解決0、元BOM親子／実在直上親の整合を確認。新FK導入後は旧33SQLでremarkを書き換えても親品の業務修正にならない。
5. `ai 0051` で2ビュー切替。対象DBの実アカウントを確認し `scripts/routing_parent_ai_views_definer.sql.txt` でownerの新列SELECT、2ビューDEFINER設定、旧remark SELECT取り消し。他ビューがremarkを読む場合は取り消しを先行しない。owner／reader双方で公開列・行数・コード改名反映・NULL親品を確認する。MySQLのDDLはデータ更新トランザクションと一括rollbackできないため段階ごとに確認する。

   **旧 `output/prod_ai_views_definer.sql` は再実行禁止。** 親品を旧remarkから取得する定義と旧列GRANTを含むため、ID切替後に実行すると正規参照が戻る。2ビューの正式原本は `scripts/routing_parent_ai_views_definer.sql.txt`。本番owner切替はBOSSが「今回はデータ移行の確認までにする」と指定したため保留し、本手順の記載を実行許可と扱わない。
6. APIとUIの全クライアントを同時に切り替え、確認後に保守停止を解除する。全件移行未完了のまま新API／UIやAIビューを公開しない。旧remarkを送るクライアントは400になるため更新漏れを確認する。

## 復旧

schema追加のみ／全件移行失敗時は保守停止を継続し、旧コード・旧AIビューで再開する方針を確認する。移行失敗は全件トランザクションが取り消される。新FK列を削除する操作を自動実行しない。

切替後に親品入力や品番改名がある場合、保存した旧remarkをそのまま使って旧アプリへ戻すと切替後の変更を失う。BOSSへ現在状態維持か移行前snapshot復元かを明示し承認後に復旧する。現在状態維持の場合は保守停止下で現在FK→現在品番コードを旧remarkへ逆変換し、親未指定はNULLにする。照合結果を保存してから旧AIビューと旧owner列権限を戻し、旧アプリへ切り替える。逆変換／snapshot復元のSQL実行は今回未許可・未実行。旧remark保持は移行前復旧材料であり、切替後の業務変更を自動復元するものではない。

## 試験結果と未確認

- SQLite専用 `project.analysis_test_settings`、既存 `D:/pm/venv/Scripts/python.exe` で、親品機能15件・既存AI定義32件・新中間工程受注展開1件の計48件OK。不存在ID、旧remark入力、直上親不一致、任意NULL、自己親、生成final自己親、品番改名、PROTECT／API400、使用個数、BOM同期、API失敗atomic rollback、未知移行値全件中止、既存FK再適用拒否、AI列順／行数／改名反映を確認。
- 既存 `production.tests_order_expansion` は10件中4件成功、3failure／3error。HEAD版サービスをメモリ内差し替えした同設定・同日付の比較でも同じ6件失敗。日付だけを固定しても5件失敗するため、今回のID置換で新しく生じた差分とは確認されない。既存試験／業務計算を今回scopeで修正しない。受注展開全体の回帰試験は未合格として残す。
- root実行: `npm run build` 成功（749 modules、既存chunkサイズ警告あり）、`makemigrations masters --dry-run --check` 成功（No changes detected）。
- 初回system Python試験はredis未導入で停止。既存venvに切替して上記を実行した。新依存追加なし。既存requests依存versionwarningは非致命。
- MySQL実DDL・本番DEFINER／列権限、実DB全件移行、ブラウザ手動操作は未確認。SQLiteのCREATE VIEW検証はMySQL `CREATE OR REPLACE`／DDL検証の代わりではない。
- SQL輸出・Excelの実ファイル往復、全受注版・全同期パターンは独立evaluatorで確認範囲を判断する。generatorは完了判定をしない。evaluatorの判定・未確認事項は本計画へ追記する。

## 保留・業務上の限界

現行のBOMItemを過去／未来を含む複数ルーティングが参照し、BOM編集や再帰追加が複数版へ同期する仕組みは残る。対象版選択だけでは未選択ルーティングの元BOM内容が変わるため、BOM新版保護かリンク切断・snapshot保存かの方式を単位2で決める必要がある。BOSSは今回ID化のみ先行と指示済み。品番未登録・改名後の古い親コードの残存はID化で防ぐが、BOM設変をどの版へ反映するかの問題は未解決。


## 初回独立評価の指摘への修正（2026-10-12、独立再検証1回目実施済み）
初回評価は不合格。指摘は、承認対象の途中変更／欠落が移行照合を迂回できる、管理画面が直上親不一致を保存できる、必須SQLがgitignore対象でGit反映できない、の3点。

- 承認全対象preflightを追加し、旧値変更（登録済み自己親コード／別コード／空）・欠落・階層／業務文脈変更時は全件停止する。元33SQL適用済みの候補コードは許可。FK状態読取は旧remarkを参照しない。既存FKへのapply拒否を維持。
- `services/routing_parent_validation.py` に直上親検証を共通化し、APIと `RoutingStep.clean()`（inline／単独管理画面のModelFormから呼ばれる）へ適用。NULL／自己親／最上位／final／既存親工程欠落の例外を維持。
- `scripts/routing_parent_ai_views_definer.sql.txt` をGit対象の正式SQL原本として保存。全 `*.sql` を除外する既存.gitignoreは変更せず、`output/routing_parent_ai_views_definer.sql` は副本として保持。正式原本と副本の本文一致をファイル比較で確認。拡張子に依存せず、対象DBを選択してSQL本文をAdminerへ貼付するか、mysqlクライアントの入力として渡す。実行前の他ビュー旧remark参照・実アカウント確認は従来手順どおり。
- 追加検証: 承認対象の自己親登録済みコード／空／別登録済みコード変更、欠落、階層変更、既補正値許容、FK点検の旧値無参照、両admin ModelFormで不一致拒否と正常／NULL／自己親／欠落例外許可、正式原本の現行2ビュー／新列GRANT／旧列REVOKEを確認。最新のSQLite試験55件（親品22＋AI32＋受注中間工程1）は全件OK。実DBDDLの試行を避け、正規CLIのSQLite設定とdefaultだけを使う。
- MySQL実DDL、本番権限、SQL／Excel実往復、ブラウザ操作、既存受注全体の回帰未合格は未確認事項として維持。DB／コミット／push未反映。

## 独立再検証1回目の判定（2026-10-12）

evaluatorの総合判定は**条件付き**。初回の3指摘はすべて解消し、コード準備を確認。実DB移行・公開の完了判定ではない。

- 指定4ラベルのSQLite試験55件と、以前の失敗経路を確認する独立probe3件は成功。承認行の登録済み自己親コード／空への変更、工程欠落を全件停止し、管理画面の不一致保存を拒否する。
- 正式SQL原本はGit非除外、副本と全文一致。両ビュー定義はai0051と一致し、新列GRANT／旧列REVOKEを確認。差分形式チェック成功。
- フロントbuildとモデル／migration定義確認は成功。既存受注展開全体はHEADと同じ6件失敗が残り、全体回帰は未合格。
- 未確認はMySQL実DDL、実DB全件移行、本番DEFINER・列権限、他ビューの旧remark参照、ブラウザ操作、SQL／Excel実往復、全同期・全受注パターン。対象DB・実アカウントと参照影響を確認してから権限切替を行う。
- BOM新版保護・対象ルーティング選択はBOSS指示で保留。今回の変更で解決した扱いにしない。DB更新、migrate、コミット、push、本番反映は未実施。

初回独立評価の追加probeでは接続対象指定を誤り、ai_readerの`test_pm_db`へCREATE DATABASEを1回試行し、1044権限エラーで直ちに拒否された。ローカルDjango処理とログの確認によりDROP・再CREATE・テーブル作成・データ更新は未到達と確認。BOSSへ説明済み。1回目再検証のprobeはDATABASESをSQLiteメモリのdefaultだけへ限定し、`aliases={'default'}`を明示して実DB・ai_readerへ接続していない。


## 開発環境の実移行結果（2026-10-12）

BOSSの「ここは開発です　本番も移行したい」により、開発移行と本番移行の準備を実施。本番は接続設定未取得のため未着手。上記の未実施記述はコード準備時点の履歴であり、現在の開発状態は本節を正とする。コードはローカルコミット `4dbe2ad5b7cac1258e847974d3de8cbe58f5ae60` に保存済み。pushは未実施。

- 開発対象は `localhost / pm_db`。事前にmasters0087とai0051が適用済みで、親品IDは全7,612工程で未設定だった。新画面の親製品欄が空だった原因は、schema／表示切替に対してデータ移行が未実施だったこと。
- 開発Djangoを停止し、全工程テーブルのバックアップを `output/dev_routing_step_before_parent_id_20261012_164956.sql` に保存。SHA256は `d0a47b42d94552f0efd111695d7c274026fd4a5b29dea087fc220aefabc0c7c3`。
- 専用移行コマンドのapplyを1回実行してcommit完了。後続のログファイル保存は権限エラーで失敗したため、applyを再実行せず、バックアップ・対応表・独立読取照合で結果を確認した。旧remarkは保持。
- 他ビューが旧remarkを参照していないことと実アカウントを確認。既存ビュー／owner権限を `output/dev_parent_view_owner_before_20261012_165727.json` に保存し、正式SQLの4文（新列GRANT、2ビューDEFINER設定、旧列REVOKE）を開発のみへ適用。
- 独立evaluator判定は開発データ移行・AIビュー切替について合格。工程7,612件すべて親品ID設定、NULL／参照切れ0件。承認36工程の候補・文脈・旧remark保持は全一致。その他の登録済旧品番、新FK、元BOM親子、実在直上親の不一致は0件。既存例外3工程の親品と階層は維持。
- AI工程7,612件／材料6,380件は元テーブルと一致し、公開列33／20と順序を保持。FKの現在コードとの不一致0件。指定ownerのDEFINER、新列SELECTあり／旧remark SELECTなし、開発AI readerの両ビューSELECT成功。
- 開発Djangoを非表示で再起動し、`http://localhost:8081/admin/login/` がHTTP200で応答することを確認。ブラウザでの手動入力は未確認。
- 本番は10.0.1.232との資料記載のみ確認。SSH／DBの既存接続設定、本番コード・schema・実データ・権限は未確認。接続設定をBOSSへ照会済み。開発のProduct IDを本番へ転用せず、本番の現状照合・バックアップ・保守停止の後に移行する。

BOM新版保護、全受注回帰の既存失敗、SQL／Excel往復の未確認は従来どおり残る。本節の合格は開発データ移行とAIビュー切替に限定する。


### 本番の接続方法（2026-10-12追記）

BOSSより本番操作はAdminerとの指定。URLとログイン状態を照会中。読取専用の事前確認SQLを `output/ルーティング親品ID移行/checks/production_routing_parent_adminer_precheck.sql.txt` に準備した。本番のschema、migration履歴、実データ、ビューownerを確認するまで更新SQLは実行しない。AdminerによるDB操作に加え、新API／UIの配備状態と更新処理の保守停止も別途確認する。本番DBの確認・更新・移行完了判定はいずれも未実施。


### 本番Adminerの読取確認結果と実施条件（2026-10-12）

BOSS指定URL `http://10.0.1.232:8082/?server=mysql&username=root&db=pm_db` を開き、BOSSによるログイン後にSELECT／SHOWのみ実行。選択DBはpm_db、DB hostnameは27cbe67a474e、MySQL8.0.44。工程は7,612件、空の旧remarkは0件、品番マスタに存在しない旧親品を持つ工程は36件。これらは事前照合時点の読取結果で、適用時の固定件数条件ではない。

- masters0086／ai0050適用済み、masters0087／ai0051未適用。parent_product_id列は存在しない。m_product.idはsigned bigint、移行関連6表はInnoDB。
- 両AIビューのDEFINERはpm_ai_view_owner@localhost、SQL SECURITY DEFINER。ownerは工程remark列のSELECTを保持。remarkを読むv_ai_shipmentは出荷テーブル側の権限であり、工程remark列権限取消の影響はビュー本文を改めて確認する。
- BOSSは「現在本番運用中」「SQL実行していい」と回答。SQL実行の許可は取得済みだが、親品ID対応アプリの配備状態、更新処理の停止、切替実施時間は未確認。これらを照会し、運用中は読み取り照合だけ実施する。
- plannerのAdminer案は、バックアップ → 列・索引・FK追加 → 全件照合付きデータ更新 → 2ビュー切替 → 実DDLとDjango migration履歴の整合確認。DDLとデータ更新を一括トランザクション扱いにしない。データ更新では旧remarkを保持し、updated_atのON UPDATE自動変更への対応を明示する。
- CLIと同等の全件ガード／ロック／失敗時rollbackをSQLで満たす場合、一時routine等の実装が必要となる。これはまだ提案段階で、routine作成・履歴直接登録を実施した扱いにしない。具体的なSQLは独立評価の後に使用する。

本番のデータ更新、DDL、GRANT／REVOKE、migration履歴登録、push、アプリ配備はいずれも未実施。読取照合の成功を本番移行完了と扱わない。


### 本番全件読取照合（2026-10-12）

`output/ルーティング親品ID移行/checks/production_parent_readonly_context_check.sql.txt`（全件集約と36候補）およびコンパクト版を作成。独立evaluatorは静的評価合格と判定。承認JSON全36行の全9属性、先頭空白、既存専用コマンドの初回防御条件を照合した。SELECTのみで、工程の新FK列は参照しない。コンパクト版SHA256は `9cd713b51d0c98961a85ece303064ec61e6575748803d3e8cec24bbc3ec6b730`。

rootがコンパクト版のSELECTを本番Adminerで実行し、結果を確認した。actual_database=pm_db、total_steps=7,612、approved_count=36、approved_present_count=36、resolved_parent_count=7,612、元から任意親品0、error_count=0、error_step_count=0。承認文脈／候補解決／未承認親／未解決親／元BOM親子／実在直上親／承認材料／承認BOMの各エラー数はすべて0。本番SQL modeにNO_BACKSLASH_ESCAPESなしを確認。v_ai_shipmentはt_shipment_actual.remarkを読むため、工程remark列権限の取消対象とは別列である。

これは運用中の移行前照合であり、本番移行完了ではない。更新処理・スケジューラの停止、親品ID対応コードの配備状態、切替時間が未確認。BOSSへ実施可能時間と切替方法を質問済み。適用直前のバックアップとロック後再照合はまだ必要。ここまで本番へSELECT／SHOWだけを実行し、DDL・データ更新・権限変更・履歴登録・pushは未実施。


### 本番Adminer実移行SQLの準備（2026-10-12）

BOSSは「いまでもいい」「いいよ」「移行して」と指示し、SQLコマンド貼付またはインポート画面による実行方法を写真で指定。実行許可と現在の実施時間は取得済み。許可の再確認は不要。Adminerにログインできているが、アプリ／スケジューラの実停止と親品ID対応アプリ配備を操作する接続先は未取得。

planner案に従い、schema追加、schema実体条件付きDjango履歴、全件ガード付き移行routine、CALL、routine削除、AI ownerビュー、AI履歴、事後確認のSQLをoutputに準備。データroutineは6表をid順ロックし全36文脈と全工程を再照合、失敗rollback、parent_product_idだけ更新、旧remarkとupdated_atを保持し、更新数と全件の事後一致が成功してからcommitする。更新とDDLは別段階。

独立静的評価の総合判定は条件付き。SQL準備を確認したが、本番のバックアップ保存・実停止・対応アプリ配備・各段階のMySQL実行は未確認。事後確認へ材料ビュー親品コードの一致照合を追加し、再評価中。

工程テーブルのAdminer SQLエクスポートを保存方式で試みたが、ダウンロード完了通知が返らず、保存先・完全性を確認できていない。保存成功と扱わない。本番のDDL・データ更新・権限変更・履歴登録・コード配備・pushはここまで未実施。移行SQLは実行順と条件を満たして使用する準備資料であり、本番完了ではない。


Adminer用SQL副本9本を `output/production_parent_adminer/` に保存し、配布用 `output/production_parent_adminer_sql.zip` を作成。手順書は `output/ルーティング親品ID移行/documents/production_parent_migration_steps.txt`。1回目独立静的再検証は条件付き。材料ビュー親コード一致・owner/reader確認の追加、副本9本と原本のbytes一致、正式owner SQL本文一致、段階別の手順を確認。readerホストは実DB未確認のため候補扱いとし、実アカウントを確認して使用する。本番停止・バックアップ成功・対応コード配備・MySQL routine構文／Adminer parserの未確認は維持。本番更新はまだ開始していない。


### BOSSによる本番migration適用後の実DB確認（2026-10-12）

BOSSがbackend build/up後のmigration実行済みと報告。rootが本番AdminerのSELECTで再確認し、接続先pm_db/hostname27cbe67a474e、masters0087適用日時2026-10-12 20:15:19.498258、ai0051適用日時同20:15:19.739640を確認した（DB返却値）。工程7,612件、親品ID設定0件、NULL7,612件。列追加・AI migrationは適用済みだが既存親品データ移行は未実施。

両AIビューのDEFINERはroot@%へ変わっている。全件データ移行後に指定ownerへ戻し、新親品ID列SELECTと旧remark列SELECTの切替・reader照合が必要。既存SQLの01列追加／01bと06の履歴登録を再実行しない。実migration適用はBOSS操作であり、rootによる本番書込みではない。rootはSELECTのみ。バックアップ保存成功・データapply・owner切替・本番完了の独立確認はまだ未実施。


### 本番の既存データ移行後確認（2026-10-12）

BOSSがダンプ終了を報告後、本番コンテナで専用Djangoコマンド `migrate_routing_parent_products --apply` を実行。終行は日本語文字化けを含むが、工程7,612／移行7,612／エラー0／更新済みを報告。rootが本番Adminer SELECTで実結果を確認した。Adminer用routineは実行していない。

- 親品ID設定7,612、NULL0、参照切れ0。旧品番からの承認補正を含む新FK現在コード不一致0、元BOM親子0、実在直上親0。
- 承認36工程の全9文脈属性・旧remark・新親品コードを一覧で照合し一致。材料親工程不足0、親子BOM不足0。例外13525／17314の親と階層、16629の階層10と親を維持。
- AI工程7,612、材料6,380は元テーブルと一致。公開列数33／20、両ビュー親品コードとFK現在コードの不一致0。ただし定義者はmigration適用後のroot@%のまま。
- 本番の `updated_at` は全7,612工程で2026-10-12 20:36:11となった。MySQLのON UPDATE設定により、Django bulk_updateで親IDを書いた際に更新日時も変更された。SQL案のupdated_at自己代入による保持とは別の実経路であり、日時保持成功と扱わない。旧日時の復元は未実施。BOSSへ説明済み。
- rootがownerへ親品ID列SELECTを付与しようとした操作は自動承認レビューにより実行前に拒否。具体的権限承認をBOSSへ照会した結果「今回はデータ移行の確認までにする」と指定。owner GRANT／ビュー定義者変更／旧remark REVOKEはすべて本番未実行、今後の対象として保留。
- BOSSによるダンプ完了報告はあるが、root/evaluatorは保存ファイル自体・完全性を未確認。今回の事後確認結果は `output/production_parent_post_migration_review_20261012.json` に保存。独立評価者はDBへ独自接続せず、この証拠を評価する。

本番の親品IDデータ移行は反映済み。AI owner権限切替、実reader接続、ブラウザ手動操作、全機能回帰の未確認を全体完了扱いにしない。再applyは不要であり、既存FKが存在するため拒否される。新SQL案のschema／履歴追加も既に適用済みのため実行しない。

独立限定事後評価は条件付き。評価者は本番へ独自接続せず、rootのSELECT証拠から親品IDの集計整合を確認した。旧更新日時保持は未達、実バックアップと原値の独立比較・画面/API・readerは未確認、owner切替はBOSS指定で保留。本節の36文脈/材料/BOM追加結果はrootの読取確認であり、独立DB再確認と表現しない。今回の報告範囲はBOSS指定どおり本番データ移行の確認までとする。

## 独立レビュー指摘への最小修正（2026-10-13）

BOSSは「この最小修正で進める」と承認。対象は、画面追加の親品必須条件の復元と、登録済み親品のクリア拒否である。本番データの再移行、BOM明細更新、BOM同期全体の変更、モデル／管理画面のNULL許容変更は行わない。

- `RoutingMaster.vue`: 工程追加の無効条件を親品ID未選択へ戻す。既存欄保存は空・未登録コードを拒否し、選択品番のIDだけをPATCHする。
- `RoutingStepSerializer.validate`: 既存親品IDが非NULLの工程に明示的な `parent_product: null` を送った場合は400とする。BOM同期やリンク解除・旧BOM削除へ到達する前に拒否する。API新規作成時の任意親品、元からNULLの既存工程、親品省略PATCHは維持する。
- 回帰試験: 既存親品クリア拒否時の工程・BOM・材料・履歴不変、元NULL工程のNULL更新、親品省略PATCH、API新規作成の任意NULLを確認する。SQLiteメモリのdefaultだけを使い、実DB／ai_readerに接続しない。
- 運用: 階層移動で直上親を変える場合は階層と新親品を同じPATCHで更新する。SQL輸出の旧remarkは復旧材料として維持する。
- 指摘3の対応表制約と指摘4の旧SQL再実行禁止を本計画・本番手順へ明記する。JSONや旧SQL本体は変更しない。

コード修正は作業ツリーに保存済み。2026-10-13の独立評価は、今回承認済みのUI／API修正と文書の範囲で限定合格。SQLiteメモリdefault一つだけの独立試験25件すべて成功（PATCH／PUT拒否時の工程・BOM・明細・材料・履歴不変、NULL例外、親品省略更新、階層と親品の同時変更）。実DB／ai_reader接続なし。rootのフロントbuildは成功（749 modules、1m24s、既存chunkサイズ警告あり）。差分形式チェックも成功。ブラウザでの空入力操作、SQL／Excel往復、既存受注全体の回帰未合格は未確認として維持する。今回修正のコミット・push・本番アプリ反映は未実施で、新migrationとデータ再applyは不要。既に反映済みの本番親品IDを再移行しない。AI owner権限切替はBOSS指定どおり保留する。

## 管理画面の設定済み親品クリア拒否（2026-10-13追加承認）

BOSSは「管理画面はクリアできないようにして 変更はできる」と追加承認。前節の管理画面NULL許容維持は当時の修正範囲であり、この追加修正では設定済み親品の解除だけを拒否する。新規工程の親品必須化は行わない。

- `RoutingStep.clean()` は親品が空に変更された既存工程について、同じDBの保存済み工程の親品IDを照会する。保存済み親品が非NULLなら `parent_product` のフィールドエラーで拒否する。
- 別の非NULL親品への変更は既存の階層整合検証を維持して許可する。単独管理画面とルーティング内のinline ModelForm双方で適用する。APIの既存クリア拒否処理は変更しない。
- 元から親品NULLの工程は他項目編集を許可し、新規NULL工程も維持する。モデルFKのNULL可・PROTECT、BOM連携・同期処理、移行コマンドは変更しない。実DB更新・migrate・再移行は不要。
- 実装者と独立評価者のSQLiteメモリdefaultだけの試験はそれぞれ27件成功。両管理画面フォームの空拒否時の工程・BOM・明細・材料・履歴不変、正常な別親品への実保存、元NULL工程の他項目保存、新規NULL工程の保存を確認した。実DB／ai_reader接続なし。独立評価は今回承認された管理画面修正の範囲で限定合格。管理画面のブラウザ実操作と開発／本番への配備は未確認のまま維持する。
- 作業ツリーにコード・試験・仕様を保存。コミット・push・開発／本番アプリへの配備は未実施。管理画面のブラウザ実操作は未確認。前節のUI/API修正と本追加修正を本番へ反映するまで、配備済みコードの操作条件は変わらない。AI owner権限切替はBOSS指定どおり保留する。

## 移行資料の整理（2026-10-13）

BOSSの整理指示により、output直下の移行関連txt13本を output/ルーティング親品ID移行/ へ移動した。未使用の移行SQL案7本は archive_sql_do_not_run、保留中のAI owner案1本は pending_ai_owner、確認SQL4本は checks、手順書1本は documents に分類し、README.txtに現状と旧パスの扱いを記載。移動前後のSHA256一致を全13本で確認し、本文は保持した。JSON結果・バックアップ・Adminer副本とZIP・旧全ビューSQLは今回移動していない。SQL実行・DB更新・削除・コミット・pushなし。本番データ再移行不要、AI owner切替保留の状態は変更しない。

BOSSの追加指示により、整理ディレクトリを output/ルーティング親品ID移行/ に変更。開発・本番のJSON5本をresults、開発移行前バックアップSQLをbackups、未使用Adminer副本ディレクトリとZIPをarchive_sql_do_not_runへ集約した。移動した全ファイルのSHA256一致を確認し、README.txtを更新。前段の未移動記載はこの追加整理前の状態を示す。業務コード・DB・正式scripts・他のoutput資料は変更していない。

2026-10-13、BOSS指示により `output/ルーティング親品ID移行/archive_sql_do_not_run/`（未使用の移行SQL案7本、Adminer副本、配布ZIP）を削除した。results・backups・checks・documents・pending_ai_owner は残している。上記の archive_sql_do_not_run への言及は削除前の記録で、現存しない。業務コード・DB・scripts は変更していない。

## 2026-10-14 AIビュー定義者修復（今回の承認範囲）

BOSSが開発2ビューの定義者修復を承認し、本番用SQLの提供を指示した。以前の本番owner切替保留は当時の記録として保持する。今回は開発DBで実行し、本番ではSQLを準備する範囲で、本番DBへの実行は行わない。

- 主担当の開発DB確認・実行結果: 現在の両SHOW CREATE VIEWを退避し、SELECT本文、ALGORITHM、文字セット・照合順序、公開列と順序を保持したままDEFINERだけを `pm_ai_view_owner@localhost` へ変更。owner/readerのSHOW GRANTSは前後不変で、開発では追加GRANTなし。
- 主担当の実DB確認: AI readerで工程7,612件・材料6,380件、公開33列／20列の全列参照に成功し、元テーブル件数と一致。画面と同じ件数確認経路で工程7,612件・品番2,849件・合計10,461件の確認に成功。ここに記した件数は主担当のDB一次確認結果であり、generatorによる独立DB確認ではない。
- 本番提供用 `scripts/repair_routing_ai_view_definers.sql.txt`を準備。`pm_db`、ai0051/masters0087適用済み、親品ID移行済み、既存ownerと必要参照列権限の存在を事前確認する。親品ID列のSELECT付与と、0051と同じSELECT本文による2ビューのDEFINER再設定だけを行う。前後DEFINER・元テーブルとビュー件数・公開列確認を含む。
- 既存 `scripts/routing_parent_ai_views_definer.sql.txt` は旧remark SELECT取消を含む初期切替手順として保持する。今回の修復SQLはREVOKE、reader権限追加、業務データ再移行、migration履歴変更、owner作成を含まない。旧全ビューSQLも再実行しない。
- 独立評価は今回の開発修復・本番SQL提供範囲で合格。修復前退避と実DBの照合でDEFINER以外の定義・文字セット・照合順序・列順不変、元テーブル／ビュー／reader件数一致、全公開列参照、画面の件数確認成功を確認した。本番SQLのSELECT本文は正式原本と完全一致し、変更範囲も合格。権限不変の独立前後比較は修復前GRANT退避がないため未確認で、主担当の比較結果と区別する。
- 開発は反映済み。本番SQLの準備時点では未実行だったが、同日にBOSSから本番インポート実行結果を受領した。貼付結果で対象pm_db、masters0087／ai0051適用済み、ownerロック、2ビューの専用定義者への変更、工程7,612件・材料6,380件の元／ビュー一致、公開33列／20列の列順を確認。owner権限の前後差分はparent_product_idのSELECT追加だけで、remark権限は維持されている。これはBOSS提供の実行結果の照合であり、エージェントによる本番DB独立接続確認ではない。最終COUNTの接続ユーザーが結果にないため、本番アプリのai_reader経路とブラウザ再操作は未確認。コミット・pushは今回未実施。
2026-10-13、BOSS指示により開発DBの移行前バックアップSQL（`output/ルーティング親品ID移行/backups/`）を削除した。上記の backups への言及は削除前の記録で、現存しない。
