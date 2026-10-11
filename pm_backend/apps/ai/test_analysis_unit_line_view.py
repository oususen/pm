"""グループとラインの紐付のビュー v_ai_unit_line の登録を検証する。

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
    BASE_SQL_SCHEMA, SCREEN_SQL_TABLES, TABLE_NOTES, _validate_sql, allowed_tables_for_screen, schema_text)

VIEW = 'v_ai_unit_line'
EXISTING_VIEWS = (
    'v_ai_shipment', 'v_ai_purchase_receipt', 'v_ai_product', 'v_ai_process', 'v_ai_line', 'v_ai_supplier',
    'v_ai_customer')
PERIOD = ('2026-09-01', '2026-09-30')
PUBLISHED = ('id', 'unit_id', 'unit_name', 'line_id', 'line_code', 'line_name', 'sort_order', 'is_default')
SOURCES = ('m.id', 'm.unit_id', 'u.name', 'm.line_id', 'l.line_code', 'l.line_name', 'm.sort_order', 'm.is_default')
EXISTING_DEFINITION_SHA256 = 'db31acbfe065946a26dc439a40b4076ca41530869749bedf1f92e06600a410ed'
MIGRATION = Path(__file__).parent / 'migrations' / '0048_ai_unit_line_view.py'
ALLOWED_UPPER_WORDS = {'ID'}
COMMON_PARTS = (
    '1つの', 'グループ', 'ライン', 'unit_id', 'unit_name', 'line_id', 'line_code', 'line_name', 'v_ai_department',
    'v_ai_line', 'sort_order', '表示順', 'is_default', '初期ライン', 'モデルのラベル', 'get_unit_lines',
    '降順', '昇順', 'unique_together', '多対多', '未確認')


def check_no_fixed_values(case, text):
    """説明文に実データ由来の値(件数・グループ名・ライン名・コード)が混入していないことを検査する。"""
    case.assertIsNone(re.search(r'[0-9]{2,}', text))
    case.assertIsNone(re.search(r'[0-9]+(?:件|種類|人|名)|(?<![0-9])[0-9]+行', text.replace('1行', '')))
    case.assertIsNone(re.search(r'(?<![0-9])(?:[02-9]|[0-9]{2,})(?:列|個|グループ|ライン|ユーザー|階層)', text))
    for word in re.findall(r'(?<![A-Za-z_])[A-Z][A-Z0-9_]*(?![A-Za-z_])', text):
        case.assertIn(word, ALLOWED_UPPER_WORDS, word)


def migration_sql():
    return MIGRATION.read_text(encoding='utf-8').split('CREATE_VIEW = """')[1].split('"""')[0]


class UnitLineViewDefinitionTest(SimpleTestCase):
    def test_view_is_registered_without_date_and_quantity_field(self):
        definition = ANALYSIS_VIEWS[VIEW]
        self.assertIsNone(definition['date_field'])
        self.assertIsNone(definition['quantity_field'])
        self.assertEqual(definition['label'], 'グループのライン')

    def test_column_types_match_published_columns_exactly(self):
        self.assertEqual(BASE_SQL_SCHEMA[VIEW], PUBLISHED)
        self.assertEqual(set(service.ANALYSIS_COLUMN_TYPES[VIEW]), set(PUBLISHED))
        self.assertEqual(list(service.ANALYSIS_COLUMN_TYPES[VIEW]), list(PUBLISHED))
        self.assertEqual(service.ANALYSIS_COLUMN_TYPES[VIEW], {
            'id': 'BIGINT', 'unit_id': 'BIGINT', 'unit_name': 'VARCHAR', 'line_id': 'BIGINT', 'line_code': 'VARCHAR',
            'line_name': 'VARCHAR', 'sort_order': 'BIGINT', 'is_default': 'BIGINT'})
        # 結合先のビューの同じ意味の列と型が同じ
        line = service.ANALYSIS_COLUMN_TYPES['v_ai_line']
        department = service.ANALYSIS_COLUMN_TYPES['v_ai_department']
        types = service.ANALYSIS_COLUMN_TYPES[VIEW]
        self.assertEqual(types['line_id'], line['id'])
        self.assertEqual(types['line_code'], line['line_code'])
        self.assertEqual(types['line_name'], line['line_name'])
        self.assertEqual(types['unit_id'], department['id'])
        self.assertEqual(types['unit_name'], department['name'])

    def test_non_public_columns_are_absent(self):
        for column in ('created_at', 'updated_at'):
            self.assertNotIn(column, BASE_SQL_SCHEMA[VIEW])
            self.assertNotIn(column, service.ANALYSIS_COLUMN_TYPES[VIEW])
            self.assertNotIn(column, migration_sql())

    def test_ai_definition_omits_none_keys(self):
        definition = ai_view_definition(VIEW)
        self.assertEqual(set(definition), {'label', 'description'})

    def test_existing_views_output_is_unchanged(self):
        schema = {view: {**ai_view_definition(view), 'fields': BASE_SQL_SCHEMA[view]} for view in EXISTING_VIEWS}
        digest = hashlib.sha256(json.dumps(schema, ensure_ascii=False).encode('utf-8')).hexdigest()
        self.assertEqual(digest, EXISTING_DEFINITION_SHA256)

    def test_description_has_required_notes_and_no_fixed_values(self):
        # 分析画面側の説明(ANALYSIS_VIEWS)はユーザービューとの結合も書く
        description = ANALYSIS_VIEWS[VIEW]['description']
        for part in COMMON_PARTS + ('v_ai_user', 'unit_id)に対応', '一覧', 'serializers'):
            self.assertIn(part, description, part)
        check_no_fixed_values(self, description)
        # チャットのSQL辞書(TABLE_NOTES)は v_ai_user を見せないため、ユーザービューの名前を書かない
        notes = TABLE_NOTES[VIEW]
        for part in COMMON_PARTS + ('プロフィールの unit_id', '一覧', 'serializers'):
            self.assertIn(part, notes, part)
        check_no_fixed_values(self, notes)

    def test_description_does_not_guess_business_meaning(self):
        # 未確認の業務上の意味を断定しない(運用・絞り込みは「未確認」と書く)
        for text in (ANALYSIS_VIEWS[VIEW]['description'], TABLE_NOTES[VIEW]):
            self.assertIn('業務上の意味は未確認', text)
            self.assertNotIn('必ず', text)
            self.assertNotIn('推奨', text)

    def test_chat_notes_do_not_mention_user_view(self):
        self.assertNotIn('v_ai_user', TABLE_NOTES[VIEW])
        for personal in (False, True):
            self.assertNotIn('v_ai_user', schema_text('ai_home', personal))
        self.assertIn('v_ai_user', ANALYSIS_VIEWS[VIEW]['description'])

    def test_chat_sql_allows_view_and_dictionary_lists_it(self):
        # このビューは個人情報を含まないため、チャット(AIホーム)のSQLに見えてよい
        self.assertIn(VIEW, SCREEN_SQL_TABLES['ai_home'])
        allowed = allowed_tables_for_screen('ai_home')
        statement, error = _validate_sql('SELECT unit_name, line_name FROM v_ai_unit_line', allowed, 100)
        self.assertIsNone(error)
        self.assertIn(VIEW, statement)
        for personal in (False, True):
            text = schema_text('ai_home', personal)
            self.assertIn(VIEW, text)
            self.assertIn('unit_name', text)
        statement, error = _validate_sql('SELECT created_at FROM accounts_unit_line_mapping', allowed, 100)
        self.assertIsNone(statement)

    def test_description_check_detects_mutations(self):
        base = ANALYSIS_VIEWS[VIEW]['description']
        for mutation in (base + '全28件。', base + '28行。', base + 'A組がある。', base + '5ライン。', base + '3列。'):
            with self.assertRaises(AssertionError):
                check_no_fixed_values(self, mutation)

    def test_origin_table_is_not_added_to_screens(self):
        self.assertNotIn('accounts_unit_line_mapping', BASE_SQL_SCHEMA)
        for screen, tables in SCREEN_SQL_TABLES.items():
            self.assertNotIn('accounts_unit_line_mapping', tables)
        self.assertNotIn(VIEW, SCREEN_SQL_TABLES['production'])

    def test_validate_datasets_and_where(self):
        datasets = [{'view': VIEW, 'fields': ['id', 'unit_name', 'line_name', 'is_default']}]
        self.assertEqual(validate_datasets(datasets, *PERIOD), datasets)
        with self.assertRaises(AnalysisError):
            validate_datasets([{'view': VIEW, 'fields': ['id', 'created_at']}], *PERIOD)
        self.assertEqual(build_where(VIEW, *PERIOD), ('', []))

    def test_consult_prompt_has_view(self):
        self.assertIn(VIEW, consult._system_prompt([]))

    def test_setup_command(self):
        self.assertIn(VIEW, cmd.EXISTING_JOIN_VIEWS)
        self.assertNotIn(VIEW, cmd.SIMPLE_MASTER_VIEWS)
        self.assertEqual(
            cmd.OTHER_VIEW_COLUMNS['accounts_unit_line_mapping'], {'id', 'unit_id', 'line_id', 'sort_order', 'is_default'})
        self.assertEqual(len(cmd.wanted_columns('accounts_unit_line_mapping')), 5)

    def test_migration_is_primary_key_left_joins_without_where(self):
        source = MIGRATION.read_text(encoding='utf-8')
        sql = migration_sql()
        for banned in ('`', 'DEFINER', 'SQL SECURITY', 'WHERE', 'pm_db', 'INNER', 'RIGHT', 'CROSS', 'GROUP', 'UNION'):
            self.assertNotIn(banned, sql)
        self.assertIn('CREATE OR REPLACE VIEW v_ai_unit_line AS', sql)
        self.assertIn('FROM accounts_unit_line_mapping m', sql)
        self.assertEqual(sql.count('JOIN'), 2)
        self.assertEqual(
            re.findall(r'LEFT JOIN (\S+) (\w+) ON \2\.id = m\.(\w+)', sql),
            [('accounts_department', 'u', 'unit_id'), ('m_line', 'l', 'line_id')])
        body = re.search(r'SELECT(.*?)FROM', sql, re.S).group(1)
        columns = [c.strip() for c in body.split(',') if c.strip()]
        names, sources = [], []
        for column in columns:
            source_column, _, alias = column.partition(' AS ')
            sources.append(source_column.strip())
            names.append(alias.strip() or source_column.split('.')[1])
        self.assertEqual(names, list(PUBLISHED))
        self.assertEqual(sources, list(SOURCES))
        self.assertIn("DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_unit_line'", source)
        self.assertIn("('ai', '0047_aianalysisrun_purpose')", source)

    def test_user_view_unit_id_and_line_view_id_exist_for_joining(self):
        self.assertIn('unit_id', BASE_SQL_SCHEMA['v_ai_user'])
        self.assertIn('id', BASE_SQL_SCHEMA['v_ai_department'])
        self.assertIn('id', BASE_SQL_SCHEMA['v_ai_line'])
