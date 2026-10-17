"""ブレーキ・板金スポットの中断のビュー v_ai_brake_interruption の登録を検証する。

偽のDB接続・定義の検査だけを使う試験(SimpleTestCase)と、開発DBへ読み取りだけを行う件数照合試験(DBCountMatchTest)を分ける。
本ビューは`brake_line_record`単独(結合なし)だが、WHERE句で絞り込むため`SIMPLE_MASTER_VIEWS`ではなく`EXISTING_JOIN_VIEWS`で扱う
(既存の`v_ai_laser_interruption`・`v_ai_process_production_actual`と同じ扱い)。
件数照合は、`migrate`未実行(本ビュー未作成)の間は、元テーブルの直接件数だけを計算し、
ビュー自体へのSELECTは `information_schema.VIEWS` でビューの存在を確認してから行う(存在しなければ明示してスキップする)。
"""
import re
from pathlib import Path

from django.test import SimpleTestCase

from ai.management.commands import setup_ai_views as cmd
from ai.services import analysis_execution_service as service
from ai.services.analysis_data_service import ANALYSIS_VIEWS, ai_view_definition, build_where, validate_datasets
from ai.services.analysis_plan_store import AnalysisError
from ai.services.sql_queries import BASE_SQL_SCHEMA, TABLE_NOTES

VIEW = 'v_ai_brake_interruption'
PERIOD = ('2026-09-01', '2026-09-30')
# BOSSが決定した公開15列。順序はマイグレーションのSELECT順と同じ(AI用ビュー作成計画。sequence_noは含めない)。
PUBLISHED = (
    'id', 'plan_date', 'product_code', 'operator_action', 'operator_action_reason', 'qty',
    'recorded_at', 'equipment_id', 'line_id', 'process_id', 'product_id', 'operator_user_id',
    'operator_login_id', 'interruption_reason_code', 'remarks',
)
# 非公開(ビューに含めない): operator(個人名)のみ
HIDDEN = ('operator',)
MIGRATION = Path(__file__).parent / 'migrations' / '0060_ai_brake_interruption_view.py'


def migration_sql():
    return MIGRATION.read_text(encoding='utf-8').split('CREATE_VIEW = """')[1].split('"""')[0]


def migration_columns():
    body = re.search(r'SELECT(.*)FROM', migration_sql(), re.S).group(1)
    return [c.strip() for c in body.split(',') if c.strip()]


class BrakeInterruptionViewDefinitionTest(SimpleTestCase):
    def test_view_is_registered_with_plan_date_and_qty(self):
        definition = ANALYSIS_VIEWS[VIEW]
        self.assertEqual(definition['date_field'], 'plan_date')
        self.assertEqual(definition['quantity_field'], 'qty')
        self.assertEqual(definition['label'], 'ブレーキ・スポット中断')

    def test_column_types_match_published_columns_exactly(self):
        self.assertEqual(BASE_SQL_SCHEMA[VIEW], PUBLISHED)
        self.assertEqual(len(PUBLISHED), 15)
        self.assertEqual(set(service.ANALYSIS_COLUMN_TYPES[VIEW]), set(BASE_SQL_SCHEMA[VIEW]))
        self.assertEqual(service.ANALYSIS_COLUMN_TYPES[VIEW], {
            'id': 'BIGINT', 'plan_date': 'DATE', 'product_code': 'VARCHAR', 'operator_action': 'VARCHAR',
            'operator_action_reason': 'VARCHAR', 'qty': 'BIGINT', 'recorded_at': 'TIMESTAMP',
            'equipment_id': 'BIGINT', 'line_id': 'BIGINT', 'process_id': 'BIGINT', 'product_id': 'BIGINT',
            'operator_user_id': 'BIGINT', 'operator_login_id': 'VARCHAR', 'interruption_reason_code': 'VARCHAR',
            'remarks': 'VARCHAR',
        })
        # JSON型の列が混入していないこと(分析実行の値変換が未対応のため実行が失敗する再発防止)
        self.assertNotIn('JSON', service.ANALYSIS_COLUMN_TYPES[VIEW].values())

    def test_hidden_columns_do_not_appear_anywhere(self):
        columns = migration_columns()
        sql = migration_sql()
        for hidden in HIDDEN:
            # operatorは、operator_action等の公開列名の接頭辞と重なるため、単語境界つきの正規表現で判定する
            # (単純な部分文字列一致だと、公開列の文中に誤検出してしまう)
            self.assertNotIn(hidden, columns)
            self.assertNotIn(hidden, BASE_SQL_SCHEMA[VIEW])
            self.assertNotIn(hidden, service.ANALYSIS_COLUMN_TYPES[VIEW])
            self.assertNotRegex(TABLE_NOTES[VIEW], rf'\b{hidden}\b')
            self.assertNotRegex(ANALYSIS_VIEWS[VIEW]['description'], rf'\b{hidden}\b')
            self.assertNotRegex(sql, rf'\b{hidden}\b')

    def test_sequence_no_is_not_published(self):
        # BOSS決定: 中断ビューではsequence_noを含めない
        self.assertNotIn('sequence_no', BASE_SQL_SCHEMA[VIEW])
        self.assertNotIn('sequence_no', migration_columns())

    def test_ai_definition_has_date_and_quantity_field(self):
        definition = ai_view_definition(VIEW)
        self.assertEqual(set(definition), {'label', 'date_field', 'quantity_field', 'description'})
        self.assertNotIn(None, definition.values())

    def test_validate_datasets_requires_plan_date_and_rejects_hidden_columns(self):
        datasets = [{'view': VIEW, 'fields': ['id', 'plan_date', 'qty']}]
        self.assertEqual(validate_datasets(datasets, *PERIOD), datasets)
        with self.assertRaises(AnalysisError):
            validate_datasets([{'view': VIEW, 'fields': ['id', 'qty']}], *PERIOD)
        for hidden in HIDDEN:
            with self.assertRaises(AnalysisError):
                validate_datasets([{'view': VIEW, 'fields': ['plan_date', hidden]}], *PERIOD)

    def test_build_where_filters_by_plan_date(self):
        self.assertEqual(
            build_where(VIEW, *PERIOD),
            (' WHERE `plan_date` >= %s AND `plan_date` <= %s', list(PERIOD)))
        self.assertEqual(
            build_where(VIEW, *PERIOD, last_id=9),
            (' WHERE `plan_date` >= %s AND `plan_date` <= %s AND `id` > %s', [*PERIOD, 9]))

    def test_description_has_required_notes(self):
        for text in (ANALYSIS_VIEWS[VIEW]['description'], TABLE_NOTES[VIEW]):
            for part in (
                    'operator_action', 'PAUSE', 'TEMP_END', 'qty', 'line_id', 'operator_action_reason',
                    'operator_user_id', 'operator_login_id', 'interruption_reason_code', 'remarks'):
                self.assertIn(part, text)
            for hidden in HIDDEN:
                # operatorは公開列名(operator_action等)の接頭辞と重なるため単語境界つきの正規表現で判定する
                self.assertNotRegex(text, rf'\b{hidden}\b')
        # line_idでブレーキ(9・L0010)とスポット(10・L0013)が混在する旨
        self.assertIn('9', TABLE_NOTES[VIEW])
        self.assertIn('L0010', TABLE_NOTES[VIEW])
        self.assertIn('L0013', TABLE_NOTES[VIEW])
        # qtyはTEMP_ENDでは常に0、PAUSEでは値がある場合とない場合がある旨
        self.assertIn('0', TABLE_NOTES[VIEW])
        # plan_dateとrecorded_at-8hの不一致率(このサブセット固有の値)
        self.assertIn('recorded_at', TABLE_NOTES[VIEW])
        self.assertIn('1.1', TABLE_NOTES[VIEW])
        # 367件(PAUSE 306・TEMP_END 61)である旨
        self.assertIn('367', TABLE_NOTES[VIEW])

    def test_setup_command_treats_this_view_as_not_simple(self):
        self.assertIn(VIEW, cmd.EXISTING_JOIN_VIEWS)
        self.assertNotIn(VIEW, cmd.SIMPLE_MASTER_VIEWS)

    def test_migration_sql_has_no_mysql_specific_definer_syntax(self):
        sql = migration_sql()
        for banned in ('`', 'DEFINER', 'SQL SECURITY', 'pm_db'):
            self.assertNotIn(banned, sql)
        self.assertIn('CREATE OR REPLACE VIEW v_ai_brake_interruption AS', sql)
        self.assertIn('FROM brake_line_record', sql)
        self.assertEqual(sql.count('WHERE'), 1)
        self.assertIn("operator_action IN ('PAUSE', 'TEMP_END')", sql)
        for column in PUBLISHED:
            self.assertIn(f'    {column}', sql)

    def test_migration_sql_has_no_join(self):
        sql = migration_sql()
        self.assertNotIn('JOIN', sql)

    def test_migration_columns_match_base_sql_schema_order(self):
        columns = migration_columns()
        self.assertEqual(tuple(columns), PUBLISHED)
        self.assertEqual(len(columns), 15)

    def test_migration_dependencies(self):
        source = MIGRATION.read_text(encoding='utf-8')
        self.assertIn("('ai', '0059_ai_brake_production_actual_view_add_columns')", source)
        self.assertIn("DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_brake_interruption'", source)

    def test_existing_view_definitions_in_migrations_are_unchanged(self):
        # 既存ビューのマイグレーション(0001〜0059)に、このビューが混入していない
        for path in (Path(__file__).parent / 'migrations').glob('00[0-5]*.py'):
            if path.name == '0060_ai_brake_interruption_view.py':
                continue
            self.assertNotIn(VIEW, path.read_text(encoding='utf-8'), path.name)


class BrakeInterruptionDBCountMatchTest(SimpleTestCase):
    """開発DBの実データで、ビューの件数と独立計算した期待件数が一致することを確認する(検証項目A)。"""

    def test_view_count_matches_independent_count(self):
        connection = service.open_snapshot_connection(service.Deadline(30, 'stage_deadline_fetch'), read_timeout=30)
        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.VIEWS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s", (VIEW,))
            view_exists = cursor.fetchone()[0] > 0
            cursor.execute(
                "SELECT COUNT(*) FROM brake_line_record WHERE operator_action IN ('PAUSE', 'TEMP_END')")
            expected = cursor.fetchone()[0]
            if not view_exists:
                self.skipTest(
                    f'v_ai_brake_interruption は未作成(migrate未実行)のため件数照合をスキップ。'
                    f'独立計算の期待件数={expected}(2026-10-18 generator確認時点)。migrate実行後に本試験で照合する。')
            cursor.execute(f'SELECT COUNT(*) FROM `{VIEW}`')
            actual = cursor.fetchone()[0]
            cursor.close()
        finally:
            connection.close()
        self.assertEqual(actual, expected)

    def test_action_breakdown_matches_db(self):
        """operator_action別の件数(PAUSE・TEMP_END)を実データで検証する。"""
        connection = service.open_snapshot_connection(service.Deadline(30, 'stage_deadline_fetch'), read_timeout=30)
        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT "
                "SUM(CASE WHEN operator_action = 'PAUSE' THEN 1 ELSE 0 END), "
                "SUM(CASE WHEN operator_action = 'TEMP_END' THEN 1 ELSE 0 END), "
                "COUNT(*) "
                "FROM brake_line_record WHERE operator_action IN ('PAUSE', 'TEMP_END')")
            pause, temp_end, total = cursor.fetchone()
            cursor.close()
        finally:
            connection.close()
        # 2026-10-18 generator確認時点の開発DB実データ
        self.assertEqual(total, 367)
        self.assertEqual(pause, 306)
        self.assertEqual(temp_end, 61)

    def test_qty_breakdown_matches_db(self):
        """qtyの分布(TEMP_ENDは常に0、PAUSEは値がある場合とない場合がある)を実データで検証する。"""
        connection = service.open_snapshot_connection(service.Deadline(30, 'stage_deadline_fetch'), read_timeout=30)
        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT "
                "SUM(CASE WHEN operator_action = 'TEMP_END' AND qty <> 0 THEN 1 ELSE 0 END), "
                "SUM(CASE WHEN operator_action = 'PAUSE' AND qty = 0 THEN 1 ELSE 0 END), "
                "SUM(CASE WHEN operator_action = 'PAUSE' AND qty <> 0 THEN 1 ELSE 0 END) "
                "FROM brake_line_record WHERE operator_action IN ('PAUSE', 'TEMP_END')")
            temp_end_nonzero, pause_zero, pause_nonzero = cursor.fetchone()
            cursor.close()
        finally:
            connection.close()
        # 2026-10-18 generator確認時点の開発DB実データ
        self.assertEqual(temp_end_nonzero, 0)
        self.assertEqual(pause_zero, 98)
        self.assertEqual(pause_nonzero, 208)
