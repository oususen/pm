# ルーティング親品ID化実装計画

## 承認範囲・状況（2026-10-12）

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
- `RoutingMaster.vue`: POST/PATCHで親品IDを送信、IDで自己親・親工程を比較。表示の検索文字列を編集すると選択IDを解除し、非空未選択入力を拒否。空は任意NULLとして許可。
- `masters/management/commands/migrate_routing_parent_products.py`、`services/routing_parent_approved_mapping.json`: 全件移行の専用コマンドと承認済み36対応表。
- `ai/migrations/0051_routing_parent_product_views.py`、AI説明2箇所、`setup_ai_views.py`: 親品ID JOINで既存33／20公開列・順序・全行公開を維持。旧0042/0043の履歴定義は不変。
- `scripts/routing_parent_ai_views_definer.sql.txt`: 2ビューのowner新列SELECT、DEFINER再設定、旧remark列SELECT取り消し（未実行）。既存33修正SQL／本番全ビューSQLは変更しない。

## 既存データ移行の照合

調査記録は `output/routing_parent_migration_review.json`（2026-10-12 13:46の読取結果）と `output/routing_parent_migration_identity.json`（同13:58の36候補文脈照合）。調査時の件数を適用条件として固定しない。DBは並行操作で変わり得るため、適用直前の現在値を全件再照合する。

対応表は工程ID・ルーティングID／コード／完成品コード・加工後品ID／コード・旧親コード・階層・新親コードを保持する。本番の新親品IDは現在の品番コードから解決し、開発のProduct IDを転用しない。未登録値の補正は36承認候補に限定し、直上親工程・その材料・親子BOMの現存を確認する。既に旧33SQLで候補コードへ直された行も同じ文脈を照合する。元BOMがある行は親と子＝加工後品の両方を照合する。

未承認の未登録親品、文脈不一致、元BOM親子の不一致、実在直上親と非自己親の不一致が1件でもあれば一覧を出して全件中止。未確定行をNULL／ゼロで補完しない。元から親品未指定の行だけNULLを維持する。親品／階層不一致の旧誤抽出24行に階層修正を加えない。親工程欠落の既存例外13525／17314、既存階層10の16629は親品を維持し、工程追加／階層変更を行わない。

初回移行（全工程の親品IDが未設定）では、まず承認36全対象の存在・旧親コードが承認旧値または候補値であること・routing/output/階層/品番コードの文脈を必須照合する。承認対象の欠落、空変更、加工後品コード等の別登録済みコードへの変更も全件停止する。元33SQLで候補コードへ直された行は文脈・材料・BOMが一致すれば許可する。

コマンドは既定が読取照合。`--apply`時は全関連行を同一トランザクションでロックして現在値を照合し、全件成功時だけ親品IDを一括保存する。remarkは改変しない。既に親品IDが存在するDBへの適用は部分移行／切替後旧値上書きを防ぐため拒否する。既に親品IDが存在する状態の既定読取は「FK状態読取点検」モードと表示し、新FKの存在・現在コード・BOM／工程文脈を正として行う。NULLも正規値として扱い、旧remarkが残っていてもそこから親品を復元／移行候補へ追加しない。定期スケジュールや自動修復は追加しない。

## リリース手順（BOSS承認後に実施）

1. 対象DB・バックアップ／工程旧値一覧・新FK対応表を確認する。schema／データ／ビュー／API／UIを一体の切替として扱う。ルーティングや品番・BOMを更新する画面、バッチ、スケジューラを停止し、利用者操作を保守停止する。ロックだけで新規行追加・別クライアント操作を完全に防ぐものではない。
2. 新アプリを公開せず `masters 0087` までschema追加。現コードで専用コマンドを実行するための環境は準備するが、新API／UI／スケジューラを起動しない。通常 `migrate` 全体ではai0051も先行するため、段階を指定する。
3. `python manage.py migrate_routing_parent_products` で現在値と対象全件を照合し出力を保存。問題があれば旧方式のまま停止して原因を確認する。元CSVの33修正SQLとこの移行を同時並行適用しない。
4. BOSS承認後に同コマンド `--apply` でロック後の再照合と全件更新。工程数不変、対象36候補と全既存登録コードの新FK、未解決0、元BOM親子／実在直上親の整合を確認。新FK導入後は旧33SQLでremarkを書き換えても親品の業務修正にならない。
5. `ai 0051` で2ビュー切替。対象DBの実アカウントを確認し `scripts/routing_parent_ai_views_definer.sql.txt` でownerの新列SELECT、2ビューDEFINER設定、旧remark SELECT取り消し。他ビューがremarkを読む場合は取り消しを先行しない。owner／reader双方で公開列・行数・コード改名反映・NULL親品を確認する。MySQLのDDLはデータ更新トランザクションと一括rollbackできないため段階ごとに確認する。
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
