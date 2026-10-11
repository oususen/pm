"""部署のビュー v_ai_department の登録を検証する。

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

VIEW = 'v_ai_department'
EXISTING_VIEWS = (
    'v_ai_shipment', 'v_ai_purchase_receipt', 'v_ai_product', 'v_ai_process', 'v_ai_line', 'v_ai_supplier',
    'v_ai_customer')
PERIOD = ('2026-09-01', '2026-09-30')
PUBLISHED = ('id', 'name', 'level', 'display_id', 'parent_id', 'parent_name')
SOURCES = ('d.id', 'd.name', 'd.level', 'd.display_id', 'd.parent_id', 'pd.name')
EXISTING_DEFINITION_SHA256 = 'db31acbfe065946a26dc439a40b4076ca41530869749bedf1f92e06600a410ed'
MIGRATION = Path(__file__).parent / 'migrations' / '0046_ai_department_view.py'
ALLOWED_UPPER_WORDS = {'ID'}
LEVEL_LABELS = ('division=事業部・課', 'group=係', 'team=班', 'unit=グループ')
ROLE_HIERARCHY_PARTS = (
    'ユーザーの役割は所属する組織の階層に対応する', 'manager=事業部・課(division_id)', 'chief=係(group_id)',
    'supervisor=班(team_id)', 'leader=グループ(unit_id)', '配下の部署', 'parent_id', 'permission_scope',
    'supervisor_teams', 'leader_units', 'ビューに含まれない')


def check_no_fixed_values(case, text):
    """説明文に実データ由来の値(件数・部署名・コード)が混入していないことを検査する。"""
    case.assertIsNone(re.search(r'[0-9]{2,}', text))
    case.assertIsNone(re.search(r'[0-9]+(?:件|種類|人|名)|(?<![0-9])[0-9]+行', text.replace('1行', '')))
    case.assertIsNone(re.search(r'(?<![0-9])(?:[02-9]|[0-9]{2,})(?:列|個|部署|ユーザー|階層)', text))
    for word in re.findall(r'(?<![A-Za-z_])[A-Z][A-Z0-9_]*(?![A-Za-z_])', text):
        case.assertIn(word, ALLOWED_UPPER_WORDS, word)


def migration_sql():
    return MIGRATION.read_text(encoding='utf-8').split('CREATE_VIEW = """')[1].split('"""')[0]


class DepartmentViewDefinitionTest(SimpleTestCase):
    def test_view_is_registered_without_date_and_quantity_field(self):
        definition = ANALYSIS_VIEWS[VIEW]
        self.assertIsNone(definition['date_field'])
        self.assertIsNone(definition['quantity_field'])
        self.assertEqual(definition['label'], '部署')

    def test_column_types_match_published_columns_exactly(self):
        self.assertEqual(BASE_SQL_SCHEMA[VIEW], PUBLISHED)
        self.assertEqual(set(service.ANALYSIS_COLUMN_TYPES[VIEW]), set(PUBLISHED))
        self.assertEqual(service.ANALYSIS_COLUMN_TYPES[VIEW], {
            'id': 'BIGINT', 'name': 'VARCHAR', 'level': 'VARCHAR', 'display_id': 'BIGINT', 'parent_id': 'BIGINT',
            'parent_name': 'VARCHAR'})
        # ユーザービューの部署のID・名称の型と同じ
        user = service.ANALYSIS_COLUMN_TYPES['v_ai_user']
        self.assertEqual(service.ANALYSIS_COLUMN_TYPES[VIEW]['id'], user['department_id'])
        self.assertEqual(service.ANALYSIS_COLUMN_TYPES[VIEW]['name'], user['department_name'])

    def test_ai_definition_omits_none_keys(self):
        definition = ai_view_definition(VIEW)
        self.assertEqual(set(definition), {'label', 'description'})

    def test_existing_views_output_is_unchanged(self):
        schema = {view: {**ai_view_definition(view), 'fields': BASE_SQL_SCHEMA[view]} for view in EXISTING_VIEWS}
        digest = hashlib.sha256(json.dumps(schema, ensure_ascii=False).encode('utf-8')).hexdigest()
        self.assertEqual(digest, EXISTING_DEFINITION_SHA256)

    def test_description_has_required_notes_and_no_fixed_values(self):
        # 分析画面側の説明(ANALYSIS_VIEWS)はユーザービューとの結合・役割の対応も書く
        description = ANALYSIS_VIEWS[VIEW]['description']
        for part in (
                '1部署', '組織の階層', 'parent_name', 'display_id', '表示順', 'v_ai_user', 'department_id', 'division_id',
                'group_id', 'team_id', 'unit_id', 'モデルのラベル', '親が空の部署') + LEVEL_LABELS + ROLE_HIERARCHY_PARTS:
            self.assertIn(part, description, part)
        check_no_fixed_values(self, description)
        # チャットのSQL辞書(TABLE_NOTES)は v_ai_user を見せないため、ユーザービューの名前・列を書かない
        notes = TABLE_NOTES[VIEW]
        for part in (
                '1部署', '組織の階層', 'parent_name', 'display_id', '表示順', 'モデルのラベル', '親が空の部署', '配下の部署',
                'parent_id', 'permission_scope', 'supervisor_teams', 'leader_units', 'ビューに含まれない') + LEVEL_LABELS:
            self.assertIn(part, notes, part)
        check_no_fixed_values(self, notes)

    def test_chat_notes_do_not_mention_user_view(self):
        # チャット(AIホーム)のSQL辞書に出る文面に v_ai_user の名前を出さない(v_ai_user は AI_HOME_EXCLUDED_TABLES で除外)
        self.assertNotIn('v_ai_user', TABLE_NOTES[VIEW])
        for personal in (False, True):
            self.assertNotIn('v_ai_user', schema_text('ai_home', personal))
        # 分析画面側の説明は v_ai_user と結べることを書いてよい
        self.assertIn('v_ai_user', ANALYSIS_VIEWS[VIEW]['description'])

    def test_chat_sql_rejects_user_view_but_allows_department_view(self):
        allowed = allowed_tables_for_screen('ai_home')
        statement, error = _validate_sql('SELECT login_id FROM v_ai_user', allowed, 100)
        self.assertIsNone(statement)
        self.assertIn('v_ai_user', error)
        statement, error = _validate_sql('SELECT id, name FROM v_ai_department', allowed, 100)
        self.assertIsNone(error)
        self.assertIn('v_ai_department', statement)

    def test_description_check_detects_mutations(self):
        base = ANALYSIS_VIEWS[VIEW]['description']
        for mutation in (base + '全39部署。', base + '39件。', base + 'A課がある。', base + '5階層。'):
            with self.assertRaises(AssertionError):
                check_no_fixed_values(self, mutation)

    def test_origin_table_is_not_added_to_screens(self):
        self.assertNotIn('accounts_department', BASE_SQL_SCHEMA)
        self.assertIn(VIEW, SCREEN_SQL_TABLES['ai_home'])
        self.assertNotIn(VIEW, SCREEN_SQL_TABLES['production'])

    def test_validate_datasets_and_where(self):
        datasets = [{'view': VIEW, 'fields': ['id', 'name', 'parent_name']}]
        self.assertEqual(validate_datasets(datasets, *PERIOD), datasets)
        with self.assertRaises(AnalysisError):
            validate_datasets([{'view': VIEW, 'fields': ['id', 'created_at']}], *PERIOD)
        self.assertEqual(build_where(VIEW, *PERIOD), ('', []))

    def test_consult_prompt_has_view(self):
        self.assertIn(VIEW, consult._system_prompt([]))

    def test_setup_command(self):
        self.assertIn(VIEW, cmd.EXISTING_JOIN_VIEWS)
        self.assertNotIn(VIEW, cmd.SIMPLE_MASTER_VIEWS)
        self.assertEqual(cmd.OTHER_VIEW_COLUMNS['accounts_department'], {'id', 'name', 'level', 'display_id', 'parent_id'})
        self.assertEqual(len(cmd.wanted_columns('accounts_department')), 5)

    def test_migration_is_self_left_join_without_where(self):
        source = MIGRATION.read_text(encoding='utf-8')
        sql = migration_sql()
        for banned in ('`', 'DEFINER', 'SQL SECURITY', 'WHERE', 'pm_db', 'INNER', 'RIGHT', 'CROSS', 'GROUP', 'UNION'):
            self.assertNotIn(banned, sql)
        self.assertIn('CREATE OR REPLACE VIEW v_ai_department AS', sql)
        self.assertIn('FROM accounts_department d', sql)
        self.assertEqual(sql.count('JOIN'), 1)
        self.assertEqual(re.findall(r'LEFT JOIN accounts_department pd ON pd\.id = d\.parent_id', sql),
                         ['LEFT JOIN accounts_department pd ON pd.id = d.parent_id'])
        body = re.search(r'SELECT(.*?)FROM', sql, re.S).group(1)
        columns = [c.strip() for c in body.split(',') if c.strip()]
        names, sources = [], []
        for column in columns:
            source_column, _, alias = column.partition(' AS ')
            sources.append(source_column.strip())
            names.append(alias.strip() or source_column.split('.')[1])
        self.assertEqual(names, list(PUBLISHED))
        self.assertEqual(sources, list(SOURCES))
        self.assertIn("DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_department'", source)
        self.assertIn("('ai', '0045_ai_user_view')", source)

    def test_user_view_columns_join_to_department_id(self):
        # ユーザービューの所属のIDの列が、この id と結べる(名称の列が対になっている)
        user = BASE_SQL_SCHEMA['v_ai_user']
        for prefix in ('department', 'division', 'group', 'team', 'unit'):
            self.assertIn(f'{prefix}_id', user)
            self.assertIn(f'{prefix}_name', user)
