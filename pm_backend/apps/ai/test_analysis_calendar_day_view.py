"""稼働カレンダのビュー v_ai_calendar_day の登録を検証する。

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

CALENDAR_DAY = 'v_ai_calendar_day'
EXISTING_VIEWS = (
    'v_ai_shipment', 'v_ai_purchase_receipt', 'v_ai_product', 'v_ai_process', 'v_ai_line', 'v_ai_supplier',
    'v_ai_customer')
PERIOD = ('2026-09-01', '2026-09-30')
PUBLISHED = (
    'id', 'calendar_id', 'calendar_code', 'calendar_name', 'calendar_type', 'target_date', 'is_working_day',
    'is_delivery_day', 'is_order_day', 'is_holiday_work', 'work_minutes', 'work_pattern_id')
# 非公開(ビューに含めない): m_calendar_day の note・created_at・updated_at と、m_calendar の他の列
HIDDEN = (
    'note', 'created_at', 'updated_at', 'description', 'is_line_assignable', 'is_supplier_assignable',
    'created_by', 'updated_by')
# v_ai_calendar_day 追加前の、既存7ビューのAIへ渡す定義(fields付き)のJSONのSHA-256。1文字でも変わると不一致になる
# (v_ai_calendar_day を追加した後の現行コードで計算。うち既存6ビューの値は、得意先ビューの試験の固定値 8ca47c57… と別に確認済み)
EXISTING_DEFINITION_SHA256 = 'db31acbfe065946a26dc439a40b4076ca41530869749bedf1f92e06600a410ed'
MIGRATION = Path(__file__).parent / 'migrations' / '0040_ai_calendar_day_view.py'


def migration_sql():
    return MIGRATION.read_text(encoding='utf-8').split('CREATE_VIEW = """')[1].split('"""')[0]


class CalendarDayViewDefinitionTest(SimpleTestCase):
    def test_calendar_day_view_is_registered_with_date_field(self):
        definition = ANALYSIS_VIEWS[CALENDAR_DAY]
        self.assertEqual(definition['date_field'], 'target_date')
        self.assertIsNone(definition['quantity_field'])
        self.assertEqual(definition['label'], '稼働カレンダ')

    def test_column_types_match_published_columns_exactly(self):
        self.assertEqual(BASE_SQL_SCHEMA[CALENDAR_DAY], PUBLISHED)
        self.assertEqual(len(PUBLISHED), 12)
        self.assertEqual(set(service.ANALYSIS_COLUMN_TYPES[CALENDAR_DAY]), set(BASE_SQL_SCHEMA[CALENDAR_DAY]))
        self.assertEqual(service.ANALYSIS_COLUMN_TYPES[CALENDAR_DAY], {
            'id': 'BIGINT', 'calendar_id': 'BIGINT', 'calendar_code': 'VARCHAR', 'calendar_name': 'VARCHAR',
            'calendar_type': 'VARCHAR', 'target_date': 'DATE', 'is_working_day': 'BIGINT', 'is_delivery_day': 'BIGINT',
            'is_order_day': 'BIGINT', 'is_holiday_work': 'BIGINT', 'work_minutes': 'BIGINT', 'work_pattern_id': 'BIGINT'})

    def test_bool_and_id_types_match_existing_views(self):
        # bool列(tinyint(1))・id列・calendar_id の型は、既存ビュー(is_active、id、calendar_id)と同じ
        types = service.ANALYSIS_COLUMN_TYPES
        self.assertEqual(types[CALENDAR_DAY]['id'], types['v_ai_customer']['id'])
        self.assertEqual(types[CALENDAR_DAY]['calendar_id'], types['v_ai_customer']['calendar_id'])
        self.assertEqual(types[CALENDAR_DAY]['calendar_id'], types['v_ai_line']['calendar_id'])
        for column in ('is_working_day', 'is_delivery_day', 'is_order_day', 'is_holiday_work'):
            self.assertEqual(types[CALENDAR_DAY][column], types['v_ai_customer']['is_active'])

    def test_ai_definition_omits_none_keys_but_keeps_date_field(self):
        definition = ai_view_definition(CALENDAR_DAY)
        self.assertEqual(set(definition), {'label', 'date_field', 'description'})
        self.assertEqual(definition['date_field'], 'target_date')
        self.assertNotIn(None, definition.values())

    def test_existing_views_output_is_unchanged(self):
        schema = {view: {**ai_view_definition(view), 'fields': BASE_SQL_SCHEMA[view]} for view in EXISTING_VIEWS}
        digest = hashlib.sha256(json.dumps(schema, ensure_ascii=False).encode('utf-8')).hexdigest()
        self.assertEqual(digest, EXISTING_DEFINITION_SHA256)

    def test_description_has_required_notes_and_no_hidden_or_fixed_values(self):
        for text in (ANALYSIS_VIEWS[CALENDAR_DAY]['description'], TABLE_NOTES[CALENDAR_DAY]):
            for part in ('1つのカレンダの1日', 'target_date', 'calendar_id', 'v_ai_line', 'v_ai_supplier', 'v_ai_customer',
                         'INTERNAL=社内', 'SUPPLIER=仕入れ', 'COMPANY=会社', 'CUSTOMER=顧客', 'OTHER=その他',
                         '稼働日', '納入日', '発注日', '休日出勤', '稼働分', '業務上の意味は未確認'):
                self.assertIn(part, text)
            # 非公開列は説明に書かない。具体的なカレンダコード・名称・件数・期間の事実も、説明に固定しない
            for hidden in ('note', 'created_at', 'updated_at', 'is_line_assignable', 'is_supplier_assignable',
                           'daiso', 'DAISO', '8479', '8,479', '2025-04-01', '2027-03-31'):
                self.assertNotIn(hidden, text)
            self.assertIsNone(re.search(r'[0-9]{3,}', text))  # 件数・年などの3桁以上の数字を書かない

    def test_origin_table_permissions_are_not_replaced(self):
        # 元テーブル m_calendar_day の許可(生産・購買・出荷の各画面)と4列は、ビューの追加後も変わらない
        self.assertEqual(BASE_SQL_SCHEMA['m_calendar_day'], ('id', 'target_date', 'is_working_day', 'work_minutes'))
        for screen in ('production', 'purchase', 'shipping'):
            self.assertIn('m_calendar_day', SCREEN_SQL_TABLES[screen])
        self.assertNotIn('m_calendar', BASE_SQL_SCHEMA)

    def test_validate_datasets_requires_target_date(self):
        # 日付列ありのビュー: 期間の根拠 target_date を fields に含める必要がある
        datasets = [{'view': CALENDAR_DAY, 'fields': ['id', 'target_date', 'is_working_day']}]
        self.assertEqual(validate_datasets(datasets, *PERIOD), datasets)
        with self.assertRaises(AnalysisError):
            validate_datasets([{'view': CALENDAR_DAY, 'fields': ['id', 'is_working_day']}], *PERIOD)
        for hidden in HIDDEN:
            with self.assertRaises(AnalysisError):
                validate_datasets([{'view': CALENDAR_DAY, 'fields': ['target_date', hidden]}], *PERIOD)

    def test_build_where_filters_by_period_unlike_dateless_masters(self):
        # 日付ありのため期間で絞る(顧客・ラインなどの日付なしビューは全行で、ここが違う)
        self.assertEqual(build_where(CALENDAR_DAY, *PERIOD), (' WHERE `target_date` >= %s AND `target_date` <= %s', list(PERIOD)))
        self.assertEqual(
            build_where(CALENDAR_DAY, *PERIOD, last_id=5),
            (' WHERE `target_date` >= %s AND `target_date` <= %s AND `id` > %s', [*PERIOD, 5]))
        self.assertEqual(build_where('v_ai_customer', *PERIOD), ('', []))

    def test_consult_prompt_has_date_field_for_calendar_day(self):
        prompt = consult._system_prompt([])
        self.assertIn(CALENDAR_DAY, prompt)
        self.assertIn('"date_field": "target_date"', prompt)
        self.assertNotIn('"date_field": null', prompt)
        self.assertNotIn('"quantity_field": null', prompt)

    def test_setup_command_treats_calendar_day_as_join_view(self):
        # v_ai_shipment と同様の結合ビュー: 単純なマスタビューに入れず(再作成しない)、確認の対象にする
        self.assertIn(CALENDAR_DAY, cmd.EXISTING_JOIN_VIEWS)
        self.assertNotIn(CALENDAR_DAY, cmd.SIMPLE_MASTER_VIEWS)
        # 元テーブルの列権限が REVOKE されないよう、使う列を OTHER_VIEW_COLUMNS に持つ
        self.assertEqual(cmd.OTHER_VIEW_COLUMNS['m_calendar_day'], {
            'id', 'calendar_id', 'target_date', 'is_working_day', 'is_delivery_day', 'is_order_day',
            'is_holiday_work', 'work_minutes', 'work_pattern_id'})
        self.assertEqual(cmd.OTHER_VIEW_COLUMNS['m_calendar'], {'id', 'calendar_code', 'calendar_name', 'calendar_type'})
        self.assertEqual(cmd.wanted_columns('m_calendar'), {'id', 'calendar_code', 'calendar_name', 'calendar_type'})
        self.assertEqual(len(cmd.wanted_columns('m_calendar_day')), 9)

    def test_published_columns_equal_union_of_both_source_tables(self):
        # ビューの12列 = m_calendar_day の9列 + m_calendar の3列(コード・名称・区分)。m_calendar.id は結合キーで、列としては出さない(d.calendar_id と同じ値)
        day, calendar = cmd.OTHER_VIEW_COLUMNS['m_calendar_day'], cmd.OTHER_VIEW_COLUMNS['m_calendar']
        self.assertEqual(set(PUBLISHED), day | (calendar - {'id'}))

    def test_migration_is_standard_left_join_without_hidden_columns(self):
        source = MIGRATION.read_text(encoding='utf-8')
        sql = migration_sql()
        for banned in ('`', 'DEFINER', 'SQL SECURITY', 'WHERE', 'pm_db', 'INNER', 'RIGHT', 'CROSS', 'GROUP', 'UNION'):
            self.assertNotIn(banned, sql)
        self.assertIn('CREATE OR REPLACE VIEW v_ai_calendar_day AS', sql)
        self.assertEqual(sql.count('JOIN'), 1)
        self.assertEqual(len(re.findall(r'\bLEFT JOIN\b', sql)), 1)
        self.assertIn('FROM m_calendar_day d', sql)
        self.assertIn('LEFT JOIN m_calendar c ON c.id = d.calendar_id', sql)
        self.assertEqual(sql.count(' AS'), 1)  # 列の別名なし(ビュー名の AS だけ)
        # 公開列は、この順序で、先頭が d. または c. の列
        body = re.search(r'SELECT(.*?)FROM', sql, re.S).group(1)
        columns = [c.strip() for c in body.split(',') if c.strip()]
        self.assertEqual([c.split('.')[1] for c in columns], list(PUBLISHED))
        self.assertEqual(
            [c.split('.')[0] for c in columns],
            ['d', 'd', 'c', 'c', 'c', 'd', 'd', 'd', 'd', 'd', 'd', 'd'])
        for hidden in HIDDEN:
            self.assertNotIn(hidden, sql)
        self.assertIn("DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_calendar_day'", source)
        self.assertIn("('ai', '0039_ai_customer_view')", source)
        self.assertIn("('masters', '0086_add_is_order_day_to_calendar_day')", source)

    def test_migration_dependency_exists_and_covers_source_columns(self):
        masters = Path(__file__).parent.parent / 'masters' / 'migrations'
        self.assertTrue((masters / '0086_add_is_order_day_to_calendar_day.py').exists())
        self.assertIn("'is_order_day'", (masters / '0086_add_is_order_day_to_calendar_day.py').read_text(encoding='utf-8'))
        self.assertIn("'calendar_type'", (masters / '0057_calendar_type.py').read_text(encoding='utf-8'))

    def test_existing_view_definitions_in_migrations_are_unchanged(self):
        # 既存ビューのマイグレーションに v_ai_calendar_day が混入していない
        for path in (Path(__file__).parent / 'migrations').glob('00[0-3]*.py'):
            self.assertNotIn(CALENDAR_DAY, path.read_text(encoding='utf-8'), path.name)
