# PostgreSQL切替用SQL

切替当夜（2026-10-21 02:00〜04:00）と、その前のリハーサルで使う確認用SQL。
手順と合否基準は `仕様書/PostgreSQL切替当夜計画_20261021.md` を参照。

| ファイル | 実行先 | 内容 |
|---|---|---|
| `01_mysql_counts_generator.sql.txt` | MySQL | 全テーブルの件数を数えるSQLを生成する（生成後に実行） |
| `02_pg_counts.sql.txt` | PG | 全テーブルの件数（1文で完結） |
| `03_key_aggregates.sql.txt` | MySQL・PG 共通 | 主要テーブルの合計・最小・最大・NULL件数 |
| `04_pg_structure_checks.sql.txt` | PG | スキーマ配置・型・デフォルト・シーケンス・ビューの確認 |
| `05_pg_post_load_fix.sql.txt` | PG | 移行直後の後処理（public移動・json→jsonb・デフォルト付け直し）。**リハーサルで検証してから本番で使う** |

すべて読み取り専用（05を除く）。05はPGのみを変更する。MySQL側（旧本番・新PCのPM用MySQL）には書き込まない。
