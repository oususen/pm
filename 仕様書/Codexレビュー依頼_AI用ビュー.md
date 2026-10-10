# Codexレビュー依頼：AI用ビュー（v_ai_product）と列型の拡張

依頼者：BOSS ／ 作成：Claude Code ／ 日付：2026-10-10 ／ 状態：レビュー依頼（コードは変更しない）

## 依頼の範囲

作業ツリーの未コミット変更のうち、次の2つだけをレビューしてください。他の変更（結果の記録、残業、ログインID等）は別の目的です。

### 1. 品番ビュー `v_ai_product`（実装済み・検証は条件付き）
- `pm_backend/apps/ai/migrations/0034_ai_product_view.py`
- `pm_backend/apps/ai/services/sql_queries.py`（`BASE_SQL_SCHEMA`・`TABLE_NOTES` の `v_ai_product` の追加分）
- 仕様書：`AI用ビュー作成計画.md` §4.1・§9・§9.3、`AI運用規約・AI用DB辞書.md` §6.5-4、`AIマスタビュー確認明細.md`

### 2. 列型の拡張（サイクルA。検証は条件付き合格）
- `pm_backend/apps/ai/services/analysis_execution_service.py`（`parse_decimal_type`・`_decimal_cell`・`_cell`）
- `analysis-sandbox/job/job_main.py`（`is_allowed_column_type`・`validate_header`）
- 試験：`pm_backend/apps/ai/test_analysis_execution.py`（追加3件）、`analysis-sandbox/tests/test_column_types.py`（新規）
- 仕様書：`AI分析基盤仕様書.md` §8、`AI用ビュー作成計画.md` §10

## 守った決定事項（レビューの前提）

- 1テーブル1ビュー。結合なし・WHEREなし・別名なし（`v_ai_product`）。公開32列、非公開は `image_url`・`product_name_halfwidth`・`is_phantom`・`self_lt_days`。
- 「AI分析は全ビューに日付列が必須」の規定は取り下げ（BOSS 2026-10-10）。ただし日付なしビューの取得（サイクルB・C）は未実装。
- 小数は `DECIMAL(p,s)`（p 1〜38、s 0〜p）を許可。丸めず、桁が超えたら拒否。
- `analysis_guard_runtime.py` は変更しない（`WRAPPER_VERSION` のため）。
- 上限値・フォールバックは新設しない。日時は `datetime.now()`。コメントは日本語。

## 特に見てほしい点

1. `_cell` / `_decimal_cell` の境界。`Decimal('0E+5')`、`1E+2`、負数、`-0.00`、先頭ゼロ、小数桁0、p=38、`adjusted()` による整数部の桁数の数え方。
2. `DECIMAL(18,3)` の挙動変更：小数4桁以上と整数部15桁超を、以前は通し、今回は拒否する。実データ（出荷542行・入荷2,872行）では影響なしを確認済み。妥当か。
3. `job_main.py`：型名がそのまま `CREATE TABLE` に入る。検査をすり抜ける経路がないか。`DECIMAL(018,03)`（先頭ゼロ）を許してよいか（DuckDBが受け付けるか未確認）。
4. `v_ai_product` の32列が、マイグレーション・`BASE_SQL_SCHEMA`・承認した列と一致するか。`masters 0085` への依存が妥当か。
5. `ai_home` の許可は `BASE_SQL_SCHEMA` の全キーから作られるため、`v_ai_product` が自動で入る。チャットSQLの許可範囲への影響。
6. `TABLE_NOTES` の列の説明が、仕様書にある意味と食い違っていないか。仕様書にない意味を断定していないか（`AI用ビュー作成計画.md` §4.1-1 参照）。
7. 手順SQL（§9.3：列単位の `GRANT`、`DEFINER = pm_ai_view_owner@localhost` でのビュー再作成、`pm_ai_reader` の `GRANT`）の正しさ。開発DBの `pm_ai_reader` は DB 全体に `SELECT` を持つため、「元テーブルの直接参照が拒否される」確認は開発では成立しない。

## 未確認・未実施（レビュー対象外として扱ってよい）

- DuckDB コンテナ内での `DECIMAL(p,s)` の取り込み確認（ローカルに duckdb なし）。
- `v_ai_product` は開発DBに未作成（`migrate`・権限付与はBOSSが実行）。
- `ANALYSIS_VIEWS`・`ANALYSIS_COLUMN_TYPES`・`SCREEN_SQL_TABLES` への `v_ai_product` 登録（サイクルCで実施予定）。
- 本番への反映。

## レビューの進め方

- 読み取りのみ。コードの変更、`migrate`、DBへの書き込み、コミット、pushはしない。
- DBの確認は `SELECT`・`SHOW` だけ。`python manage.py shell` を使う場合は `PYTHONUTF8=1` を付ける。
- 試験：`python manage.py test ai.test_analysis_execution`（DBを作らない `SimpleTestCase`）、`python -m unittest discover -s analysis-sandbox/tests -p test_column_types.py`。
- 指摘は、重大度（高・中・低）、`path:line`、再現手順または根拠つきで。推測は推測と明記する。
