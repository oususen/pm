# Codexレビュー依頼：AI用ビュー（品番・工程・ライン）と、AI分析の日付なし対応

依頼者：BOSS ／ 作成：Claude Code ／ 初版：2026-10-10、更新：2026-10-10（第2回の依頼）／ 状態：レビュー依頼（コードは変更しない）

## 第1回のレビュー（済み）
`v_ai_product` と列型の拡張（サイクルA）。結果は条件付き合格で、指摘3件（辞書の説明の断定、DECIMAL(18,3)の仕様書の記述、手順SQLのDB修飾）は対応済み。

## 第2回の依頼の範囲（コミット済みの変更）
`git show <hash>` で差分を確認してください。他の変更（結果の記録、変数の値の正規化、テンプレートの再利用など）は別の目的で、対象外です。

| コミット | 内容 |
|---|---|
| `73a9a643` | v_ai_product の追加、列型の拡張（A。第1回で確認済み）、**date_field の任意化（B）**、**AIへの指示文・画面・公開ビュー登録（C）** |
| `86c65bcf` | v_ai_process（工程）の追加（`ai/0035`） |
| `3050e89d` | v_ai_process の再検証の指摘を反映（文書のみ） |
| `757c84a4` | v_ai_line（ライン）の追加（`ai/0036`） |
| `6cf8cfb3` | 「個人の評価・順位付け・査定に使わない」規定の取り下げ、ログインIDの送信可（文言の削除。`chat_service.py` の案内文を含む） |
| `fe97e563` | 確認明細（14テーブル177列の公開判断）と、第1回の依頼書（文書のみ） |

## 守った決定事項（レビューの前提）
- 設計原則は `仕様書/AI用ビュー作成計画.md` §4.1 の1〜9番（1テーブル1ビュー、マスタ属性付与の結合のみ可、公開列はBOSSが決める、標準SQL、列の説明は仕様書で確認、定義者は `pm_ai_view_owner`）。
- 「AI分析は全ビューに日付列が必須」の規定は取り下げ（BOSS 2026-10-10）。日付なしビューは `date_field=None` と明示的に宣言し、期間で絞らず全行を取得する（宣言のないビューは `KeyError` で止まる。補完しない）。
- 小数は `DECIMAL(p,s)`（p 1〜38、s 0〜p、先頭ゼロの数字は拒否）。丸めず、桁が超えたら拒否。
- `analysis_guard_runtime.py` は変更しない（`WRAPPER_VERSION`）。上限値・フォールバックは新設しない。`SCREEN_SQL_TABLES`・`TERM_COLUMNS` は変更しない。
- 公開列：品番30列（当初32列で0034を作成し開発DBに適用済み。2026-10-10にBOSSが作成日・更新日を非公開にしていたため、0037で30列に修正）、工程9列（`is_outsource`は非公開）、ライン6列（`lead_time_days`・`use_direct_process`は非公開）。

## 特に見てほしい点
### B：date_field の任意化（最重要。取得・件数・日付の扱いに関わる）
1. `analysis_data_service.build_where` が、日付ありビューで変更前と完全に同じSQL・パラメータを返すか（1ページ目・2ページ目以降・承認時COUNT・実行時COUNT）。
2. 日付なしビューの取得（`ORDER BY id LIMIT` と `WHERE id > %s`）で、行の欠落・重複が起きないか。`id` が単調増加でない・NULL・重複する場合の挙動。
3. 承認時COUNTと実行時COUNTの照合、`approved_count_changed`・`refetch_mismatch`・`fetch_rows_exceeded` が、日付なしビューでも日付ありと同じ流れで働くか。日付ありと日付なしを同時に選んだときの合計の比較。
4. `validate_datasets` が、`date_field=None` のビューだけ、日付列の検査を外しているか。他に、日付に依存して壊れる箇所が残っていないか。
5. `analysis_worker_identity.py` が `analysis_data_service.py` などのソースのハッシュで版を決める。変更後のデプロイで、ワーカーの再起動以外の影響（保存済みテンプレートの再利用判定など）がないか。

### C：AIへの指示文・登録・画面
6. `ai_view_definition` が、日付あり既存ビューの出力を1文字も変えていないか（planning・consult・codegen の3経路）。日付なしを含むときだけ、codegen の末尾に `DATELESS_VIEW_RULE` が付くか。
7. 指示文の変更（`analysis_planning_service.py` の指示と conditions）で、日付ありビューの意味（期間で絞る・日付列を fields に含める）が保たれているか。コード生成の既存指示（期間は `period_from`・`period_to`）と、日付なしの追加指示が矛盾しないか（日付なしビューの日付の列で絞る分析は許す設計。期間の変数が使われなければ `parameters_unused` で拒否される。2026-10-10に指示文を見直し済み）。
8. `period_applied`（`count_target_rows` の応答に追加）が追加のみで、保存済みの preview との互換を壊さないか。画面（`AIAnalysis.vue`）の表示条件。

### v_ai_process・v_ai_line
9. マイグレーション `0035`・`0036` が標準SQLで、公開列と過不足なく一致するか。依存（`masters 0084`、`masters 0023`）。
10. 説明文（`sql_queries.py` の `TABLE_NOTES`、`analysis_data_service.py` の `description`）に、仕様書・BOSS説明で確認できない業務意味の断定がないか。特に `process_code` の `G`・`PURCHASE`（実際の工程ではなく、BOM・ルーティングで外作・購買を示すための工程）、`line_type` の4値、`is_active`（購買ラインは、ER図は「意図的に0」とするが、実データは1。説明には書かない）。
11. 手順SQL（計画書 §4.1の9番、§9.3、§14、§16）：`migrate` 直後の、列単位の `GRANT`、`DEFINER = pm_ai_view_owner@localhost` でのビュー再作成、`pm_ai_reader` の `GRANT`。標準SQLのマイグレーションと、MySQL固有の手順SQLの分離が妥当か。PostgreSQL移行後の読み替え（§9.3）。

### その他
12. `6cf8cfb3`：文言の削除だけで、個人別残業の集計などの動作に影響がないか。取り下げ漏れ（同じ趣旨の記述が他に残っていないか）。
13. `test_analysis_column_guide.py` の更新（「クボタ」の検査から、承認済みの `OTHER=クボタ納期調整` を除外）が、検査を弱めていないか。

## 未確認・未実施（レビュー対象外として扱ってよい）
- 実機のAI（Qwen・外部AI）での分析案・コード生成の再試験。
- DuckDBコンテナ内での `DECIMAL(p,s)` の取り込み確認（ローカルに duckdb なし）。
- テスト用DBを要する `ai.test_analysis_*`（consult・execution_flow・permissions・template_* など）の回帰。
- 本番への反映（本番は未反映。デプロイ時は `migrate` のあとに、権限付与と定義者の付け替えをBOSSが実行。ワーカーの再起動も必要）。
- 工程「801」（重複した「レーザ1」）の削除は保留中（`output/prod_delete_process_801.sql`。基幹システム用Excelへの影響を確認してから判断）。

## レビューの進め方
- 読み取りのみ。コードの変更、`migrate`、DBへの書き込み、コミット、pushはしない。
- DBの確認は `SELECT`・`SHOW` だけ。`python manage.py shell` を使う場合は `PYTHONUTF8=1` を付ける。開発DBには、`v_ai_product`・`v_ai_process`・`v_ai_line` が作成済み（定義者は `pm_ai_view_owner@localhost`）。
- 試験：`python manage.py test ai.test_analysis_line_view ai.test_analysis_process_view ai.test_analysis_product_view ai.test_analysis_dateless_view ai.test_analysis_execution ai.test_analysis_planning ai.test_analysis_column_guide ai.test_analysis_codegen ai.test_analysis_jobs ai.test_analysis_multi_period ai.test_analysis_period_warning ai.test_analysis_worker_version`（DBを作らない `SimpleTestCase`。263件OK・skipped=4）、`pm-ui/scripts/test-analysis-*.mjs` 7本（fail 0）。テスト用DBを作る・消す試験は実行しない。
- 指摘は、重大度（高・中・低）、`path:line`、再現手順または根拠つきで。推測は推測と明記する。

## 第2回のレビュー結果（2026-10-10。条件付き合格）
| # | 重大度 | 指摘 | 対応 |
|---|---|---|---|
| 1 | 中 | 日付なしビューへの期間条件（`created_at BETWEEN {{period_from}} AND {{period_to}}` など）を、生成物の検査で拒否できない。取得時COUNTは全行なので、分析側の絞り込みを検出しない。「矛盾しても必ず`parameters_unused`で拒否される」という説明は成立しない | BOSS判断により、検査は追加せず、指示文を直した（日付なしビューの日付の列で絞る分析は正しい分析として許す。期間の変数が使われなければ`parameters_unused`で拒否されるが、日付の列で絞るSQLは拒否されない）。対応済み。実機のAI再試験は未実施 |
| 2 | 中 | 工程・ラインの本番用手順SQLが不足（品番の§9.3に相当するSQLがない） | 対応済み：計画書 §14.1・§16.1 に追記 |
| 3 | 低 | ログインIDの送信規定が、同じ節内で矛盾（表は「送らない」、111行は「送ってよい」） | 対応済み：規約の表を「氏名そのものは送らない。ログインIDは、送ってよい」に統一 |
| 4 | 低 | 取り下げた個人評価・順位付け禁止が、公開HTML（社内AIチャット_作業手順書.html）に残存 | 対応済み：該当項目を削除 |

確認できた範囲（Codex）：日付ありのWHERE・パラメータは従来と同じ。日付なしも承認件数・実行件数・混在時の合計上限・再取得照合の流れを共有。公開列（32・9・6列）とマイグレーション依存は妥当。既存ビューの定義出力、旧previewとの互換、ワーカー版と保存済みコードのハッシュの分離も確認。`6cf8cfb3`の動作変更は見当たらない。試験は、バックエンド263件成功・4件スキップ、フロント7本・202件成功。
