"""一般工程の中断・強制終了のビュー v_ai_process_interruption の登録を検証する。

偽のDB接続・定義の検査だけを使う試験(SimpleTestCase)と、開発DBへ読み取りだけを行う件数照合試験(DBCountMatchTest)を分ける。
本ビューは`t_process_work_session`に`t_process_realtime_record`をLEFT JOINするため、`SIMPLE_MASTER_VIEWS`ではなく
`EXISTING_JOIN_VIEWS`で扱う(既存の`v_ai_brake_interruption`・`v_ai_laser_interruption`と同じ扱い)。
`interruption_reason`は新規の計算列(interruption_reason_code優先、空ならevent_data(JSON)から抽出)のため、
その優先順位が実データで期待どおりになっていることを個別に検証する。
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

VIEW = 'v_ai_process_interruption'
PERIOD = ('2026-09-01', '2026-09-30')
# BOSSが決定した公開16列(全22列中)。順序はマイグレーションのSELECT順と同じ(AI用ビュー作成計画 次セクション)。
PUBLISHED = (
    'id', 'product_code', 'product_name', 'plan_date', 'session_no', 'session_type', 'start_action',
    'end_action', 'started_at', 'ended_at', 'duration_seconds', 'process_id', 'product_id',
    'operator_name', 'operator_login_id', 'interruption_reason',
)
# 非公開6列: status・production_qty・issue_count・issue_flags・defect_qty・equipment_via_session(結合案。カバレッジ低のため非公開)
HIDDEN = ('status', 'production_qty', 'issue_count', 'issue_flags', 'defect_qty', 'equipment_via_session')
MIGRATION = Path(__file__).parent / 'migrations' / '0061_ai_process_interruption_view.py'


def migration_sql():
    return MIGRATION.read_text(encoding='utf-8').split('CREATE_VIEW = """')[1].split('"""')[0]


def migration_columns():
    """SELECTの列を、別名(存在すれば)優先、なければ列名そのもので、順序つきで返す。"""
    body = re.search(r'SELECT(.*)FROM', migration_sql(), re.S).group(1)
    # interruption_reason列はCOALESCE(...)の複数行の式のため、トップレベルの括弧の対応を見てカンマで分割する
    columns = []
    depth = 0
    current = ''
    for ch in body:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if ch == ',' and depth == 0:
            columns.append(current.strip())
            current = ''
        else:
            current += ch
    if current.strip():
        columns.append(current.strip())
    aliases = []
    for column in columns:
        match = re.search(r'\bAS\s+(\w+)\s*$', column, re.S)
        if match:
            aliases.append(match.group(1))
        else:
            aliases.append(column.split('.')[-1].strip())
    return columns, aliases


class ProcessInterruptionViewDefinitionTest(SimpleTestCase):
    def test_view_is_registered_with_plan_date_and_no_quantity_field(self):
        definition = ANALYSIS_VIEWS[VIEW]
        self.assertEqual(definition['date_field'], 'plan_date')
        self.assertIsNone(definition['quantity_field'])
        self.assertEqual(definition['label'], '一般工程中断')

    def test_column_types_match_published_columns_exactly(self):
        self.assertEqual(BASE_SQL_SCHEMA[VIEW], PUBLISHED)
        self.assertEqual(len(PUBLISHED), 16)
        self.assertEqual(set(service.ANALYSIS_COLUMN_TYPES[VIEW]), set(BASE_SQL_SCHEMA[VIEW]))
        self.assertEqual(service.ANALYSIS_COLUMN_TYPES[VIEW], {
            'id': 'BIGINT', 'product_code': 'VARCHAR', 'product_name': 'VARCHAR', 'plan_date': 'DATE',
            'session_no': 'BIGINT', 'session_type': 'VARCHAR', 'start_action': 'VARCHAR', 'end_action': 'VARCHAR',
            'started_at': 'TIMESTAMP', 'ended_at': 'TIMESTAMP', 'duration_seconds': 'BIGINT', 'process_id': 'BIGINT',
            'product_id': 'BIGINT', 'operator_name': 'VARCHAR', 'operator_login_id': 'VARCHAR',
            'interruption_reason': 'VARCHAR',
        })
        # JSON型の列が混入していないこと(分析実行の値変換が未対応のため実行が失敗する再発防止)
        self.assertNotIn('JSON', service.ANALYSIS_COLUMN_TYPES[VIEW].values())

    def test_hidden_columns_do_not_appear_anywhere(self):
        columns, aliases = migration_columns()
        sql = migration_sql()
        for hidden in HIDDEN:
            self.assertNotIn(hidden, aliases)
            self.assertNotIn(hidden, BASE_SQL_SCHEMA[VIEW])
            self.assertNotIn(hidden, service.ANALYSIS_COLUMN_TYPES[VIEW])
            self.assertNotRegex(TABLE_NOTES[VIEW], rf'\b{hidden}\b')
            self.assertNotRegex(ANALYSIS_VIEWS[VIEW]['description'], rf'\b{hidden}\b')
            self.assertNotRegex(sql, rf'\b{hidden}\b')

    def test_ai_definition_has_date_field_and_omits_quantity_field(self):
        # ai_view_definitionは値がNoneのキー(quantity_field)を出さない仕様(v_ai_laser_interruptionと同じ)
        definition = ai_view_definition(VIEW)
        self.assertEqual(set(definition), {'label', 'date_field', 'description'})
        self.assertNotIn(None, definition.values())

    def test_validate_datasets_requires_plan_date_and_rejects_hidden_columns(self):
        datasets = [{'view': VIEW, 'fields': ['id', 'plan_date', 'interruption_reason']}]
        self.assertEqual(validate_datasets(datasets, *PERIOD), datasets)
        with self.assertRaises(AnalysisError):
            validate_datasets([{'view': VIEW, 'fields': ['id', 'interruption_reason']}], *PERIOD)
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
                    'plan_date', 'PAUSE', 'TEMP_END', 'session_type', 'end_action', 'interruption_reason_code',
                    'event_data', 'pause_reason', 'temp_end_reason', 'operator_action_reason', 'operator_name'):
                self.assertIn(part, text)
        # session_typeとend_actionの関係(end_action=PAUSEはsession_type=WORK、end_action=TEMP_ENDはsession_type=PAUSE)を明記
        self.assertIn('WORK', TABLE_NOTES[VIEW])
        # operator_nameが個人名である旨
        self.assertIn('個人名', TABLE_NOTES[VIEW])
        # 開発DB確認の120件(PAUSE97・TEMP_END23)である旨
        self.assertIn('120', TABLE_NOTES[VIEW])
        self.assertIn('97', TABLE_NOTES[VIEW])
        self.assertIn('23', TABLE_NOTES[VIEW])

    def test_setup_command_treats_this_view_as_not_simple(self):
        self.assertIn(VIEW, cmd.EXISTING_JOIN_VIEWS)
        self.assertNotIn(VIEW, cmd.SIMPLE_MASTER_VIEWS)

    def test_migration_sql_has_no_mysql_specific_definer_syntax(self):
        sql = migration_sql()
        for banned in ('`', 'DEFINER', 'SQL SECURITY', 'pm_db'):
            self.assertNotIn(banned, sql)
        self.assertIn('CREATE OR REPLACE VIEW v_ai_process_interruption AS', sql)
        self.assertIn('FROM t_process_work_session s', sql)
        self.assertEqual(sql.count('WHERE'), 1)
        self.assertIn("s.end_action IN ('PAUSE', 'TEMP_END')", sql)

    def test_migration_sql_has_left_join_on_end_record_id(self):
        sql = migration_sql()
        self.assertIn('LEFT JOIN t_process_realtime_record r ON r.id = s.end_record_id', sql)
        self.assertEqual(sql.count('JOIN'), 1)

    def test_migration_sql_interruption_reason_priority_order(self):
        """COALESCEの優先順位(コード→pause_reason→temp_end_reason→operator_action_reason)がSQLに書かれていること"""
        sql = migration_sql()
        code_pos = sql.index('interruption_reason_code')
        pause_pos = sql.index('pause_reason')
        temp_end_pos = sql.index('temp_end_reason')
        operator_pos = sql.index('operator_action_reason')
        self.assertTrue(code_pos < pause_pos < temp_end_pos < operator_pos)
        self.assertIn('JSON_UNQUOTE', sql)
        self.assertIn('JSON_EXTRACT', sql)
        self.assertIn('COALESCE', sql)

    def test_migration_columns_match_base_sql_schema_order(self):
        columns, aliases = migration_columns()
        self.assertEqual(tuple(aliases), PUBLISHED)
        self.assertEqual(len(columns), 16)

    def test_migration_dependencies(self):
        source = MIGRATION.read_text(encoding='utf-8')
        self.assertIn("('ai', '0060_ai_brake_interruption_view')", source)
        self.assertIn("DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_process_interruption'", source)

    def test_existing_view_definitions_in_migrations_are_unchanged(self):
        # 既存ビューのマイグレーション(0001〜0060)に、このビューが混入していない
        for path in (Path(__file__).parent / 'migrations').glob('00[0-5]*.py'):
            self.assertNotIn(VIEW, path.read_text(encoding='utf-8'), path.name)
        migration_0060 = Path(__file__).parent / 'migrations' / '0060_ai_brake_interruption_view.py'
        self.assertNotIn(VIEW, migration_0060.read_text(encoding='utf-8'))


class ProcessInterruptionDBCountMatchTest(SimpleTestCase):
    """開発DBの実データで、ビューの件数と独立計算した期待件数が一致することを確認する(検証項目A)。

    本ビューは2026-10-18時点で`migrate`未実行のため、`v_ai_process_interruption`が存在しない間は、
    期待値だけを計算してスキップする(BOSSの指示でmigrate実行後に本試験が有効になる)。
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
                "SELECT COUNT(*) FROM t_process_work_session WHERE end_action IN ('PAUSE', 'TEMP_END')")
            expected = cursor.fetchone()[0]
            if not view_exists:
                self.skipTest(
                    f'v_ai_process_interruption は未作成(migrate未実行)のため件数照合をスキップ。'
                    f'独立計算の期待件数={expected}(2026-10-18 generator確認時点)。migrate実行後に本試験で照合する。')
            cursor.execute(f'SELECT COUNT(*) FROM `{VIEW}`')
            actual = cursor.fetchone()[0]
            cursor.close()
        finally:
            connection.close()
        self.assertEqual(actual, expected)

    def test_action_breakdown_matches_db(self):
        """end_action別の件数(PAUSE・TEMP_END)、およびsession_typeとの対応関係を実データで検証する。"""
        connection = service.open_snapshot_connection(service.Deadline(30, 'stage_deadline_fetch'), read_timeout=30)
        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT "
                "SUM(CASE WHEN end_action = 'PAUSE' THEN 1 ELSE 0 END), "
                "SUM(CASE WHEN end_action = 'TEMP_END' THEN 1 ELSE 0 END), "
                "COUNT(*) "
                "FROM t_process_work_session WHERE end_action IN ('PAUSE', 'TEMP_END')")
            pause, temp_end, total = cursor.fetchone()
            # end_action=PAUSEの行はsession_type=WORK、end_action=TEMP_ENDの行はsession_type=PAUSEであること
            cursor.execute(
                "SELECT COUNT(*) FROM t_process_work_session "
                "WHERE end_action = 'PAUSE' AND session_type <> 'WORK'")
            pause_mismatch = cursor.fetchone()[0]
            cursor.execute(
                "SELECT COUNT(*) FROM t_process_work_session "
                "WHERE end_action = 'TEMP_END' AND session_type <> 'PAUSE'")
            temp_end_mismatch = cursor.fetchone()[0]
            cursor.close()
        finally:
            connection.close()
        # 2026-10-18 generator確認時点の開発DB実データ
        self.assertEqual(total, 120)
        self.assertEqual(pause, 97)
        self.assertEqual(temp_end, 23)
        self.assertEqual(pause_mismatch, 0)
        self.assertEqual(temp_end_mismatch, 0)

    def test_interruption_reason_priority_matches_db(self):
        """interruption_reason計算列の優先順位(コード優先・JSON抽出フォールバック)が実データで期待どおりになっていることを検証する。"""
        connection = service.open_snapshot_connection(service.Deadline(30, 'stage_deadline_fetch'), read_timeout=30)
        try:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT
                  SUM(CASE WHEN NULLIF(r.interruption_reason_code,'') IS NOT NULL THEN 1 ELSE 0 END) AS code_cnt,
                  SUM(CASE WHEN NULLIF(r.interruption_reason_code,'') IS NULL
                           AND NULLIF(JSON_UNQUOTE(JSON_EXTRACT(r.event_data,'$.pause_reason')),'') IS NOT NULL
                       THEN 1 ELSE 0 END) AS pause_json,
                  SUM(CASE WHEN NULLIF(r.interruption_reason_code,'') IS NULL
                           AND NULLIF(JSON_UNQUOTE(JSON_EXTRACT(r.event_data,'$.pause_reason')),'') IS NULL
                           AND NULLIF(JSON_UNQUOTE(JSON_EXTRACT(r.event_data,'$.temp_end_reason')),'') IS NOT NULL
                       THEN 1 ELSE 0 END) AS temp_end_json,
                  SUM(CASE WHEN NULLIF(r.interruption_reason_code,'') IS NULL
                           AND NULLIF(JSON_UNQUOTE(JSON_EXTRACT(r.event_data,'$.pause_reason')),'') IS NULL
                           AND NULLIF(JSON_UNQUOTE(JSON_EXTRACT(r.event_data,'$.temp_end_reason')),'') IS NULL
                           AND NULLIF(JSON_UNQUOTE(JSON_EXTRACT(r.event_data,'$.operator_action_reason')),'') IS NOT NULL
                       THEN 1 ELSE 0 END) AS op_action_json,
                  SUM(CASE WHEN COALESCE(
                           NULLIF(r.interruption_reason_code,''),
                           NULLIF(JSON_UNQUOTE(JSON_EXTRACT(r.event_data,'$.pause_reason')),''),
                           NULLIF(JSON_UNQUOTE(JSON_EXTRACT(r.event_data,'$.temp_end_reason')),''),
                           NULLIF(JSON_UNQUOTE(JSON_EXTRACT(r.event_data,'$.operator_action_reason')),'')
                       ) IS NULL THEN 1 ELSE 0 END) AS none_cnt,
                  COUNT(*) AS total
                FROM t_process_work_session s
                LEFT JOIN t_process_realtime_record r ON r.id = s.end_record_id
                WHERE s.end_action IN ('PAUSE','TEMP_END')
            """)
            code_cnt, pause_json, temp_end_json, op_action_json, none_cnt, total = cursor.fetchone()
            cursor.close()
        finally:
            connection.close()
        # 2026-10-18 generator確認時点の開発DB実データ
        self.assertEqual(total, 120)
        self.assertEqual(code_cnt, 5)
        self.assertEqual(pause_json, 85)
        self.assertEqual(temp_end_json, 22)
        self.assertEqual(op_action_json, 0)
        self.assertEqual(none_cnt, 8)
        # コード・JSON合計の非NULLが112件(約93%)であること
        self.assertEqual(code_cnt + pause_json + temp_end_json + op_action_json, 112)

    def test_operator_name_is_mostly_blank_with_one_real_name(self):
        """operator_nameの実データ(ほとんど空文字、ごく一部に実名)を確認する。"""
        connection = service.open_snapshot_connection(service.Deadline(30, 'stage_deadline_fetch'), read_timeout=30)
        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT "
                "SUM(CASE WHEN operator_name = '' THEN 1 ELSE 0 END), "
                "SUM(CASE WHEN operator_name <> '' THEN 1 ELSE 0 END) "
                "FROM t_process_work_session WHERE end_action IN ('PAUSE', 'TEMP_END')")
            blank, non_blank = cursor.fetchone()
            cursor.close()
        finally:
            connection.close()
        # 2026-10-18 generator確認時点の開発DB実データ
        self.assertEqual(blank, 119)
        self.assertEqual(non_blank, 1)
