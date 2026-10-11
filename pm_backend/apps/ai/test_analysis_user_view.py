"""ユーザーのビュー v_ai_user の登録を検証する。

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
from ai.services.sql_queries import BASE_SQL_SCHEMA, SCREEN_SQL_TABLES, TABLE_NOTES

VIEW = 'v_ai_user'
EXISTING_VIEWS = (
    'v_ai_shipment', 'v_ai_purchase_receipt', 'v_ai_product', 'v_ai_process', 'v_ai_line', 'v_ai_supplier',
    'v_ai_customer')
PERIOD = ('2026-09-01', '2026-09-30')
PUBLISHED = (
    'id', 'login_id', 'first_name', 'last_name', 'is_active', 'is_staff', 'employee_code', 'employment_type',
    'role', 'is_system_admin', 'joined_on', 'department_id', 'department_name', 'division_id', 'division_name',
    'group_id', 'group_name', 'team_id', 'team_name', 'unit_id', 'unit_name')
# 各列の元(テーブルの別名.列)。順序は PUBLISHED と同じ
SOURCES = (
    'u.id', 'u.username', 'u.first_name', 'u.last_name', 'u.is_active', 'u.is_staff', 'p.employee_code',
    'p.employment_type', 'p.role', 'p.is_system_admin', 'p.joined_on', 'p.department_id', 'd1.name',
    'p.division_id', 'd2.name', 'p.group_id', 'd3.name', 'p.team_id', 'd4.name', 'p.unit_id', 'd5.name')
# 非公開(ビューに含めない): auth_user の password・last_login・is_superuser・email・date_joined、
# accounts_userprofile の created_at・updated_at
HIDDEN = ('password', 'last_login', 'is_superuser', 'email', 'date_joined', 'created_at', 'updated_at')
EXISTING_DEFINITION_SHA256 = 'db31acbfe065946a26dc439a40b4076ca41530869749bedf1f92e06600a410ed'
MIGRATION = Path(__file__).parent / 'migrations' / '0045_ai_user_view.py'

# 説明文に出てよい英大文字の語(ID、役割の序列の出典 ROLE_RANK)
ALLOWED_UPPER_WORDS = {'ID', 'ROLE_RANK'}
# モデルのラベル(AI用ビュー作成計画 §27)。説明に含まれること
ROLE_LABELS = ('manager=事業部長・課長', 'chief=係長', 'supervisor=班長', 'leader=リーダー', 'office_staff=事務員', 'staff=一般')
EMPLOYMENT_LABELS = (
    'regular=正準社員', 'dispatch=人材派遣', 'intern=実習生', 'skilled=特定技能実習生', 'contract=嘱託社員', 'part=パート')
# 管理する部署の集め方の違い(BOSS指示 2026-10-11。根拠: permission_scope.py・approval_views.py・role_utils.py)。ANALYSIS_VIEWS は半角の語の前後を詰めて書く
LEADER_MANAGED_NOTE = (
    '管理する部署の集め方は役割ごとに異なる(コード上、リーダーの管理部署は、リーダーが担当するグループの割り当て'
    '(このビューには含まれない)から集められ、このビューの')
# 役割と組織の階層の対応・序列・追加の担当割当の注意(BOSS追加指示 2026-10-11。コード: accounts の permission_scope・approval_views・role_utils)
ROLE_HIERARCHY_PARTS = (
    '役割は所属する組織の階層に対応する', 'manager=事業部・課(division_id)', 'chief=係(group_id)', 'supervisor=班(team_id)',
    'leader=グループ(unit_id)', '配下の部署', 'parent_id', 'permission_scope', 'approval_views', 'role_utils',
    'staff・office_staff=0 < leader=1 < supervisor=2 < chief=3 < manager=4', 'ROLE_RANK',
    'supervisor_teams', 'leader_units', 'その人の所属', '担当するすべての班・グループ', LEADER_MANAGED_NOTE)


def check_no_fixed_values(case, text):
    """説明文に実データ由来の値(件数・氏名・コード)が混入していないことを検査する。"""
    # 役割の序列の式(0 < 1 < 2 < 3 < 4)の1桁の数字は許す。それ以外の2桁以上の数字は書かない
    case.assertIsNone(re.search(r'[0-9]{2,}', text))
    case.assertIsNone(re.search(r'[0-9]+(?:件|種類|人|名)|(?<![0-9])(?:[02-9]|[0-9]{2,})行', text))
    case.assertIsNone(re.search(r'(?<![0-9])[02-9](?:列|個|部署|ユーザー|アカウント)', text))
    for word in re.findall(r'(?<![A-Za-z_])[A-Z][A-Z0-9_]*(?![A-Za-z_])', text):
        case.assertIn(word, ALLOWED_UPPER_WORDS, word)
    # 社員コード(数字だけ・先頭ゼロの数字列)やメールアドレスの形を書かない
    case.assertIsNone(re.search(r'@', text))


def migration_sql():
    return MIGRATION.read_text(encoding='utf-8').split('CREATE_VIEW = """')[1].split('"""')[0]


class UserViewDefinitionTest(SimpleTestCase):
    def test_view_is_registered_without_date_and_quantity_field(self):
        definition = ANALYSIS_VIEWS[VIEW]
        self.assertIsNone(definition['date_field'])
        self.assertIsNone(definition['quantity_field'])
        self.assertEqual(definition['label'], 'ユーザー')

    def test_column_types_match_published_columns_exactly(self):
        self.assertEqual(BASE_SQL_SCHEMA[VIEW], PUBLISHED)
        self.assertEqual(len(PUBLISHED), 21)
        self.assertEqual(len(set(PUBLISHED)), 21)
        self.assertEqual(set(service.ANALYSIS_COLUMN_TYPES[VIEW]), set(BASE_SQL_SCHEMA[VIEW]))
        self.assertEqual(service.ANALYSIS_COLUMN_TYPES[VIEW], {
            'id': 'BIGINT', 'login_id': 'VARCHAR', 'first_name': 'VARCHAR', 'last_name': 'VARCHAR',
            'is_active': 'BIGINT', 'is_staff': 'BIGINT', 'employee_code': 'VARCHAR', 'employment_type': 'VARCHAR',
            'role': 'VARCHAR', 'is_system_admin': 'BIGINT', 'joined_on': 'DATE', 'department_id': 'BIGINT',
            'department_name': 'VARCHAR', 'division_id': 'BIGINT', 'division_name': 'VARCHAR', 'group_id': 'BIGINT',
            'group_name': 'VARCHAR', 'team_id': 'BIGINT', 'team_name': 'VARCHAR', 'unit_id': 'BIGINT',
            'unit_name': 'VARCHAR'})

    def test_types_match_existing_views(self):
        types = service.ANALYSIS_COLUMN_TYPES
        self.assertEqual(types[VIEW]['id'], types['v_ai_customer']['id'])
        self.assertEqual(types[VIEW]['is_active'], types['v_ai_customer']['is_active'])
        self.assertEqual(types[VIEW]['joined_on'], types['v_ai_calendar_day']['target_date'])
        self.assertEqual(types[VIEW]['department_id'], types['v_ai_customer']['id'])

    def test_ai_definition_omits_none_keys(self):
        definition = ai_view_definition(VIEW)
        self.assertEqual(set(definition), {'label', 'description'})
        self.assertNotIn(None, definition.values())

    def test_existing_views_output_is_unchanged(self):
        schema = {view: {**ai_view_definition(view), 'fields': BASE_SQL_SCHEMA[view]} for view in EXISTING_VIEWS}
        digest = hashlib.sha256(json.dumps(schema, ensure_ascii=False).encode('utf-8')).hexdigest()
        self.assertEqual(digest, EXISTING_DEFINITION_SHA256)

    def test_description_has_required_notes_and_no_hidden_or_fixed_values(self):
        for text in (ANALYSIS_VIEWS[VIEW]['description'], TABLE_NOTES[VIEW]):
            for part in (
                    '1ユーザー', 'ログインアカウント', 'login_id', 'ログインID', '姓・名', '社員コード', '入社日', 'システム管理者',
                    'v_ai_department', '5つの所属', 'department_id', 'division_id', 'group_id', 'team_id', 'unit_id',
                    'division_id・division_name=事業部・課' if text is ANALYSIS_VIEWS[VIEW]['description']
                    else 'division_id・division_name=事業部・課',
                    'モデルのラベル', 'モデルの表記のまま', 'admin', '含まれない', '未確認', 'Django') + ROLE_LABELS + EMPLOYMENT_LABELS \
                    + ROLE_HIERARCHY_PARTS:
                self.assertIn(part, text, part)
            # 非公開列・元の列名は説明に書かない(username はログインIDの元の列名)
            for hidden in HIDDEN + ('username', 'profile'.upper()):
                self.assertNotIn(hidden, text)
            check_no_fixed_values(self, text)
            # 「個人の評価に使わない」等の規定は書かない(BOSSが取り下げ済み)
            for banned in ('評価', '査定', '順位'):
                self.assertNotIn(banned, text)

    def test_role_hierarchy_note_lists_every_role_label_once_in_correct_pairs(self):
        # 役割と階層の対応は、コードで確認した組(manager=division_id・chief=group_id・supervisor=team_id・leader=unit_id)だけ
        for text in (ANALYSIS_VIEWS[VIEW]['description'], TABLE_NOTES[VIEW]):
            pairs = re.findall(r'(manager|chief|supervisor|leader)=([^(、。]+)\((\w+)\)', text)
            self.assertEqual(
                pairs,
                [('manager', '事業部・課', 'division_id'), ('chief', '係', 'group_id'),
                 ('supervisor', '班', 'team_id'), ('leader', 'グループ', 'unit_id')])

    def test_leader_managed_note_full_sentence(self):
        # 追加指示の1文の全文(ANALYSIS_VIEWS は unit_id の前に空白なし、TABLE_NOTES は空白あり)
        tail = '(所属)とは別である)。'
        self.assertIn(LEADER_MANAGED_NOTE + 'unit_id' + tail, ANALYSIS_VIEWS[VIEW]['description'])
        self.assertIn(LEADER_MANAGED_NOTE + ' unit_id' + tail, TABLE_NOTES[VIEW])

    def test_description_check_detects_mutations(self):
        # 氏名・社員コード・件数・具体値を足した説明は、検査が失敗する(検査が効いていることの確認)
        base = ANALYSIS_VIEWS[VIEW]['description']
        for mutation in (base + '社員コードは000175。', base + '98人のユーザー。', base + '全98件。',
                         base + 'ADMINを除く。', base + 'a@example.com', base + '全12ユーザー。'):
            with self.assertRaises(AssertionError):
                check_no_fixed_values(self, mutation)

    def test_origin_table_permissions_are_not_replaced(self):
        # 元テーブルは BASE_SQL_SCHEMA・SCREEN_SQL_TABLES にない(ビューの追加のみ)
        for table in ('auth_user', 'accounts_userprofile', 'accounts_department'):
            self.assertNotIn(table, BASE_SQL_SCHEMA)
        self.assertNotIn(VIEW, SCREEN_SQL_TABLES['production'])
        # チャット(AIホーム)のSQLには見せない(氏名・社員コード・ログインIDのため。BOSS承認 案A)
        self.assertNotIn(VIEW, SCREEN_SQL_TABLES['ai_home'])
        for screen_tables in SCREEN_SQL_TABLES.values():
            self.assertNotIn(VIEW, screen_tables)

    def test_validate_datasets_without_date_field(self):
        datasets = [{'view': VIEW, 'fields': ['id', 'login_id', 'role', 'employee_code']}]
        self.assertEqual(validate_datasets(datasets, *PERIOD), datasets)
        for hidden in HIDDEN + ('username', 'profile'):
            with self.assertRaises(AnalysisError):
                validate_datasets([{'view': VIEW, 'fields': ['id', hidden]}], *PERIOD)

    def test_build_where_does_not_filter_by_period(self):
        self.assertEqual(build_where(VIEW, *PERIOD), ('', []))
        self.assertEqual(build_where(VIEW, *PERIOD, last_id=5), (' WHERE `id` > %s', [5]))

    def test_consult_prompt_has_view(self):
        self.assertIn(VIEW, consult._system_prompt([]))

    def test_setup_command_treats_view_as_join_view(self):
        self.assertIn(VIEW, cmd.EXISTING_JOIN_VIEWS)
        self.assertNotIn(VIEW, cmd.SIMPLE_MASTER_VIEWS)
        self.assertEqual(cmd.OTHER_VIEW_COLUMNS['auth_user'], {'id', 'username', 'first_name', 'last_name', 'is_active', 'is_staff'})
        self.assertEqual(cmd.OTHER_VIEW_COLUMNS['accounts_userprofile'], {
            'user_id', 'employee_code', 'employment_type', 'role', 'is_system_admin', 'joined_on',
            'department_id', 'division_id', 'group_id', 'team_id', 'unit_id'})
        self.assertEqual(len(cmd.wanted_columns('auth_user')), 6)
        self.assertEqual(len(cmd.wanted_columns('accounts_userprofile')), 11)
        for column in ('password', 'last_login', 'is_superuser', 'email', 'date_joined'):
            self.assertNotIn(column, cmd.wanted_columns('auth_user'))
        for column in ('created_at', 'updated_at'):
            self.assertNotIn(column, cmd.wanted_columns('accounts_userprofile'))

    def test_published_columns_equal_source_columns(self):
        # 元の列(別名の左辺)が、OTHER_VIEW_COLUMNS と過不足なく一致する(結合キー user_id は p.user_id = u.id)
        user = {s.split('.')[1] for s in SOURCES if s.startswith('u.')}
        profile = {s.split('.')[1] for s in SOURCES if s.startswith('p.')}
        self.assertEqual(user, cmd.OTHER_VIEW_COLUMNS['auth_user'])
        self.assertEqual(profile | {'user_id'}, cmd.OTHER_VIEW_COLUMNS['accounts_userprofile'])

    def test_migration_is_standard_left_join_with_only_admin_filter(self):
        source = MIGRATION.read_text(encoding='utf-8')
        sql = migration_sql()
        for banned in ('`', 'DEFINER', 'SQL SECURITY', 'pm_db', 'INNER', 'RIGHT', 'CROSS', 'GROUP', 'UNION', 'HAVING'):
            self.assertNotIn(banned, sql)
        self.assertNotIn(' OR ', sql.replace('CREATE OR REPLACE', ''))  # WHERE に OR/AND の条件を足さない
        self.assertNotIn(' AND ', sql)
        self.assertIn('CREATE OR REPLACE VIEW v_ai_user AS', sql)
        # WHERE は admin アカウントの除外だけ(1か所・この条件)
        self.assertEqual(sql.count('WHERE'), 1)
        self.assertEqual(re.findall(r'WHERE (.*)', sql), ["u.username <> 'admin'"])
        self.assertEqual(sql.count('JOIN'), 6)
        self.assertEqual(len(re.findall(r'\bLEFT JOIN\b', sql)), 6)
        self.assertIn('FROM auth_user u', sql)
        # 結合キーは、すべて結合先の主キー(プロフィールは user_id、部署は id)
        joins = re.findall(r'LEFT JOIN (\w+) (\w+) ON (\w+)\.(\w+) = (\w+)\.(\w+)', sql)
        self.assertEqual(len(joins), 6)
        for table, alias, left_alias, left_column, _right_alias, _right_column in joins:
            self.assertEqual(alias, left_alias)
            self.assertEqual(left_column, 'user_id' if table == 'accounts_userprofile' else 'id')
        for join in (
                'LEFT JOIN accounts_userprofile p ON p.user_id = u.id',
                'LEFT JOIN accounts_department d1 ON d1.id = p.department_id',
                'LEFT JOIN accounts_department d2 ON d2.id = p.division_id',
                'LEFT JOIN accounts_department d3 ON d3.id = p.group_id',
                'LEFT JOIN accounts_department d4 ON d4.id = p.team_id',
                'LEFT JOIN accounts_department d5 ON d5.id = p.unit_id'):
            self.assertIn(join, sql)
        body = re.search(r'SELECT(.*?)FROM', sql, re.S).group(1)
        columns = [c.strip() for c in body.split(',') if c.strip()]
        self.assertEqual(len(columns), 21)
        names, sources = [], []
        for column in columns:
            source_column, _, alias = column.partition(' AS ')
            sources.append(source_column.strip())
            names.append(alias.strip() or source_column.split('.')[1])
        self.assertEqual(names, list(PUBLISHED))
        self.assertEqual(sources, list(SOURCES))
        for hidden in HIDDEN:
            self.assertNotIn(hidden, sql)
        self.assertIn("DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_user'", source)
        self.assertIn("('ai', '0044_alter_aianalysistemplate_category')", source)
        self.assertIn("('accounts', '0072_alter_departmentpermission_resource_and_more')", source)
        self.assertIn("('auth', '0012_alter_user_first_name_max_length')", source)

    def test_migration_dependency_exists(self):
        accounts = Path(__file__).parent.parent / 'accounts' / 'migrations'
        self.assertTrue((accounts / '0072_alter_departmentpermission_resource_and_more.py').exists())
        self.assertEqual(sorted(p.name for p in accounts.glob('00*.py'))[-1], '0072_alter_departmentpermission_resource_and_more.py')
        self.assertTrue((Path(__file__).parent / 'migrations' / '0044_alter_aianalysistemplate_category.py').exists())

    def test_existing_view_definitions_in_migrations_are_unchanged(self):
        for path in (Path(__file__).parent / 'migrations').glob('00[0-4][0-4]*.py'):
            self.assertNotIn(VIEW, path.read_text(encoding='utf-8'), path.name)
