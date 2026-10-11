"""リーダーの担当グループのビュー v_ai_leader_unit の登録を検証する。

偽のDB接続・定義の検査だけを使い、開発DBへは接続しない(SimpleTestCaseのみ)。実データの確認は、別に開発DBで読み取りだけを行う。
"""
import hashlib
import json
import re
from pathlib import Path

from django.test import SimpleTestCase

from ai.management.commands import setup_ai_views as cmd
from ai.services import analysis_consult_service as consult
from ai.services import analysis_execution_service as service
from ai.services.analysis_data_service import ANALYSIS_VIEWS, ai_view_definition, build_where, validate_datasets
from ai.services.analysis_plan_store import AnalysisError
from ai.services.sql_queries import (
    AI_HOME_EXCLUDED_TABLES, BASE_SQL_SCHEMA, SCREEN_SQL_TABLES, TABLE_NOTES, _validate_sql, allowed_tables_for_screen,
    schema_text)

VIEW = 'v_ai_leader_unit'
SOURCE_TABLE = 'accounts_userprofile_leader_units'
EXISTING_VIEWS = (
    'v_ai_shipment', 'v_ai_purchase_receipt', 'v_ai_product', 'v_ai_process', 'v_ai_line', 'v_ai_supplier',
    'v_ai_customer')
PERIOD = ('2026-09-01', '2026-09-30')
PUBLISHED = ('id', 'user_id', 'login_id', 'last_name', 'first_name', 'employee_code', 'unit_id', 'unit_name')
SOURCES = ('m.id', 'm.userprofile_id', 'a.username', 'a.last_name', 'a.first_name', 'p.employee_code', 'm.department_id', 'd.name')
EXISTING_DEFINITION_SHA256 = 'db31acbfe065946a26dc439a40b4076ca41530869749bedf1f92e06600a410ed'
MIGRATION = Path(__file__).parent / 'migrations' / '0050_ai_leader_unit_view.py'
ALLOWED_UPPER_WORDS = {'ID'}
COMMON_PARTS = (
    'リーダー担当グループ', 'role=leader', '多対多', 'user_id', 'login_id', 'last_name', 'first_name', 'employee_code',
    'unit_id', 'unit_name', 'v_ai_department', 'admin', 'permission_scope', '未確認')


def check_no_fixed_values(case, text):
    """説明文に実データ由来の値(件数・氏名・部署名・社員コード)が混入していないことを検査する。"""
    case.assertIsNone(re.search(r'[0-9]{2,}', text))
    case.assertIsNone(re.search(r'[0-9]+(?:件|種類|人|名)|(?<![0-9])[0-9]+行', text.replace('1行', '')))
    case.assertIsNone(re.search(r'(?<![0-9])(?:[02-9]|[0-9]{2,})(?:列|個|班|グループ|ユーザー|階層)', text))
    for word in re.findall(r'(?<![A-Za-z_])[A-Z][A-Z0-9_]*(?![A-Za-z_])', text):
        case.assertIn(word, ALLOWED_UPPER_WORDS, word)


def migration_sql():
    return MIGRATION.read_text(encoding='utf-8').split('CREATE_VIEW = """')[1].split('"""')[0]


class LeaderUnitViewDefinitionTest(SimpleTestCase):
    def test_view_is_registered_without_date_and_quantity_field(self):
        definition = ANALYSIS_VIEWS[VIEW]
        self.assertIsNone(definition['date_field'])
        self.assertIsNone(definition['quantity_field'])
        self.assertEqual(definition['label'], 'リーダーの担当グループ')

    def test_column_types_match_published_columns_exactly(self):
        self.assertEqual(BASE_SQL_SCHEMA[VIEW], PUBLISHED)
        self.assertEqual(list(service.ANALYSIS_COLUMN_TYPES[VIEW]), list(PUBLISHED))
        self.assertEqual(service.ANALYSIS_COLUMN_TYPES[VIEW], {
            'id': 'BIGINT', 'user_id': 'BIGINT', 'login_id': 'VARCHAR', 'last_name': 'VARCHAR', 'first_name': 'VARCHAR',
            'employee_code': 'VARCHAR', 'unit_id': 'BIGINT', 'unit_name': 'VARCHAR'})
        user = service.ANALYSIS_COLUMN_TYPES['v_ai_user']
        department = service.ANALYSIS_COLUMN_TYPES['v_ai_department']
        types = service.ANALYSIS_COLUMN_TYPES[VIEW]
        self.assertEqual(types['user_id'], user['id'])
        for column in ('login_id', 'last_name', 'first_name', 'employee_code'):
            self.assertEqual(types[column], user[column])
            self.assertIn(column, BASE_SQL_SCHEMA['v_ai_user'])
        self.assertEqual(types['unit_id'], department['id'])
        self.assertEqual(types['unit_name'], department['name'])

    def test_non_public_columns_are_absent(self):
        sql = migration_sql()
        for column in ('password', 'email', 'last_login', 'is_superuser', 'date_joined', 'created_at', 'updated_at'):
            self.assertNotIn(column, BASE_SQL_SCHEMA[VIEW])
            self.assertNotIn(column, service.ANALYSIS_COLUMN_TYPES[VIEW])
            self.assertNotIn(column, sql)

    def test_ai_definition_omits_none_keys(self):
        self.assertEqual(set(ai_view_definition(VIEW)), {'label', 'description'})

    def test_existing_views_output_is_unchanged(self):
        schema = {view: {**ai_view_definition(view), 'fields': BASE_SQL_SCHEMA[view]} for view in EXISTING_VIEWS}
        digest = hashlib.sha256(json.dumps(schema, ensure_ascii=False).encode('utf-8')).hexdigest()
        self.assertEqual(digest, EXISTING_DEFINITION_SHA256)

    def test_description_has_required_notes_and_no_fixed_values(self):
        description = ANALYSIS_VIEWS[VIEW]['description']
        for part in COMMON_PARTS + ('v_ai_user', 'v_ai_userと同じ値', '結べない行がありうる', 'unit_idではない'):
            self.assertIn(part, description, part)
        check_no_fixed_values(self, description)
        notes = TABLE_NOTES[VIEW]
        for part in COMMON_PARTS:
            self.assertIn(part, notes, part)
        check_no_fixed_values(self, notes)

    def test_description_does_not_guess_business_meaning(self):
        for text in (ANALYSIS_VIEWS[VIEW]['description'], TABLE_NOTES[VIEW]):
            self.assertIn('業務上の運用は未確認', text)
            self.assertNotIn('必ず', text)
            self.assertNotIn('推奨', text)

    def test_description_check_detects_mutations(self):
        base = ANALYSIS_VIEWS[VIEW]['description']
        for mutation in (base + '全28件。', base + '28行。', base + 'A班がある。', base + '5グループ。', base + '3列。'):
            with self.assertRaises(AssertionError):
                check_no_fixed_values(self, mutation)

    def test_chat_sql_does_not_show_view_but_analysis_can_use_it(self):
        # 氏名・社員コードを持つため、チャット(AIホーム)のSQLに出さない(v_ai_user と同じ方針)
        self.assertIn(VIEW, AI_HOME_EXCLUDED_TABLES)
        self.assertNotIn(VIEW, SCREEN_SQL_TABLES['ai_home'])
        allowed = allowed_tables_for_screen('ai_home')
        statement, error = _validate_sql('SELECT unit_name FROM v_ai_leader_unit', allowed, 100)
        self.assertIsNone(statement)
        self.assertIn(VIEW, error)
        for personal in (False, True):
            self.assertNotIn(VIEW, schema_text('ai_home', personal))
        # 分析画面では使える
        self.assertIn(VIEW, ANALYSIS_VIEWS)
        self.assertIn(VIEW, BASE_SQL_SCHEMA)

    def test_origin_table_is_not_added_to_screens(self):
        self.assertNotIn(SOURCE_TABLE, BASE_SQL_SCHEMA)
        for tables in SCREEN_SQL_TABLES.values():
            self.assertNotIn(SOURCE_TABLE, tables)
            self.assertNotIn(VIEW, tables)

    def test_validate_datasets_and_where(self):
        datasets = [{'view': VIEW, 'fields': ['id', 'user_id', 'last_name', 'unit_name']}]
        self.assertEqual(validate_datasets(datasets, *PERIOD), datasets)
        with self.assertRaises(AnalysisError):
            validate_datasets([{'view': VIEW, 'fields': ['id', 'password']}], *PERIOD)
        self.assertEqual(build_where(VIEW, *PERIOD), ('', []))

    def test_consult_prompt_has_view(self):
        self.assertIn(VIEW, consult._system_prompt([]))

    def test_setup_command(self):
        self.assertIn(VIEW, cmd.EXISTING_JOIN_VIEWS)
        self.assertNotIn(VIEW, cmd.SIMPLE_MASTER_VIEWS)
        self.assertEqual(cmd.OTHER_VIEW_COLUMNS[SOURCE_TABLE], {'id', 'userprofile_id', 'department_id'})
        self.assertEqual(len(cmd.wanted_columns(SOURCE_TABLE)), 3)
        self.assertTrue({'id', 'username', 'first_name', 'last_name'} <= cmd.wanted_columns('auth_user'))
        self.assertTrue({'user_id', 'employee_code'} <= cmd.wanted_columns('accounts_userprofile'))
        self.assertTrue({'id', 'name'} <= cmd.wanted_columns('accounts_department'))

    def test_migration_is_primary_key_left_joins_without_where(self):
        source = MIGRATION.read_text(encoding='utf-8')
        sql = migration_sql()
        for banned in ('`', 'DEFINER', 'SQL SECURITY', 'WHERE', 'pm_db', 'INNER', 'RIGHT', 'CROSS', 'GROUP', 'UNION'):
            self.assertNotIn(banned, sql)
        self.assertIn('CREATE OR REPLACE VIEW v_ai_leader_unit AS', sql)
        self.assertIn(f'FROM {SOURCE_TABLE} m', sql)
        self.assertEqual(sql.count('JOIN'), 3)
        self.assertEqual(
            re.findall(r'LEFT JOIN (\S+) (\w+) ON \2\.(\w+) = m\.(\w+)', sql),
            [('auth_user', 'a', 'id', 'userprofile_id'), ('accounts_userprofile', 'p', 'user_id', 'userprofile_id'),
             ('accounts_department', 'd', 'id', 'department_id')])
        body = re.search(r'SELECT(.*?)FROM', sql, re.S).group(1)
        columns = [c.strip() for c in body.split(',') if c.strip()]
        names, sources = [], []
        for column in columns:
            source_column, _, alias = column.partition(' AS ')
            sources.append(source_column.strip())
            names.append(alias.strip() or source_column.split('.')[1])
        self.assertEqual(names, list(PUBLISHED))
        self.assertEqual(sources, list(SOURCES))
        self.assertIn("DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_leader_unit'", source)
        self.assertIn("('ai', '0049_ai_supervisor_team_view')", source)

    def test_user_view_and_department_view_have_joining_ids(self):
        self.assertIn('id', BASE_SQL_SCHEMA['v_ai_user'])
        self.assertIn('id', BASE_SQL_SCHEMA['v_ai_department'])
        self.assertIn('unit_id', BASE_SQL_SCHEMA['v_ai_user'])
