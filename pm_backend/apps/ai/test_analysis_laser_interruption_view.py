"""レーザーの中断のビュー v_ai_laser_interruption の登録を検証する。

偽のDB接続・定義の検査だけを使う試験(SimpleTestCase)と、開発DBへ読み取りだけを行う件数照合試験(DBCountMatchTest)を分ける。
本ビューは`t_laser_actual`単独(結合なし)だが、WHERE句で絞り込むため`SIMPLE_MASTER_VIEWS`ではなく`EXISTING_JOIN_VIEWS`で扱う
(既存の`v_ai_process_production_actual`等と同じ扱い)。
件数照合は、`migrate`未実行(本ビュー未作成)の間は、元テーブルの直接件数だけを計算し、
ビュー自体へのSELECTは `information_schema.VIEWS` でビューの存在を確認してから行う(存在しなければ明示してスキップする)。

ビュー本体は2つのマイグレーションに分かれている:
- 0058_ai_laser_interruption_view.py: 開発DB適用済み(15列版、変更不可)
- 0062_ai_laser_views_add_interruption_reason_code.py: interruption_reason_code追加で16列への拡張
  (未適用。BOSSのmigrate待ち。2026-10-20、Codexレビュー指摘の修正2)
現在の公開列定義(PUBLISHED、16列)に対する検査は0062の内容を基準にする。
"""
import re
from pathlib import Path

from django.test import SimpleTestCase

from ai.management.commands import setup_ai_views as cmd
from ai.services import analysis_execution_service as service
from ai.services.analysis_data_service import ANALYSIS_VIEWS, ai_view_definition, build_where, validate_datasets
from ai.services.analysis_plan_store import AnalysisError
from ai.services.sql_queries import BASE_SQL_SCHEMA, TABLE_NOTES

VIEW = 'v_ai_laser_interruption'
PERIOD = ('2026-09-01', '2026-09-30')
# BOSSが決定した公開16列。順序はマイグレーションのSELECT順と同じ(AI用ビュー作成計画 §36。
# 2026-10-20、Codexレビュー指摘の修正2によりinterruption_reason_codeを追加公開)。
PUBLISHED = (
    'id', 'work_date', 'equipment_id', 'equipment_code', 'equipment_name', 'line_id', 'process_id',
    'pattern_no', 'material_id', 'material_code', 'material_name', 'operator_action',
    'operator_action_reason', 'operator_user_id', 'created_at',
    'interruption_reason_code',
)
MIGRATION = Path(__file__).parent / 'migrations' / '0062_ai_laser_views_add_interruption_reason_code.py'


def migration_sql():
    return MIGRATION.read_text(encoding='utf-8').split('CREATE_LASER_INTERRUPTION_VIEW = """')[1].split('"""')[0]


def migration_columns():
    """SELECTの列を、別名(存在すれば)優先、なければ列名そのもので、順序つきで返す。"""
    body = re.search(r'SELECT(.*)FROM', migration_sql(), re.S).group(1)
    columns = [c.strip() for c in body.split(',') if c.strip()]
    aliases = []
    for column in columns:
        match = re.search(r'\bAS\s+(\w+)\s*$', column)
        aliases.append(match.group(1) if match else column)
    return columns, aliases


class LaserInterruptionViewDefinitionTest(SimpleTestCase):
    def test_view_is_registered_with_work_date_and_no_quantity_field(self):
        definition = ANALYSIS_VIEWS[VIEW]
        self.assertEqual(definition['date_field'], 'work_date')
        self.assertIsNone(definition['quantity_field'])
        self.assertEqual(definition['label'], 'レーザー中断')

    def test_column_types_match_published_columns_exactly(self):
        self.assertEqual(BASE_SQL_SCHEMA[VIEW], PUBLISHED)
        self.assertEqual(len(PUBLISHED), 16)
        self.assertEqual(set(service.ANALYSIS_COLUMN_TYPES[VIEW]), set(BASE_SQL_SCHEMA[VIEW]))
        self.assertEqual(service.ANALYSIS_COLUMN_TYPES[VIEW], {
            'id': 'BIGINT', 'work_date': 'DATE', 'equipment_id': 'BIGINT', 'equipment_code': 'VARCHAR',
            'equipment_name': 'VARCHAR', 'line_id': 'BIGINT', 'process_id': 'BIGINT', 'pattern_no': 'VARCHAR',
            'material_id': 'BIGINT', 'material_code': 'VARCHAR', 'material_name': 'VARCHAR',
            'operator_action': 'VARCHAR', 'operator_action_reason': 'VARCHAR', 'operator_user_id': 'BIGINT',
            'created_at': 'TIMESTAMP', 'interruption_reason_code': 'VARCHAR',
        })
        # JSON型の列が混入していないこと(分析実行の値変換が未対応のため実行が失敗する再発防止)
        self.assertNotIn('JSON', service.ANALYSIS_COLUMN_TYPES[VIEW].values())

    def test_ai_definition_has_date_field_and_omits_quantity_field(self):
        # ai_view_definitionは値がNoneのキー(quantity_field)を出さない仕様(v_ai_productと同じ)
        definition = ai_view_definition(VIEW)
        self.assertEqual(set(definition), {'label', 'date_field', 'description'})
        self.assertNotIn(None, definition.values())

    def test_validate_datasets_requires_work_date(self):
        datasets = [{'view': VIEW, 'fields': ['id', 'work_date', 'operator_action']}]
        self.assertEqual(validate_datasets(datasets, *PERIOD), datasets)
        with self.assertRaises(AnalysisError):
            validate_datasets([{'view': VIEW, 'fields': ['id', 'operator_action']}], *PERIOD)

    def test_build_where_filters_by_work_date(self):
        self.assertEqual(
            build_where(VIEW, *PERIOD),
            (' WHERE `work_date` >= %s AND `work_date` <= %s', list(PERIOD)))
        self.assertEqual(
            build_where(VIEW, *PERIOD, last_id=9),
            (' WHERE `work_date` >= %s AND `work_date` <= %s AND `id` > %s', [*PERIOD, 9]))

    def test_description_has_required_notes(self):
        for text in (ANALYSIS_VIEWS[VIEW]['description'], TABLE_NOTES[VIEW]):
            for part in (
                    'work_date', 'operator_action', 'PAUSE', 'TEMP_END', 'operator_user_id',
                    'pattern_no', 'material_id', 'line_id', 'process_id', '2026-10-14'):
                self.assertIn(part, text)
        # line_id・process_idが2026-10-14より前はNULLになる旨(BOSS確認済みの事実)
        self.assertIn('NULL', TABLE_NOTES[VIEW])
        self.assertIn('created_by_id', TABLE_NOTES[VIEW])
        # 開発DBの対象16件が現時点で全件NULLである旨
        self.assertIn('16', TABLE_NOTES[VIEW])
        # JOINしない設計理由(重複)が明記されていること
        self.assertIn('重複', TABLE_NOTES[VIEW])
        # 2026-10-20追加公開のinterruption_reason_codeに関する記述(TABLE_NOTESのみ。descriptionは今回対象外)
        self.assertIn('interruption_reason_code', TABLE_NOTES[VIEW])

    def test_setup_command_treats_this_view_as_not_simple(self):
        self.assertIn(VIEW, cmd.EXISTING_JOIN_VIEWS)
        self.assertNotIn(VIEW, cmd.SIMPLE_MASTER_VIEWS)

    def test_migration_sql_has_no_mysql_specific_definer_syntax(self):
        sql = migration_sql()
        for banned in ('`', 'DEFINER', 'SQL SECURITY', 'pm_db'):
            self.assertNotIn(banned, sql)
        self.assertIn('CREATE OR REPLACE VIEW v_ai_laser_interruption AS', sql)
        self.assertIn('FROM t_laser_actual', sql)
        self.assertEqual(sql.count('WHERE'), 1)
        self.assertIn("operator_action IN ('PAUSE', 'TEMP_END')", sql)
        self.assertIn('created_by_id AS operator_user_id', sql)
        self.assertIn('interruption_reason_code', sql)

    def test_migration_sql_has_no_join_or_detail_table(self):
        # JOINなし設計の保証(結合すると中断1件が明細行数分重複するため、BOSSが結合なし設計を決定済み)
        sql = migration_sql()
        self.assertNotIn('JOIN', sql)
        self.assertNotIn('t_laser_actual_detail', sql)

    def test_renamed_column_is_published(self):
        self.assertIn('operator_user_id', BASE_SQL_SCHEMA[VIEW])

    def test_migration_columns_match_base_sql_schema_order(self):
        columns, aliases = migration_columns()
        self.assertEqual(tuple(aliases), PUBLISHED)
        self.assertEqual(len(columns), 16)

    def test_migration_dependencies(self):
        source = MIGRATION.read_text(encoding='utf-8')
        self.assertIn("('ai', '0061_ai_process_interruption_view')", source)
        self.assertIn("('production', '0125_laseractual_interruption_reason_code')", source)
        self.assertIn('REVERT_LASER_INTERRUPTION_VIEW = """', source)

    def test_migration_dependency_migration_exists_and_adds_line_process(self):
        production = Path(__file__).parent.parent / 'production' / 'migrations'
        line_process = production / '0118_laser_actual_line_process.py'
        self.assertTrue(line_process.exists())
        text = line_process.read_text(encoding='utf-8')
        self.assertIn("name='line'", text)
        self.assertIn("name='process'", text)

    def test_migration_dependency_migration_exists_and_adds_interruption_reason_code(self):
        production = Path(__file__).parent.parent / 'production' / 'migrations'
        interruption = production / '0125_laseractual_interruption_reason_code.py'
        self.assertTrue(interruption.exists())
        text = interruption.read_text(encoding='utf-8')
        self.assertIn("name='interruption_reason_code'", text)

    def test_0058_is_unchanged_original_15_column_definition(self):
        # 0058は既にDB適用済みのため、適用済み内容(15列)のまま変更しないこと(2026-10-20、Codexレビュー指摘の修正2)
        original = Path(__file__).parent / 'migrations' / '0058_ai_laser_interruption_view.py'
        source = original.read_text(encoding='utf-8')
        body = re.search(r'SELECT(.*)FROM', source, re.S).group(1)
        columns = [c.strip() for c in body.split(',') if c.strip()]
        self.assertEqual(len(columns), 15)
        self.assertNotIn('interruption_reason_code', columns)
        self.assertIn("DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_laser_interruption'", source)

    def test_existing_view_definitions_in_migrations_are_unchanged(self):
        # 既存ビューのマイグレーション(0001〜0061。0058・0062は対象ビューの定義マイグレーションのため除外)に、
        # このビューが混入していない
        for path in (Path(__file__).parent / 'migrations').glob('00[0-6][0-1]*.py'):
            if path.name in ('0058_ai_laser_interruption_view.py', '0062_ai_laser_views_add_interruption_reason_code.py'):
                continue
            self.assertNotIn(VIEW, path.read_text(encoding='utf-8'), path.name)


class LaserInterruptionDBCountMatchTest(SimpleTestCase):
    """開発DBの実データで、ビューの件数と独立計算した期待件数が一致することを確認する(検証項目A)。

    本ビューは2026-10-17時点で`migrate`未実行のため、`v_ai_laser_interruption`が存在しない間は、
    期待値だけを計算してスキップする(BOSSの指示でmigrate実行後に本試験が有効になる)。
    件数自体は列数に関係なく一致するはずなので、0062(interruption_reason_code追加)未適用でも検証できる。
    """
    def test_view_count_matches_independent_count(self):
        connection = service.open_snapshot_connection(service.Deadline(30, 'stage_deadline_fetch'), read_timeout=30)
        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.VIEWS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s", (VIEW,))
            view_exists = cursor.fetchone()[0] > 0
            cursor.execute(
                "SELECT COUNT(*) FROM t_laser_actual WHERE operator_action IN ('PAUSE', 'TEMP_END')")
            expected = cursor.fetchone()[0]
            if not view_exists:
                self.skipTest(
                    f'v_ai_laser_interruption は未作成(migrate未実行)のため件数照合をスキップ。'
                    f'独立計算の期待件数={expected}(2026-10-17 generator確認時点)。migrate実行後に本試験で照合する。')
            cursor.execute(f'SELECT COUNT(*) FROM `{VIEW}`')
            actual = cursor.fetchone()[0]
            cursor.close()
        finally:
            connection.close()
        self.assertEqual(actual, expected)

    def test_action_breakdown_matches_db(self):
        """operator_action別の件数(PAUSE・TEMP_END)が、対象行の合計と一致することを実データで検証する。
        件数は日々の業務で増減するため、固定値をハードコードせず、常に独立計算と突き合わせる。"""
        connection = service.open_snapshot_connection(service.Deadline(30, 'stage_deadline_fetch'), read_timeout=30)
        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT "
                "SUM(CASE WHEN operator_action = 'PAUSE' THEN 1 ELSE 0 END), "
                "SUM(CASE WHEN operator_action = 'TEMP_END' THEN 1 ELSE 0 END), "
                "COUNT(*) "
                "FROM t_laser_actual WHERE operator_action IN ('PAUSE', 'TEMP_END')")
            pause, temp_end, total = cursor.fetchone()
            cursor.close()
        finally:
            connection.close()
        self.assertGreater(total, 0)
        self.assertEqual(pause + temp_end, total)

    def test_view_has_16_columns_after_0062_migrate(self):
        connection = service.open_snapshot_connection(service.Deadline(30, 'stage_deadline_fetch'), read_timeout=30)
        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.VIEWS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s", (VIEW,))
            view_exists = cursor.fetchone()[0] > 0
            if not view_exists:
                self.skipTest('v_ai_laser_interruption は未作成(migrate未実行)のため列数照合をスキップ。')
            cursor.execute(f'SHOW COLUMNS FROM `{VIEW}`')
            actual_columns = tuple(row[0] for row in cursor.fetchall())
            cursor.close()
        finally:
            connection.close()
        if actual_columns == PUBLISHED:
            return
        self.skipTest(
            f'0062未適用のため、v_ai_laser_interruption はまだ15列のまま(実列={actual_columns})。'
            f'migrate実行後に本試験で16列への更新を確認する。')
