"""AI用ビューの権限付与と定義者の付け替えを、まとめて行う管理コマンド(MySQL専用)。

`migrate` で作ったビューの定義者は、実行したDBユーザー(root等)になる。AI用ビュー作成計画 §4.1-9 の原則
(定義者は専用ユーザー pm_ai_view_owner)に合わせて、管理者が migrate の後に1回実行する。
  1. owner へ、ビューが読む元テーブルの公開列だけの列単位SELECTを付与する
  2. CREATE OR REPLACE DEFINER = owner SQL SECURITY DEFINER VIEW でビューを作り直す
  3. owner が元テーブルに持つ列権限のうち、公開列の和集合にない列を REVOKE する(最小権限)

既定は表示のみ(dry-run)。--apply を付けたときだけ実行する。MySQL固有の処理は、このコマンドに閉じ込める。
"""
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, connections

from ai.services.query_common import AI_DB_ALIAS
from ai.services.sql_queries import BASE_SQL_SCHEMA

# 単純なマスタビュー(1テーブル・結合なし・全行)と元テーブルの対応。列は BASE_SQL_SCHEMA[ビュー名] から取る。
# 新しい単純なマスタビューを足すときは、ここに1行足すだけにする。
SIMPLE_MASTER_VIEWS = {
    'v_ai_product': 'm_product',
    'v_ai_process': 'm_process',
    'v_ai_line': 'm_line',
    'v_ai_supplier': 'm_supplier',
    'v_ai_customer': 'm_customer',
}

# 結合を含み、定義がマイグレーション(0012〜0014・0040)にあるビュー。再作成しない。--check で定義者などを表示するだけ。
EXISTING_JOIN_VIEWS = ('v_ai_shipment', 'v_ai_purchase_receipt', 'v_ai_calendar_day')

# 単純なマスタビュー以外のビューが、同じ元テーブルから使う列。owner のこの列権限は REVOKE しない。
# v_ai_shipment が m_product の id・product_code・product_name を使う(t_shipment_actual の列は対象外)。
# v_ai_calendar_day(m_calendar_day に m_calendar を LEFT JOIN。マイグレーション0040)が、
# m_calendar_day の9列と m_calendar の4列を使う。
OTHER_VIEW_COLUMNS = {
    'm_product': {'id', 'product_code', 'product_name'},
    'm_calendar_day': {
        'id', 'calendar_id', 'target_date', 'is_working_day', 'is_delivery_day', 'is_order_day',
        'is_holiday_work', 'work_minutes', 'work_pattern_id',
    },
    'm_calendar': {'id', 'calendar_code', 'calendar_name', 'calendar_type'},
}

READER_USER = 'pm_ai_reader'
NAME_PATTERN = re.compile(r'^[A-Za-z0-9_.%-]+$')


def quote_identifier(name):
    """識別子をバッククォートで囲む。中にバッククォートがある名前は拒否する。"""
    if not isinstance(name, str) or not name or '`' in name:
        raise CommandError(f'不正な識別子です: {name!r}')
    return f'`{name}`'


def check_account_part(value, label):
    """ユーザー名・ホスト名を検査する。"""
    if not isinstance(value, str) or not NAME_PATTERN.fullmatch(value):
        raise CommandError(f'{label}に使えない文字があります: {value!r}')
    return value


def account(user, host):
    return f"'{user}'@'{host}'"


def wanted_columns(table):
    """元テーブルについて、owner に持たせる列(同じ元テーブルを使う全ビューの公開列の和集合)。"""
    columns = set(OTHER_VIEW_COLUMNS.get(table, set()))
    for view, source in SIMPLE_MASTER_VIEWS.items():
        if source == table:
            columns.update(BASE_SQL_SCHEMA[view])
    return columns


def fetch_rows(cursor, sql, params):
    cursor.execute(sql, params)
    return cursor.fetchall()


def read_column_privileges(cursor, db, owner_account, table):
    """owner が元テーブルに持つSELECTの列権限を読む。"""
    rows = fetch_rows(
        cursor,
        "SELECT COLUMN_NAME FROM information_schema.COLUMN_PRIVILEGES "
        "WHERE GRANTEE = %s AND TABLE_SCHEMA = %s AND TABLE_NAME = %s AND PRIVILEGE_TYPE = 'SELECT'",
        [owner_account, db, table],
    )
    return {row[0] for row in rows}


def has_table_level_select(cursor, db, owner_account, table):
    # 検出するのは元テーブルへの表全体のSELECTだけ。DB全体(SCHEMA_PRIVILEGES)・グローバル(USER_PRIVILEGES)の権限は、検出しない設計。
    rows = fetch_rows(
        cursor,
        "SELECT 1 FROM information_schema.TABLE_PRIVILEGES "
        "WHERE GRANTEE = %s AND TABLE_SCHEMA = %s AND TABLE_NAME = %s AND PRIVILEGE_TYPE = 'SELECT'",
        [owner_account, db, table],
    )
    return bool(rows)


def read_view_state(cursor, db, view):
    """ビューの定義者・SECURITY_TYPE・列(順序つき)を読む。ビューがなければ None。"""
    rows = fetch_rows(
        cursor,
        'SELECT DEFINER, SECURITY_TYPE FROM information_schema.VIEWS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s',
        [db, view],
    )
    if not rows:
        return None
    columns = fetch_rows(
        cursor,
        'SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s '
        'ORDER BY ORDINAL_POSITION',
        [db, view],
    )
    return {'definer': rows[0][0], 'security_type': rows[0][1], 'columns': tuple(c[0] for c in columns)}


def build_plan(cursor, db, owner, owner_host, views, reader_host=None):
    """実行するSQLを、(種別, SQL)の順序つき一覧で作る。GRANT→CREATE(→reader GRANT)→REVOKE の順。"""
    owner_account = account(owner, owner_host)
    expected_definer = f'{owner}@{owner_host}'
    q_db = quote_identifier(db)
    q_owner = account(owner, owner_host)
    plan = []
    revokes = []
    tables = []
    granted = {}
    current = {}
    for view in views:
        table = SIMPLE_MASTER_VIEWS[view]
        columns = BASE_SQL_SCHEMA[view]
        if table not in current:
            current[table] = read_column_privileges(cursor, db, owner_account, table)
            granted[table] = set()
            tables.append(table)
        q_table = quote_identifier(table)
        q_view = quote_identifier(view)
        # 1. 足りない列だけ GRANT(権限がすでに揃っていれば実行しない)
        missing = [c for c in columns if c not in current[table] and c not in granted[table]]
        if missing:
            column_sql = ', '.join(quote_identifier(c) for c in missing)
            plan.append(('GRANT', f'GRANT SELECT ({column_sql}) ON {q_db}.{q_table} TO {q_owner}'))
            granted[table].update(missing)
        # 2. 定義者・SECURITY_TYPE・列が期待と違うときだけ、ビューを作り直す
        state = read_view_state(cursor, db, view)
        aligned = (
            state is not None
            and state['definer'] == expected_definer
            and str(state['security_type']).upper() == 'DEFINER'
            and state['columns'] == tuple(columns)
        )
        if not aligned:
            column_sql = ', '.join(quote_identifier(c) for c in columns)
            plan.append((
                'CREATE',
                f'CREATE OR REPLACE DEFINER = {q_owner} SQL SECURITY DEFINER VIEW {q_db}.{q_view} AS '
                f'SELECT {column_sql} FROM {q_db}.{q_table}',
            ))
        if reader_host:
            plan.append(('READER_GRANT', f'GRANT SELECT ON {q_db}.{q_view} TO {account(READER_USER, reader_host)}'))
    # 3. 公開列の和集合にない列権限を REVOKE(最小権限)
    for table in tables:
        extra = sorted(current[table] - wanted_columns(table))
        if extra:
            column_sql = ', '.join(quote_identifier(c) for c in extra)
            revokes.append(('REVOKE', f'REVOKE SELECT ({column_sql}) ON {q_db}.{quote_identifier(table)} FROM {q_owner}'))
    return plan + revokes


def run_check(cursor, stdout, db, owner, owner_host, views, reader_check=True):
    """読み取りのみの確認。要対応の件数を返す。"""
    owner_account = account(owner, owner_host)
    expected_definer = f'{owner}@{owner_host}'
    problems = 0
    stdout.write('--- 確認(--check) ---')
    for view in views:
        table = SIMPLE_MASTER_VIEWS.get(view)
        state = read_view_state(cursor, db, view)
        if state is None:
            stdout.write(f'[要対応] {view}: ビューがありません(migrate が必要)')
            problems += 1
            continue
        definer_ok = state['definer'] == expected_definer
        security_ok = str(state['security_type']).upper() == 'DEFINER'
        line = f'{view}: 定義者={state["definer"]} SECURITY_TYPE={state["security_type"]}'
        if not (definer_ok and security_ok):
            line += f' [要対応: 期待は {expected_definer} / DEFINER]'
            problems += 1
        stdout.write(line)
        if table is not None:
            expected_columns = tuple(BASE_SQL_SCHEMA[view])
            if state['columns'] == expected_columns:
                stdout.write(f'  列: BASE_SQL_SCHEMA と一致({len(expected_columns)}列)')
            else:
                stdout.write(f'  列: [要対応] 不一致 実際={list(state["columns"])} 期待={list(expected_columns)}')
                problems += 1
    for table in sorted({SIMPLE_MASTER_VIEWS[v] for v in views if v in SIMPLE_MASTER_VIEWS}):
        wanted = wanted_columns(table)
        current = read_column_privileges(cursor, db, owner_account, table)
        if has_table_level_select(cursor, db, owner_account, table):
            stdout.write(f'{table}: [要対応] owner が表全体のSELECT権限を持つ(列単位に絞れていない。手動で確認)')
            problems += 1
        if current == wanted:
            stdout.write(f'{table}: owner の列権限は公開列の和集合と一致({len(wanted)}列)')
        else:
            stdout.write(
                f'{table}: [要対応] owner の列権限が不一致 不足={sorted(wanted - current)} 余分={sorted(current - wanted)}'
            )
            problems += 1
    if reader_check:
        for view in views:
            try:
                with connections[AI_DB_ALIAS].cursor() as reader:
                    reader.execute(f'SELECT 1 FROM {quote_identifier(view)} LIMIT 1')
                    reader.fetchall()
                stdout.write(f'{AI_DB_ALIAS} 接続で {view} を読めます')
            except Exception as exc:  # 失敗しても確認を続ける
                stdout.write(f'[要対応] {AI_DB_ALIAS} 接続で {view} を読めません: {exc}')
                problems += 1
    stdout.write(f'要対応: {problems}件')
    return problems


class Command(BaseCommand):
    help = 'AI用ビューの権限付与と定義者の付け替えを行う(MySQL専用)。既定は表示のみ。--apply で実行する。管理者(rootなど)で実行する。'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='SQLを実際に実行する(既定は表示のみ)')
        parser.add_argument('--check', action='store_true', help='読み取りのみで、定義者・列・権限・readerの読み取りを確認する')
        parser.add_argument('--owner', default='pm_ai_view_owner', help='ビューの定義者(既定 pm_ai_view_owner)')
        parser.add_argument('--owner-host', default='localhost', help='定義者のホスト部(既定 localhost)')
        parser.add_argument('--views', nargs='+', help='対象のビューを絞る(既定は全部)')
        parser.add_argument('--reader-host', help=f'指定したときだけ {READER_USER} へビューのSELECTを付与する')

    def handle(self, *args, **options):
        if connection.vendor != 'mysql':
            self.stdout.write('PostgreSQL版は、移行時に作る。何もしない')
            return
        owner = check_account_part(options['owner'], '--owner')
        owner_host = check_account_part(options['owner_host'], '--owner-host')
        reader_host = options.get('reader_host')
        if reader_host:
            check_account_part(reader_host, '--reader-host')
        db = connection.settings_dict['NAME']
        quote_identifier(db)

        simple = list(SIMPLE_MASTER_VIEWS)
        known = simple + list(EXISTING_JOIN_VIEWS)
        requested = options.get('views')
        if requested:
            unknown = [v for v in requested if v not in known]
            if unknown:
                raise CommandError(f'対象外のビューです: {unknown}(対象: {known})')
            selected = [v for v in known if v in requested]
        else:
            selected = known
        rebuild_views = [v for v in selected if v in SIMPLE_MASTER_VIEWS]
        apply = options['apply']

        with connection.cursor() as cursor:
            if apply or not options['check']:
                plan = build_plan(cursor, db, owner, owner_host, rebuild_views, reader_host)
                self.execute_plan(cursor, plan, apply)
                if not reader_host:
                    self.stdout.write(
                        f'(参考・実行しない) {READER_USER} へのビューのSELECT付与は、--reader-host を指定したときだけ実行する'
                    )
            if apply or options['check']:
                run_check(cursor, self.stdout, db, owner, owner_host, selected)

    def execute_plan(self, cursor, plan, apply):
        if not plan:
            self.stdout.write('実行するSQLはありません(すでに揃っています)')
            return
        if not apply:
            self.stdout.write('--- 実行予定のSQL(表示のみ。実行するには --apply) ---')
            for kind, sql in plan:
                self.stdout.write(f'[{kind}] {sql};')
            return
        self.stdout.write('--- SQLを実行します ---')
        done = []
        for kind, sql in plan:
            try:
                cursor.execute(sql)
            except Exception as exc:
                self.stdout.write(f'実行済み: {len(done)}件')
                for item in done:
                    self.stdout.write(f'  [OK] {item}')
                self.stdout.write(f'失敗したSQL: {sql}')
                raise CommandError(
                    f'SQLの実行に失敗しました({exc})。GRANT・CREATE ... DEFINER に必要な権限がない可能性があります。'
                    '管理者(rootなど)で実行してください。'
                ) from exc
            done.append(sql)
            self.stdout.write(f'[実行] {kind}: {sql}')
