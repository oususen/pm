"""一般工程の生産実績のビュー v_ai_process_production_actual の登録を検証する。

偽のDB接続・定義の検査だけを使い、開発DBへは接続しない(SimpleTestCaseのみ)。
business_dayの計算式(DATE(timestamp - INTERVAL 8 HOUR))とPython版resolve_workday_date_for_process()との
全件一致は、開発DBの実データで別に確認した(generatorの完了報告・AI用ビュー作成計画 §33に記録。全15,731件・不一致0件)。
"""
import re
from datetime import date, datetime, time, timedelta
from pathlib import Path

from django.test import SimpleTestCase

from ai.management.commands import setup_ai_views as cmd
from ai.services import analysis_execution_service as service
from ai.services.analysis_data_service import ANALYSIS_VIEWS, ai_view_definition, build_where, validate_datasets
from ai.services.analysis_plan_store import AnalysisError
from ai.services.sql_queries import BASE_SQL_SCHEMA, TABLE_NOTES
from orders.utils.calendar_utils import DAY_BOUNDARY_HOUR
from production.serializers_process_realtime import resolve_workday_date_for_process

VIEW = 'v_ai_process_production_actual'
PERIOD = ('2026-09-01', '2026-09-30')
# BOSSが決定した公開14列。順序はマイグレーションのSELECT順と同じ(AI用ビュー作成計画 §33)。
# 2026-10-17 BOSS判断でoperator_nameを公開に追加、event_dataを非公開に変更
# (event_dataはJSON型で、分析実行の値変換(_cell())が未対応のため実行が失敗する)
PUBLISHED = (
    'id', 'business_day', 'operator_login_id', 'operator_name', 'process_id', 'product_code', 'product_id',
    'product_name', 'qty', 'record_type', 'timestamp', 'equipment_state', 'interruption_reason_code', 'remarks',
)
# 非公開(ビューに含めない): batch_no, event_data
HIDDEN = ('batch_no', 'event_data')
MIGRATION = Path(__file__).parent / 'migrations' / '0055_ai_process_production_actual_view.py'


def migration_sql():
    return MIGRATION.read_text(encoding='utf-8').split('CREATE_VIEW = """')[1].split('"""')[0]


def migration_columns():
    """SELECTの列(business_dayは計算式のまま)を、別名(存在すれば)優先で、順序つきで返す。"""
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
        aliases.append(match.group(1) if match else column)
    return columns, aliases


class ProcessProductionActualViewDefinitionTest(SimpleTestCase):
    def test_view_is_registered_with_business_day_and_qty(self):
        definition = ANALYSIS_VIEWS[VIEW]
        self.assertEqual(definition['date_field'], 'business_day')
        self.assertEqual(definition['quantity_field'], 'qty')
        self.assertEqual(definition['label'], '一般工程生産実績')

    def test_column_types_match_published_columns_exactly(self):
        self.assertEqual(BASE_SQL_SCHEMA[VIEW], PUBLISHED)
        self.assertEqual(len(PUBLISHED), 14)
        self.assertEqual(set(service.ANALYSIS_COLUMN_TYPES[VIEW]), set(BASE_SQL_SCHEMA[VIEW]))
        self.assertEqual(service.ANALYSIS_COLUMN_TYPES[VIEW], {
            'id': 'BIGINT', 'business_day': 'DATE', 'operator_login_id': 'VARCHAR', 'operator_name': 'VARCHAR',
            'process_id': 'BIGINT', 'product_code': 'VARCHAR', 'product_id': 'BIGINT', 'product_name': 'VARCHAR',
            'qty': 'DECIMAL(18,3)', 'record_type': 'VARCHAR', 'timestamp': 'TIMESTAMP', 'equipment_state': 'VARCHAR',
            'interruption_reason_code': 'VARCHAR', 'remarks': 'VARCHAR',
        })

    def test_operator_name_is_published_and_event_data_is_hidden(self):
        # 2026-10-17 BOSS判断: operator_nameを公開列に追加、event_dataを非公開に変更
        # (event_dataはJSON型で、分析実行の値変換(_cell())が未対応のため、選択すると実行が失敗する)
        self.assertIn('operator_name', BASE_SQL_SCHEMA[VIEW])
        self.assertIn('operator_name', service.ANALYSIS_COLUMN_TYPES[VIEW])
        self.assertEqual(service.ANALYSIS_COLUMN_TYPES[VIEW]['operator_name'], 'VARCHAR')
        self.assertNotIn('event_data', BASE_SQL_SCHEMA[VIEW])
        self.assertNotIn('event_data', service.ANALYSIS_COLUMN_TYPES[VIEW])
        # ANALYSIS_COLUMN_TYPESにJSON型の列が残っていないこと(_cell()未対応による分析実行失敗の再発防止)
        self.assertNotIn('JSON', service.ANALYSIS_COLUMN_TYPES[VIEW].values())
        with self.assertRaises(AnalysisError):
            validate_datasets([{'view': VIEW, 'fields': ['business_day', 'event_data']}], *PERIOD)
        # operator_nameは公開列のため、validate_datasetsでエラーにならない
        datasets = [{'view': VIEW, 'fields': ['business_day', 'operator_name']}]
        self.assertEqual(validate_datasets(datasets, *PERIOD), datasets)

    def test_bool_and_id_types_match_existing_views(self):
        # id・timestamp・qty・varchar列の型は既存ビューと同じ表記
        types = service.ANALYSIS_COLUMN_TYPES
        self.assertEqual(types[VIEW]['id'], types['v_ai_customer']['id'])
        self.assertEqual(types[VIEW]['timestamp'], types['v_ai_purchase_receipt']['registered_at'])
        self.assertEqual(types[VIEW]['qty'], types['v_ai_purchase_receipt']['qty'])
        self.assertEqual(types[VIEW]['product_id'], types['v_ai_purchase_receipt']['product_id'])
        self.assertEqual(types[VIEW]['process_id'], types['v_ai_purchase_receipt']['process_id'])

    def test_ai_definition_has_date_and_quantity_field(self):
        definition = ai_view_definition(VIEW)
        self.assertEqual(set(definition), {'label', 'date_field', 'quantity_field', 'description'})
        self.assertNotIn(None, definition.values())

    def test_validate_datasets_requires_business_day(self):
        datasets = [{'view': VIEW, 'fields': ['id', 'business_day', 'qty']}]
        self.assertEqual(validate_datasets(datasets, *PERIOD), datasets)
        with self.assertRaises(AnalysisError):
            validate_datasets([{'view': VIEW, 'fields': ['id', 'qty']}], *PERIOD)
        for hidden in HIDDEN:
            with self.assertRaises(AnalysisError):
                validate_datasets([{'view': VIEW, 'fields': ['business_day', hidden]}], *PERIOD)

    def test_build_where_filters_by_business_day(self):
        self.assertEqual(
            build_where(VIEW, *PERIOD),
            (' WHERE `business_day` >= %s AND `business_day` <= %s', list(PERIOD)))
        self.assertEqual(
            build_where(VIEW, *PERIOD, last_id=9),
            (' WHERE `business_day` >= %s AND `business_day` <= %s AND `id` > %s', [*PERIOD, 9]))

    def test_description_has_required_notes_and_no_hidden_columns(self):
        for text in (ANALYSIS_VIEWS[VIEW]['description'], TABLE_NOTES[VIEW]):
            for part in (
                    'record_type=PRODUCTION', 'business_day', 'qty', 'process_id', 'product_id',
                    'operator_login_id', 'operator_name', 'remarks', 'interruption_reason_code'):
                self.assertIn(part, text)
            for hidden in ('batch_no', 'event_data'):
                self.assertNotIn(hidden, text)
        # interruption_reason_codeは、このビュー(PRODUCTION行のみ)では常に空文字になる旨を明記する
        self.assertIn('空文字', TABLE_NOTES[VIEW])
        self.assertIn('PAUSE', TABLE_NOTES[VIEW])
        self.assertIn('TEMP_END', TABLE_NOTES[VIEW])
        # operator_login_idはauth_user.usernameと結べる旨
        self.assertIn('username', TABLE_NOTES[VIEW])
        # business_dayは8時区切りの業務日計算列であり、稼働開始時刻が8時以外のラインが存在しないことの確認結果を明記する
        self.assertIn('8時', TABLE_NOTES[VIEW])
        self.assertIn('稼働開始時刻が8時以外のラインは存在しない', TABLE_NOTES[VIEW])
        # process_id・product_idはそれぞれv_ai_process・v_ai_productのidと結べる旨
        self.assertIn('v_ai_process', TABLE_NOTES[VIEW])
        self.assertIn('v_ai_product', TABLE_NOTES[VIEW])

    def test_setup_command_treats_this_view_as_not_simple(self):
        # WHERE句付きのため、単純なマスタビュー(SIMPLE_MASTER_VIEWS)には入れず、既存のv_ai_purchase_receipt等と
        # 同じ「再作成しない。--checkで定義者等を表示するだけ」の扱いにする
        self.assertIn(VIEW, cmd.EXISTING_JOIN_VIEWS)
        self.assertNotIn(VIEW, cmd.SIMPLE_MASTER_VIEWS)

    def test_migration_sql_has_no_mysql_specific_definer_syntax(self):
        sql = migration_sql()
        for banned in ('`', 'DEFINER', 'SQL SECURITY', 'pm_db', 'INNER', 'LEFT JOIN', 'RIGHT', 'CROSS', 'GROUP', 'UNION', 'JOIN'):
            self.assertNotIn(banned, sql)
        self.assertIn('CREATE OR REPLACE VIEW v_ai_process_production_actual AS', sql)
        self.assertIn("WHERE record_type = 'PRODUCTION'", sql)
        self.assertEqual(sql.count('WHERE'), 1)
        self.assertIn('FROM t_process_realtime_record', sql)
        for hidden in HIDDEN:
            self.assertNotIn(hidden, sql)

    def test_migration_columns_match_base_sql_schema_order(self):
        columns, aliases = migration_columns()
        self.assertEqual(tuple(aliases), PUBLISHED)
        # business_dayだけが計算式で、他の13列は素のカラム名
        self.assertEqual(columns[1].strip(), 'DATE(timestamp - INTERVAL 8 HOUR) AS business_day')
        for column, alias in zip(columns, aliases):
            if alias != 'business_day':
                self.assertEqual(column.strip(), alias)

    def test_migration_dependencies(self):
        source = MIGRATION.read_text(encoding='utf-8')
        self.assertIn("('ai', '0054_ai_equipment_view')", source)
        self.assertIn("('production', '0124_processrealtimerecord_interruption_reason_code')", source)
        self.assertIn("DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_process_production_actual'", source)

    def test_migration_dependency_migrations_exist_and_cover_source_columns(self):
        production = Path(__file__).parent.parent / 'production' / 'migrations'
        interruption = production / '0124_processrealtimerecord_interruption_reason_code.py'
        login_id = production / '0119_process_realtime_operator_login_id.py'
        self.assertTrue(interruption.exists())
        self.assertTrue(login_id.exists())
        self.assertIn("'interruption_reason_code'", interruption.read_text(encoding='utf-8'))
        self.assertIn("'operator_login_id'", login_id.read_text(encoding='utf-8'))

    def test_existing_view_definitions_in_migrations_are_unchanged(self):
        # 既存ビューのマイグレーションに、このビューが混入していない
        for path in (Path(__file__).parent / 'migrations').glob('00[0-4]*.py'):
            if path.name == '0055_ai_process_production_actual_view.py':
                continue
            self.assertNotIn(VIEW, path.read_text(encoding='utf-8'), path.name)


class BusinessDayFormulaBoundaryTest(SimpleTestCase):
    """DB不要で検証できる範囲(8時境界・processなし)で、簡易式とresolve_workday_date_for_process()の一致を確認する。

    カレンダ(勤務パターン)に依存する分岐は、開発DBの実データ全件(15,731件・不一致0件)で別に確認済み
    (generatorの完了報告・AI用ビュー作成計画 §33)。この自動試験は、DBに依存しない2つの分岐(8時より前は前日、
    processなしは当日)だけを対象にする。
    """
    def simple_business_day(self, dt):
        return (dt - timedelta(hours=DAY_BOUNDARY_HOUR)).date()

    def test_before_8am_is_previous_day_in_both_formulas(self):
        for dt in (datetime(2026, 1, 19, 7, 59, 59), datetime(2026, 1, 19, 0, 0, 0), datetime(2026, 1, 1, 7, 59, 59, 999999)):
            with self.subTest(dt=dt):
                self.assertEqual(self.simple_business_day(dt), resolve_workday_date_for_process(None, dt))
                self.assertEqual(resolve_workday_date_for_process(None, dt), (dt.date() - timedelta(days=1)))

    def test_8am_or_later_without_process_is_same_day_in_both_formulas(self):
        for dt in (datetime(2026, 1, 19, 8, 0, 0), datetime(2026, 1, 19, 8, 0, 1), datetime(2026, 1, 19, 23, 59, 59)):
            with self.subTest(dt=dt):
                self.assertEqual(self.simple_business_day(dt), resolve_workday_date_for_process(None, dt))
                self.assertEqual(resolve_workday_date_for_process(None, dt), dt.date())

    def test_day_boundary_hour_is_8(self):
        self.assertEqual(DAY_BOUNDARY_HOUR, 8)
