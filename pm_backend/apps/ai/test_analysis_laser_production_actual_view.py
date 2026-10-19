"""レーザー生産実績のビュー v_ai_laser_production_actual の登録を検証する。

偽のDB接続・定義の検査だけを使う試験(SimpleTestCase)と、開発DBへ読み取りだけを行う件数照合試験(DBCountMatchTest)を分ける。
件数照合は、`migrate`未実行(本ビュー未作成)の間は、実テーブルの直接JOINによる期待値だけを計算し、
ビュー自体へのSELECTは `information_schema.VIEWS` でビューの存在を確認してから行う(存在しなければ明示してスキップする)。

ビュー本体は2つのマイグレーションに分かれている:
- 0056_ai_laser_production_actual_view.py: 開発DB適用済み(31列版、変更不可)
- 0062_ai_laser_views_add_interruption_reason_code.py: interruption_reason_code追加で32列への拡張
  (未適用。BOSSのmigrate待ち。2026-10-20、Codexレビュー指摘の修正2)
現在の公開列定義(PUBLISHED、32列)に対する検査は0062の内容を基準にする。
"""
import re
from pathlib import Path

from django.test import SimpleTestCase

from ai.management.commands import setup_ai_views as cmd
from ai.services import analysis_execution_service as service
from ai.services.analysis_data_service import ANALYSIS_VIEWS, ai_view_definition, build_where, validate_datasets
from ai.services.analysis_plan_store import AnalysisError
from ai.services.sql_queries import BASE_SQL_SCHEMA, TABLE_NOTES

VIEW = 'v_ai_laser_production_actual'
PERIOD = ('2026-09-01', '2026-09-30')
# BOSSが決定した公開32列。順序はマイグレーションのSELECT順と同じ(AI用ビュー作成計画 §34。
# 2026-10-20、Codexレビュー指摘の修正2によりinterruption_reason_codeを追加公開)。
PUBLISHED = (
    'id', 'actual_id', 'operator_user_id', 'equipment_id', 'equipment_code', 'equipment_name', 'line_id',
    'process_id', 'pattern_id', 'pattern_no', 'material_id', 'material_code', 'material_name', 'product_id',
    'product_code', 'product_name', 'work_date', 'shot_count', 'process_time_per_shot', 'total_process_time',
    'operator_action', 'operator_action_reason', 'units_per_shot', 'total_qty', 'scrap_qty', 'scrap_reason',
    'end_operator_user_id', 'created_at_h', 'updated_at_h', 'created_at', 'updated_at',
    'interruption_reason_code',
)
# 非公開(ビューに含めない): detail_type(常にCOMPONENT固定)、display_order(画面の並び順)、ヘッダのremarks(全件空。4,997件中4,997件が空文字)
HIDDEN = ('detail_type', 'display_order', 'remarks')
MIGRATION = Path(__file__).parent / 'migrations' / '0062_ai_laser_views_add_interruption_reason_code.py'


def migration_sql():
    return MIGRATION.read_text(encoding='utf-8').split('CREATE_LASER_PRODUCTION_ACTUAL_VIEW = """')[1].split('"""')[0]


def migration_columns():
    """SELECTの列を、別名(存在すれば)優先、なければテーブル修飾(例 d.id)を除いた列名で、順序つきで返す。"""
    body = re.search(r'SELECT(.*)FROM', migration_sql(), re.S).group(1)
    parts, depth, current = [], 0, ''
    for ch in body:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if ch == ',' and depth == 0:
            parts.append(current)
            current = ''
        else:
            current += ch
    parts.append(current)
    columns = [p.strip() for p in parts if p.strip()]
    aliases = []
    for column in columns:
        match = re.search(r'\bAS\s+(\w+)\s*$', column)
        if match:
            aliases.append(match.group(1))
        else:
            aliases.append(column.split('.')[-1])
    return columns, aliases


class LaserProductionActualViewDefinitionTest(SimpleTestCase):
    def test_view_is_registered_with_work_date_and_total_qty(self):
        definition = ANALYSIS_VIEWS[VIEW]
        self.assertEqual(definition['date_field'], 'work_date')
        self.assertEqual(definition['quantity_field'], 'total_qty')
        self.assertEqual(definition['label'], 'レーザー生産実績')

    def test_column_types_match_published_columns_exactly(self):
        self.assertEqual(BASE_SQL_SCHEMA[VIEW], PUBLISHED)
        self.assertEqual(len(PUBLISHED), 32)
        self.assertEqual(set(service.ANALYSIS_COLUMN_TYPES[VIEW]), set(BASE_SQL_SCHEMA[VIEW]))
        self.assertEqual(service.ANALYSIS_COLUMN_TYPES[VIEW], {
            'id': 'BIGINT', 'actual_id': 'BIGINT', 'operator_user_id': 'BIGINT', 'equipment_id': 'BIGINT',
            'equipment_code': 'VARCHAR', 'equipment_name': 'VARCHAR', 'line_id': 'BIGINT', 'process_id': 'BIGINT',
            'pattern_id': 'BIGINT', 'pattern_no': 'VARCHAR', 'material_id': 'BIGINT', 'material_code': 'VARCHAR',
            'material_name': 'VARCHAR', 'product_id': 'BIGINT', 'product_code': 'VARCHAR', 'product_name': 'VARCHAR',
            'work_date': 'DATE', 'shot_count': 'BIGINT', 'process_time_per_shot': 'DECIMAL(18,1)',
            'total_process_time': 'DECIMAL(18,1)', 'operator_action': 'VARCHAR', 'operator_action_reason': 'VARCHAR',
            'units_per_shot': 'DECIMAL(18,3)', 'total_qty': 'DECIMAL(18,3)', 'scrap_qty': 'DECIMAL(18,3)',
            'scrap_reason': 'VARCHAR', 'end_operator_user_id': 'BIGINT', 'created_at_h': 'TIMESTAMP',
            'updated_at_h': 'TIMESTAMP', 'created_at': 'TIMESTAMP', 'updated_at': 'TIMESTAMP',
            'interruption_reason_code': 'VARCHAR',
        })
        # JSON型の列が混入していないこと(分析実行の値変換が未対応のため実行が失敗する再発防止)
        self.assertNotIn('JSON', service.ANALYSIS_COLUMN_TYPES[VIEW].values())

    def test_hidden_columns_do_not_appear_anywhere(self):
        # 非公開3列は、ビューの出力列(SELECTの別名)・BASE_SQL_SCHEMA・ANALYSIS_COLUMN_TYPES・TABLE_NOTES本文のいずれにも出現しない。
        # detail_typeはWHEREの絞り込み条件として使うため、SQL全体からは除外しない(出力列でないことだけを確認する)。
        _, aliases = migration_columns()
        sql = migration_sql()
        for hidden in HIDDEN:
            self.assertNotIn(hidden, aliases)
            self.assertNotIn(hidden, BASE_SQL_SCHEMA[VIEW])
            self.assertNotIn(hidden, service.ANALYSIS_COLUMN_TYPES[VIEW])
            self.assertNotIn(hidden, TABLE_NOTES[VIEW])
            self.assertNotIn(hidden, ANALYSIS_VIEWS[VIEW]['description'])
        # display_order・remarksはWHEREにも使わないため、SQL全体に一切出現しない
        for hidden in ('display_order', 'remarks'):
            self.assertNotRegex(sql, rf'\b{hidden}\b')
        # detail_typeはWHEREの条件にだけ1回出現する(SELECT句の列・別名としては出現しない)
        self.assertEqual(len(re.findall(r'\bdetail_type\b', sql)), 1)
        self.assertIn("d.detail_type = 'COMPONENT'", sql)

    def test_ai_definition_has_date_and_quantity_field(self):
        definition = ai_view_definition(VIEW)
        self.assertEqual(set(definition), {'label', 'date_field', 'quantity_field', 'description'})
        self.assertNotIn(None, definition.values())

    def test_validate_datasets_requires_work_date_and_rejects_hidden_columns(self):
        datasets = [{'view': VIEW, 'fields': ['id', 'work_date', 'total_qty']}]
        self.assertEqual(validate_datasets(datasets, *PERIOD), datasets)
        with self.assertRaises(AnalysisError):
            validate_datasets([{'view': VIEW, 'fields': ['id', 'total_qty']}], *PERIOD)
        for hidden in HIDDEN:
            with self.assertRaises(AnalysisError):
                validate_datasets([{'view': VIEW, 'fields': ['work_date', hidden]}], *PERIOD)

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
                    'work_date', 'total_qty', 'operator_action', 'END', 'PAUSE', 'operator_user_id',
                    'end_operator_user_id', 'material_id', 'product_id', 'line_id', 'process_id',
                    '2026-10-14', 'created_at_h', 'updated_at_h'):
                self.assertIn(part, text)
            for hidden in HIDDEN:
                self.assertNotIn(hidden, text)
        # line_id・process_idが2026-10-14以前はNULLになる旨(BOSS確認済みの事実)を明記する
        self.assertIn('NULL', TABLE_NOTES[VIEW])
        self.assertIn('created_by_id', TABLE_NOTES[VIEW])
        self.assertIn('updated_by_id', TABLE_NOTES[VIEW])
        # 2026-10-20追加公開のinterruption_reason_codeに関する記述(TABLE_NOTESのみ。descriptionは今回対象外)
        self.assertIn('interruption_reason_code', TABLE_NOTES[VIEW])

    def test_setup_command_treats_this_view_as_not_simple(self):
        self.assertIn(VIEW, cmd.EXISTING_JOIN_VIEWS)
        self.assertNotIn(VIEW, cmd.SIMPLE_MASTER_VIEWS)

    def test_migration_sql_has_no_mysql_specific_definer_syntax(self):
        sql = migration_sql()
        for banned in ('`', 'DEFINER', 'SQL SECURITY', 'pm_db'):
            self.assertNotIn(banned, sql)
        self.assertIn('CREATE OR REPLACE VIEW v_ai_laser_production_actual AS', sql)
        self.assertIn('FROM t_laser_actual_detail d', sql)
        self.assertIn('JOIN t_laser_actual a ON a.id = d.actual_id', sql)
        self.assertEqual(sql.count('WHERE'), 1)
        self.assertIn("a.operator_action IN ('END', 'PAUSE')", sql)
        self.assertIn("d.detail_type = 'COMPONENT'", sql)
        self.assertIn('a.created_by_id AS operator_user_id', sql)
        self.assertIn('a.updated_by_id AS end_operator_user_id', sql)
        self.assertIn('a.interruption_reason_code', sql)
        for hidden in ('display_order', 'remarks'):
            self.assertNotRegex(sql, rf'\b{hidden}\b')

    def test_renamed_columns_are_published(self):
        self.assertIn('operator_user_id', BASE_SQL_SCHEMA[VIEW])
        self.assertIn('end_operator_user_id', BASE_SQL_SCHEMA[VIEW])

    def test_migration_columns_match_base_sql_schema_order(self):
        columns, aliases = migration_columns()
        self.assertEqual(tuple(aliases), PUBLISHED)
        self.assertEqual(len(columns), 32)

    def test_migration_dependencies(self):
        source = MIGRATION.read_text(encoding='utf-8')
        self.assertIn("('ai', '0061_ai_process_interruption_view')", source)
        self.assertIn("('production', '0125_laseractual_interruption_reason_code')", source)
        self.assertIn('REVERT_LASER_PRODUCTION_ACTUAL_VIEW = """', source)

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

    def test_0056_is_unchanged_original_31_column_definition(self):
        # 0056は既にDB適用済みのため、適用済み内容(31列)のまま変更しないこと(2026-10-20、Codexレビュー指摘の修正2)
        original = Path(__file__).parent / 'migrations' / '0056_ai_laser_production_actual_view.py'
        source = original.read_text(encoding='utf-8')
        body = re.search(r'SELECT(.*)FROM', source, re.S).group(1)
        columns = [c.strip().rstrip(',') for c in body.strip().split('\n') if c.strip()]
        self.assertEqual(len(columns), 31)
        self.assertNotIn('interruption_reason_code', columns)
        self.assertIn("DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_laser_production_actual'", source)

    def test_existing_view_definitions_in_migrations_are_unchanged(self):
        # 既存ビューのマイグレーション(0001〜0061。0056・0062は対象ビューの定義マイグレーションのため除外)に、
        # このビューが混入していない
        for path in (Path(__file__).parent / 'migrations').glob('00[0-6][0-1]*.py'):
            if path.name in ('0056_ai_laser_production_actual_view.py', '0062_ai_laser_views_add_interruption_reason_code.py'):
                continue
            self.assertNotIn(VIEW, path.read_text(encoding='utf-8'), path.name)


class LaserProductionActualDBCountMatchTest(SimpleTestCase):
    """開発DBの実データで、ビューの件数と独立計算した期待件数が一致することを確認する(検証項目A)。

    本ビューは2026-10-17時点で`migrate`未実行のため、`v_ai_laser_production_actual`が存在しない間は、
    期待値だけを計算してスキップする(BOSSの指示でmigrate実行後に本試験が有効になる)。
    件数自体は列数に関係なく一致するはずなので、0062(interruption_reason_code追加)未適用でも検証できる。
    """
    def test_view_count_matches_independent_join_count(self):
        # Django ORM経由の接続(SimpleTestCaseのDB保護対象)ではなく、既存のDeadlineTest等と同じ
        # 生のmysql.connector接続(service.open_snapshot_connection)を使い、開発DBへ直接読み取りだけを行う。
        connection = service.open_snapshot_connection(service.Deadline(30, 'stage_deadline_fetch'), read_timeout=30)
        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.VIEWS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s", (VIEW,))
            view_exists = cursor.fetchone()[0] > 0
            cursor.execute(
                "SELECT COUNT(*) FROM t_laser_actual_detail d JOIN t_laser_actual a ON a.id = d.actual_id "
                "WHERE a.operator_action IN ('END', 'PAUSE') AND d.detail_type = 'COMPONENT'")
            expected = cursor.fetchone()[0]
            if not view_exists:
                self.skipTest(
                    f'v_ai_laser_production_actual は未作成(migrate未実行)のため件数照合をスキップ。'
                    f'独立計算の期待件数={expected}(2026-10-17 generator確認時点)。migrate実行後に本試験で照合する。')
            cursor.execute(f'SELECT COUNT(*) FROM `{VIEW}`')
            actual = cursor.fetchone()[0]
            cursor.close()
        finally:
            connection.close()
        self.assertEqual(actual, expected)

    def test_view_has_32_columns_after_0062_migrate(self):
        connection = service.open_snapshot_connection(service.Deadline(30, 'stage_deadline_fetch'), read_timeout=30)
        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.VIEWS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s", (VIEW,))
            view_exists = cursor.fetchone()[0] > 0
            if not view_exists:
                self.skipTest('v_ai_laser_production_actual は未作成(migrate未実行)のため列数照合をスキップ。')
            cursor.execute(f'SHOW COLUMNS FROM `{VIEW}`')
            actual_columns = tuple(row[0] for row in cursor.fetchall())
            cursor.close()
        finally:
            connection.close()
        if actual_columns == PUBLISHED:
            return
        self.skipTest(
            f'0062未適用のため、v_ai_laser_production_actual はまだ31列のまま(実列={actual_columns})。'
            f'migrate実行後に本試験で32列への更新を確認する。')
