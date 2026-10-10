"""管理コマンド setup_ai_views を検証する。

DBを作らない(SimpleTestCase)。偽の接続・カーソルだけを使い、開発DBへは接続しない。
"""
import re
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from ai.management.commands import setup_ai_views as cmd
from ai.services.sql_queries import BASE_SQL_SCHEMA

MODULE = 'ai.management.commands.setup_ai_views'
DB = 'pm_test_db'
OWNER = 'pm_ai_view_owner@localhost'
# 各ビューの最新の CREATE_VIEW があるマイグレーション
LATEST_MIGRATION = {
    'v_ai_product': '0037_ai_product_view_remove_dates.py',
    'v_ai_process': '0035_ai_process_view.py',
    'v_ai_line': '0036_ai_line_view.py',
    'v_ai_supplier': '0038_ai_supplier_view.py',
    'v_ai_customer': '0039_ai_customer_view.py',
}


class FakeCursor:
    """information_schema の問い合わせに、状態を返す偽のカーソル。"""

    def __init__(self, privileges, views):
        self.privileges = privileges  # {元テーブル: {列}}
        self.views = views  # {ビュー: (定義者, SECURITY_TYPE, 列のタプル)}
        self.executed = []  # DDL(GRANT・CREATE・REVOKE)
        self.table_select = set()  # 表全体のSELECTを持つ元テーブル
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        if 'COLUMN_PRIVILEGES' in sql:
            self.rows = [(c,) for c in sorted(self.privileges.get(params[2], set()))]
        elif 'TABLE_PRIVILEGES' in sql:
            self.rows = [(1,)] if params[2] in self.table_select else []
        elif 'information_schema.VIEWS' in sql:
            state = self.views.get(params[1])
            self.rows = [(state[0], state[1])] if state else []
        elif 'information_schema.COLUMNS' in sql:
            state = self.views.get(params[1])
            self.rows = [(c,) for c in state[2]] if state else []
        else:
            self.executed.append(sql)
            self.rows = []

    def fetchall(self):
        return self.rows


def fake_connection(cursor, vendor='mysql'):
    return SimpleNamespace(vendor=vendor, settings_dict={'NAME': DB}, cursor=lambda: cursor)


def aligned_state():
    """すべて揃った状態(権限=公開列の和集合、全ビューの定義者・列が期待どおり)。"""
    privileges = {}
    for table in set(cmd.SIMPLE_MASTER_VIEWS.values()):
        privileges[table] = set(cmd.wanted_columns(table))
    views = {v: (OWNER, 'DEFINER', tuple(BASE_SQL_SCHEMA[v])) for v in cmd.SIMPLE_MASTER_VIEWS}
    for v in cmd.EXISTING_JOIN_VIEWS:
        views[v] = (OWNER, 'DEFINER', ('id',))
    return privileges, views


def initial_state():
    """migrate 直後: 定義者は root、権限は m_product に余分な列のみ。"""
    privileges = {'m_product': {'id', 'product_code', 'product_name', 'created_at', 'updated_at'}}
    views = {v: ('root@localhost', 'DEFINER', tuple(BASE_SQL_SCHEMA[v])) for v in cmd.SIMPLE_MASTER_VIEWS}
    return privileges, views


def run(cursor, *args, vendor='mysql', reader_ok=True):
    out = StringIO()
    reader = SimpleNamespace(
        cursor=lambda: _Reader(reader_ok),
    )
    with patch(f'{MODULE}.connection', fake_connection(cursor, vendor)), \
            patch(f'{MODULE}.connections', {cmd.AI_DB_ALIAS: reader}):
        call_command('setup_ai_views', *args, stdout=out)
    return out.getvalue()


class _Reader:
    def __init__(self, ok):
        self.ok = ok

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        if not self.ok:
            raise RuntimeError('denied')

    def fetchall(self):
        return [(1,)]


class SetupAiViewsTests(SimpleTestCase):
    def plan(self, state=None, views=None, reader_host=None):
        privileges, view_state = state or initial_state()
        cursor = FakeCursor(privileges, view_state)
        views = views or list(cmd.SIMPLE_MASTER_VIEWS)
        return cmd.build_plan(cursor, DB, 'pm_ai_view_owner', 'localhost', views, reader_host)

    def test_create_sql_matches_base_sql_schema(self):
        plan = dict()
        for kind, sql in self.plan():
            if kind == 'CREATE':
                plan[re.search(r'`(v_ai_\w+)` AS', sql).group(1)] = sql
        self.assertEqual(set(plan), set(cmd.SIMPLE_MASTER_VIEWS))
        for view, sql in plan.items():
            table = cmd.SIMPLE_MASTER_VIEWS[view]
            columns = re.search(r'AS SELECT (.*) FROM', sql).group(1)
            self.assertEqual(re.findall(r'`(\w+)`', columns), list(BASE_SQL_SCHEMA[view]))
            self.assertTrue(sql.startswith(
                "CREATE OR REPLACE DEFINER = 'pm_ai_view_owner'@'localhost' SQL SECURITY DEFINER VIEW"))
            self.assertTrue(sql.endswith(f'FROM `{DB}`.`{table}`'))

    def test_migration_columns_match_command(self):
        # マイグレーションとコマンドの食い違いを検出する
        base = Path(__file__).parent / 'migrations'
        for view, name in LATEST_MIGRATION.items():
            source = (base / name).read_text(encoding='utf-8')
            sql = source.split('CREATE_VIEW = """')[1].split('"""')[0]
            body = re.search(r'SELECT(.*)FROM\s+(\w+)', sql, re.S)
            columns = [c.strip() for c in body.group(1).split(',') if c.strip()]
            self.assertEqual(columns, list(BASE_SQL_SCHEMA[view]), view)
            self.assertEqual(body.group(2), cmd.SIMPLE_MASTER_VIEWS[view], view)

    def test_default_is_dry_run(self):
        privileges, views = initial_state()
        cursor = FakeCursor(privileges, views)
        output = run(cursor)
        self.assertEqual(cursor.executed, [])
        self.assertIn('[GRANT]', output)
        self.assertIn('[CREATE]', output)
        self.assertIn('[REVOKE]', output)
        self.assertIn('表示のみ', output)

    def test_apply_executes_grant_create_revoke_in_order(self):
        privileges, views = initial_state()
        cursor = FakeCursor(privileges, views)
        run(cursor, '--apply')
        kinds = [s.split()[0] for s in cursor.executed]
        self.assertEqual(set(kinds), {'GRANT', 'CREATE', 'REVOKE'})
        self.assertEqual(kinds[:2], ['GRANT', 'CREATE'])
        # 1ビューごとに GRANT→CREATE、REVOKE は最後
        first_revoke = kinds.index('REVOKE')
        self.assertTrue(all(k == 'REVOKE' for k in kinds[first_revoke:]))
        # m_product は id・product_code・product_name が既に有り、created_at・updated_at だけを REVOKE する
        revokes = [s for s in cursor.executed if s.startswith('REVOKE')]
        self.assertEqual(len(revokes), 1)
        self.assertIn('`created_at`, `updated_at`', revokes[0])
        self.assertIn('`m_product`', revokes[0])
        # reader への GRANT は、既定では実行しない
        self.assertFalse(any(pm in s for s in cursor.executed for pm in ('pm_ai_reader',)))

    def test_reader_grant_only_with_reader_host(self):
        sqls = [sql for kind, sql in self.plan(reader_host='10.0.%')]
        self.assertEqual(sum("TO 'pm_ai_reader'@'10.0.%'" in s for s in sqls), len(cmd.SIMPLE_MASTER_VIEWS))
        self.assertFalse(any('pm_ai_reader' in sql for kind, sql in self.plan()))

    def test_rejects_invalid_values_for_every_option(self):
        privileges, views = initial_state()
        cursor = FakeCursor(privileges, views)
        bad_values = ('abc\n', 'a b', 'a;b', "a'b", 'a"b', 'a`b')
        for option in ('--owner', '--owner-host', '--reader-host'):
            for value in bad_values + ('',):
                if option == '--reader-host' and value == '':
                    continue  # 空は「指定なし」と同じ扱い
                with self.subTest(option=option, value=value):
                    with self.assertRaises(CommandError):
                        run(cursor, option, value)
        for value in bad_values + ('v_ai_unknown', 'v_ai_line\n'):
            with self.subTest(option='--views', value=value):
                with self.assertRaises(CommandError):
                    run(cursor, '--views', value)
        with self.assertRaises(CommandError):
            cmd.quote_identifier('a`b')
        self.assertEqual(cursor.executed, [])

    def test_rejects_backtick_in_db_name(self):
        privileges, views = initial_state()
        cursor = FakeCursor(privileges, views)
        connection = SimpleNamespace(vendor='mysql', settings_dict={'NAME': 'a`b'}, cursor=lambda: cursor)
        with patch(f'{MODULE}.connection', connection):
            with self.assertRaises(CommandError):
                call_command('setup_ai_views', stdout=StringIO())

    def test_non_mysql_does_nothing(self):
        privileges, views = initial_state()
        cursor = FakeCursor(privileges, views)
        output = run(cursor, '--apply', vendor='postgresql')
        self.assertIn('何もしない', output)
        self.assertEqual(cursor.executed, [])

    def test_idempotent_when_aligned(self):
        privileges, views = aligned_state()
        cursor = FakeCursor(privileges, views)
        output = run(cursor, '--apply')
        self.assertEqual(cursor.executed, [])
        self.assertIn('すでに揃っています', output)
        self.assertIn('要対応: 0件', output)

    def test_does_not_recreate_join_views(self):
        privileges, views = initial_state()
        for v in cmd.EXISTING_JOIN_VIEWS:
            views[v] = ('root@localhost', 'DEFINER', ('id',))
        # CREATE の対象に入らない(build_plan は単純なマスタビューしか受け付けない)
        created = [sql for kind, sql in self.plan((privileges, views)) if kind == 'CREATE']
        self.assertEqual(len(created), len(cmd.SIMPLE_MASTER_VIEWS))
        for v in cmd.EXISTING_JOIN_VIEWS:
            self.assertFalse(any(v in sql for sql in created))
            self.assertNotIn(v, cmd.SIMPLE_MASTER_VIEWS)
        cursor = FakeCursor(privileges, views)
        output = run(cursor, '--apply')
        for v in cmd.EXISTING_JOIN_VIEWS:
            self.assertFalse(any(v in s for s in cursor.executed))
            self.assertIn(f'{v}: 定義者=root@localhost', output)  # --check の対象としては表示する
        # --views で join系だけを指定しても、何も実行しない
        cursor = FakeCursor(privileges, views)
        run(cursor, '--apply', '--views', *cmd.EXISTING_JOIN_VIEWS)
        self.assertEqual(cursor.executed, [])

    def test_other_view_columns_are_not_revoked(self):
        # v_ai_product から product_code を外しても、v_ai_shipment が使うため REVOKE しない
        reduced = tuple(c for c in BASE_SQL_SCHEMA['v_ai_product'] if c != 'product_code')
        privileges, views = initial_state()
        privileges['m_product'] = {'id', 'product_code', 'product_name', 'created_at'}
        with patch.dict(BASE_SQL_SCHEMA, {'v_ai_product': reduced}):
            revokes = [sql for kind, sql in self.plan((privileges, views)) if kind == 'REVOKE']
        self.assertEqual(len(revokes), 1)
        self.assertIn('`created_at`', revokes[0])
        self.assertNotIn('product_code', revokes[0])
        self.assertNotIn('`id`', revokes[0])
        self.assertNotIn('product_name', revokes[0])

    def test_check_flags_table_level_select_and_no_revoke(self):
        # 検出するのは元テーブルの表全体のSELECTだけ。DB全体・グローバルの権限は、検出しない設計
        privileges, views = aligned_state()
        cursor = FakeCursor(privileges, views)
        cursor.table_select = {'m_line'}
        output = run(cursor, '--check')
        self.assertIn('m_line: [要対応] owner が表全体のSELECT権限を持つ', output)
        # 列権限がない状態(表全体のSELECTだけ)では REVOKE は出ない
        privileges['m_line'] = set()
        plan = self.plan((privileges, views), views=['v_ai_line'])
        self.assertEqual([kind for kind, sql in plan if kind == 'REVOKE'], [])
        self.assertEqual(cursor.executed, [])

    def test_create_condition_each_factor(self):
        def creates(definer=OWNER, security='DEFINER', reverse=False):
            privileges, views = aligned_state()
            columns = tuple(BASE_SQL_SCHEMA['v_ai_line'])
            views['v_ai_line'] = (definer, security, columns[::-1] if reverse else columns)
            return [sql for kind, sql in self.plan((privileges, views)) if kind == 'CREATE']

        self.assertEqual(creates(), [])
        for kwargs in ({'definer': 'root@localhost'}, {'security': 'INVOKER'}, {'reverse': True}):
            with self.subTest(**kwargs):
                result = creates(**kwargs)
                self.assertEqual(len(result), 1)
                self.assertIn('`v_ai_line`', result[0])

    def test_views_option_limits_targets(self):
        privileges, views = initial_state()
        cursor = FakeCursor(privileges, views)
        run(cursor, '--apply', '--views', 'v_ai_line')
        kinds = [s.split()[0] for s in cursor.executed]
        self.assertEqual(kinds, ['GRANT', 'CREATE'])
        self.assertTrue(all('`m_line`' in s for s in cursor.executed))
        for other in ('m_product', 'm_process', 'm_supplier', 'm_customer',
                      'v_ai_product', 'v_ai_process', 'v_ai_supplier', 'v_ai_customer'):
            self.assertFalse(any(other in s for s in cursor.executed))

    def test_apply_order_all_statements(self):
        privileges, views = initial_state()
        cursor = FakeCursor(privileges, views)
        run(cursor, '--apply')
        kinds = [s.split()[0] for s in cursor.executed]
        # ビューごとに GRANT(足りない列があるときだけ)→CREATE、最後にまとめて REVOKE
        expected = []
        for view, table in cmd.SIMPLE_MASTER_VIEWS.items():
            if any(c not in privileges.get(table, set()) for c in BASE_SQL_SCHEMA[view]):
                expected.append('GRANT')
            expected.append('CREATE')
        expected.append('REVOKE')
        self.assertEqual(kinds, expected)
        for index, sql in enumerate(cursor.executed):
            if sql.startswith('GRANT'):
                table = re.search(r'ON `\w+`\.`(\w+)`', sql).group(1)
                self.assertTrue(cursor.executed[index + 1].startswith('CREATE'))
                self.assertTrue(cursor.executed[index + 1].endswith(f'`{table}`'))

    def failing_apply(self, prefix):
        privileges, views = initial_state()
        cursor = FakeCursor(privileges, views)
        original = cursor.execute

        def failing(sql, params=None):
            if sql.startswith(prefix):
                raise RuntimeError('command denied')
            original(sql, params)

        cursor.execute = failing
        out = StringIO()
        with patch(f'{MODULE}.connection', fake_connection(cursor)):
            with self.assertRaises(CommandError) as ctx:
                call_command('setup_ai_views', '--apply', stdout=out)
        return cursor, out.getvalue(), str(ctx.exception)

    def test_check_reports_mismatch_and_reader_failure(self):
        privileges, views = initial_state()
        cursor = FakeCursor(privileges, views)
        output = run(cursor, '--check', reader_ok=False)
        self.assertEqual(cursor.executed, [])
        self.assertIn('[要対応]', output)
        self.assertIn('読めません', output)

    def test_failure_reports_sql_for_grant_create_revoke(self):
        for prefix in ('GRANT', 'CREATE', 'REVOKE'):
            with self.subTest(prefix=prefix):
                cursor, output, message = self.failing_apply(prefix)
                self.assertIn('管理者', message)
                self.assertIn(f'失敗したSQL: {prefix}', output)
                self.assertIn(f'実行済み: {len(cursor.executed)}件', output)
                for sql in cursor.executed:
                    self.assertIn(f'[OK] {sql}', output)
                if prefix == 'GRANT':
                    self.assertEqual(cursor.executed, [])
                if prefix == 'CREATE':
                    self.assertTrue(cursor.executed[0].startswith('GRANT'))
                if prefix == 'REVOKE':
                    self.assertTrue(cursor.executed[-1].startswith('CREATE'))
                    self.assertNotIn('[OK] REVOKE', output)
