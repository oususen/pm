ルーティング親品ID移行資料（2026-10-13整理）

本番はDjango migrationと専用コマンドで移行済み。このフォルダは準備・確認の記録です。
SQLを順番に実行するための配布セットではありません。

（archive_sql_do_not_run/ は2026-10-13にBOSS指示で削除済み。未使用の移行SQL案とAdminer副本・ZIPで、本番では使用していない。）

pending_ai_owner/
  05_owner_viewsのSQL案1本。AI owner権限切替はBOSS指定で保留中です。
  正式原本は D:/pm/scripts/routing_parent_ai_views_definer.sql.txt。

checks/
  SELECTによる確認SQL4本。
  事前確認SQLは移行前を前提とするため、移行後の判定にはそのまま使わないでください。
  07_postcheckも準備時点の案です。現在の状況は手順書と実装計画を参照してください。

documents/
  production_parent_migration_steps.txt：移行経緯、現状、準備時点の手順。
  本文のoutput直下の旧パスは整理前の記録です。現在の場所はこの案内の分類に従います。

results/
  開発・本番の移行結果と事前確認・ビュー情報のJSON5本。

（backups/ は2026-10-13にBOSS指示で削除済み。開発DBの移行前バックアップSQL。）
