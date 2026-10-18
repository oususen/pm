# AIビュー作成 統括セッション 引継ぎ

作成日: 2026-10-18。作成元: 実績系AIビュー作成セッション（本セッションは実績系の統括であり、ビュー作成全体の統括ではない）。

## 役割

このセッションは、複数のカテゴリ別セッション（実績系・計画在庫進度系・今後増える他カテゴリ）を横断して把握し、以下を行う:

1. 各カテゴリセッションの進捗・計画・実装状況を把握する
2. カテゴリをまたいで共有されるファイル（`sql_queries.py`等）の衝突・整合性を見る
3. `仕様書/AI用ビュー作成計画.md`（全カテゴリ共通のガバナンス文書）のセクション番号・記録の一貫性を保つ
4. 新しいカテゴリセッションを立ち上げる際の引継ぎ文を作る
5. 必要に応じてBOSSへ、カテゴリ横断の状況をまとめて報告する

このセッション自体は、個別のビュー実装（planner/generator/evaluatorサイクル）を主導する場ではない。各カテゴリセッションがそれを行う。

## ガバナンスの原則（全カテゴリ共通、`仕様書/AI用ビュー作成計画.md`冒頭を参照）

- 1テーブル1ビュー。マスタビューを実績・計画系ビューより先に作る
- 列の公開可否はBOSSが決定する。AIは全列を一覧化し、公開/非公開の案を示すだけ
- 将来のPostgreSQL移行を見据え、SQLはバッククォート・`DEFINER`・`SQL SECURITY`・DB修飾なしの標準SQLのみで書く（`JSON_EXTRACT`/`JSON_UNQUOTE`等MySQL固有のJSON関数は使ってよいが、PostgreSQL移行時の書き換えが必要な旨をコメントに明記する）
- 推測禁止。列の型・NULL率・分布等は必ずDBに直接確認してから計画・実装する
- 進め方は planner（読み取り専用で計画） → BOSS承認 → generator（実装） → evaluator（独立検証） → BOSS報告 → コミット（BOSSの指示）の順。`migrate`・本番反映はBOSSが実行する

## 現在の反映状況（2026-10-18時点）

### 開発DBに存在する22ビュー（`SHOW FULL TABLES WHERE Table_type='VIEW'`で確認）
`v_ai_bom_item` `v_ai_brake_interruption` `v_ai_brake_production_actual`(※13列のまま、下記注意) `v_ai_calendar_day` `v_ai_customer` `v_ai_department` `v_ai_equipment` `v_ai_laser_interruption` `v_ai_laser_production_actual` `v_ai_leader_unit` `v_ai_line` `v_ai_process` `v_ai_process_production_actual` `v_ai_product` `v_ai_purchase_receipt` `v_ai_routing_step` `v_ai_routing_step_material` `v_ai_shipment` `v_ai_supervisor_team` `v_ai_supplier` `v_ai_unit_line` `v_ai_user`

### 未反映（マイグレーション未適用）
- `v_ai_process_interruption`（`ai/0061`、コミット済み`1122ded1`、BOSSの`migrate`待ち）
- `v_ai_brake_production_actual`の16列化（`ai/0059`、コミット済み`c32f6513`。`ai/0057`で作成済みの13列版は反映済みだが、3列追加分`0059`が未適用のため、現在DB上は13列のまま）

### 本番DB
2026-10-12時点で16ビュー反映済み（過去の記録）。実績系7ビュー（§32〜§38）はいずれも本番未反映。本番への反映はBOSSが別途実施。

### `仕様書/AI用ビュー作成計画.md`のセクション構成
§1〜§19: 初期フェーズの各種マスタビュー・基盤整備
§20: `setup_ai_views`管理コマンドの設計
§21〜§22: 得意先マスタ `v_ai_customer`
§23: AI分析の検証失敗理由コード（ビュー作成とは別件、AI分析基盤の話）
§24: 稼働カレンダ `v_ai_calendar_day`
§25: BOM明細 `v_ai_bom_item`
§26: ルーティング `v_ai_routing_step` / `v_ai_routing_step_material`
§27: ユーザー・部署 `v_ai_user` / `v_ai_department`
§28: グループ・ライン紐付 `v_ai_unit_line`
§29: 班長・リーダー担当 `v_ai_supervisor_team` / `v_ai_leader_unit`
§30: 工程とBOM明細の連産品判定規則の説明文改善
§31: ルーティング親品ID化
**§32〜§38: 実績系（本セッションが担当・完了）**
- §32 設備マスタ `v_ai_equipment`
- §33 一般工程生産実績 `v_ai_process_production_actual`
- §34 レーザー生産実績 `v_ai_laser_production_actual`
- §35 ブレーキ・スポット生産実績 `v_ai_brake_production_actual`
- §36 レーザー中断 `v_ai_laser_interruption`
- §37 ブレーキ・スポット中断 `v_ai_brake_interruption`
- §38 一般工程中断 `v_ai_process_interruption`

**次は§39以降を、新しいカテゴリ（計画・在庫・進度系）が使う想定。** 新カテゴリ着手前に、この統括セッションが最新のセクション番号を確認し、重複しないよう採番すること。

## マイグレーション番号の状態（`ai`アプリ）
最新は`0061_ai_process_interruption_view.py`。次の新規マイグレーションは`0062`から。**複数セッションが並行作業する場合、番号の奪い合い・依存関係の分岐が起きる**（実績系作業中に実際に発生した。下記「教訓」参照）。新カテゴリセッション開始時は、着手の都度`ls pm_backend/apps/ai/migrations/`で最新番号を確認すること。

## 実績系セッションで得られた教訓（全カテゴリに有効、必ず共有すること）

1. **JSON型の列をAI分析実行用に公開してはいけない**: `analysis_execution_service.py`の`_cell()`関数（DuckDB投入用CSV変換）がJSON型に対応しておらず、JSON型の列をそのまま公開列にすると、AI分析実行時に100%失敗する。JSON由来の情報を出したい場合は、`JSON_UNQUOTE(JSON_EXTRACT(...))`でSQL側にテキスト化してから公開する（`v_ai_process_interruption`の`interruption_reason`列がこの方式の実例）。

2. **適用済みのマイグレーションファイルを直接書き換えてはいけない**: `v_ai_brake_production_actual`で、既に`migrate`適用済みのマイグレーションファイルのSELECT文を直接書き換える対応をしてしまい、Djangoが再実行しないため開発DBのビュー定義と実際のコードが乖離する不整合バグが発生した（コミット`c32f6513`で修正）。列を追加・変更する場合は、必ず新しいマイグレーションファイルを作成し、`CREATE OR REPLACE VIEW`を再発行すること。

3. **BOSSが決めた列リストは、必ず実テーブルの`SHOW COLUMNS`と突き合わせること**: アーティファクトでBOSSが決定した時点の列リストが、実テーブルの最新列構成と食い違っていることが複数回あった（新しく追加された列がリストに無い等）。実装前に必ず実テーブルの全列を確認し、差分があればBOSSに追加確認すること。

4. **複数セッションが同じ作業ディレクトリ(`D:\pm`)を共有する**: 共有ファイル（`sql_queries.py`・`analysis_data_service.py`・`analysis_execution_service.py`・`setup_ai_views.py`・`test_setup_ai_views.py`）は、複数カテゴリの変更が同時に混在することがある。**コミット時は、`git add`で自分のタスクに関係するファイルだけを明示的に指定し、`git add -A`や無差別な一括コミットをしないこと**。他セッションの未完成・未評価の変更を誤ってコミットする事故を防ぐため。

5. **マイグレーションの依存関係に複数のleafができることがある**: 並行して複数の新規マイグレーションが作られると、依存関係グラフが枝分かれし`makemigrations --check`が`Conflicting migrations`エラーを出す。後から追加するマイグレーションの`dependencies`に、両方のleafを含めることで解消できる（実績系で実際に発生し対応済み）。

6. **設備との紐付けが弱いデータがある**: 一般工程の中断セッション(`t_process_work_session`)は、設備との結合カバレッジが約6.7%と低く、BOSSの判断で非公開とした経緯がある。ブレーキ・レーザーは比較的設備情報が充実している。カテゴリ・テーブルごとに設備・個人情報等の充実度にばらつきがあるので、都度実データで確認すること。

7. **列の公開判断ツールはアーティファクト（claude.ai）で行う**: 実績系では「実績ビュー公開判断」というアーティファクト（`https://claude.ai/artifact/9xtdpGnQPFYwvpTvvoAzoY`）を使い、BOSSが列ごとに公開/非公開をタップで選ぶUIを用意した。新カテゴリでも同じ方式（新しいアーティファクトを作る）を踏襲するとよい。元になった「マスタビュー公開判断」アーティファクトも参考にできる。

## 次のアクション（BOSSへの提案）

1. この統括セッションが、計画・在庫・進度系セッションの立ち上げ引継ぎ文を作成する（対象テーブルの選定はBOSSと相談しながら進める）
2. §39以降のセクション番号を計画・在庫・進度系に割り当てる
3. 実績系7ビューの本番反映（`migrate`・`setup_ai_views --apply`・コミットのpush）は、BOSSのタイミングで別途実施

### 対応状況（2026-10-18、本統括セッションが対応）

- 項目1・2を完了。対象テーブルはBOSSが「中核3テーブル（`LineBacklog`・`LineDemand`・`LinePlan`）+ 調整値（`LineBacklogAdjustment`）」の4テーブルに決定。引継ぎ文を`仕様書/AIビュー作成_計画在庫進度系セッション引継ぎ.md`に作成し、`仕様書/AI用ビュー作成計画.md`に§39見出しを予約した（実装内容はまだ無い。実装は新しいカテゴリセッションが行う）。
- 項目3は未対応（BOSSのタイミングで別途実施、変更なし）。
