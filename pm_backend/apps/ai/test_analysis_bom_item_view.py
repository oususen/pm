"""BOM明細のビュー v_ai_bom_item の登録を検証する。

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

BOM_ITEM = 'v_ai_bom_item'
EXISTING_VIEWS = (
    'v_ai_shipment', 'v_ai_purchase_receipt', 'v_ai_product', 'v_ai_process', 'v_ai_line', 'v_ai_supplier',
    'v_ai_customer')
PERIOD = ('2026-09-01', '2026-09-30')
PUBLISHED = (
    'id', 'bom_id', 'parent_product_id', 'parent_product_code', 'parent_product_name', 'bom_version',
    'bom_valid_from', 'bom_valid_to', 'bom_is_active', 'bom_is_coproduct', 'child_product_id',
    'child_product_code', 'child_product_name', 'quantity', 'loss_rate', 'sourcing_type', 'supplier_id',
    'supplier_code', 'supplier_name', 'process_id', 'process_code', 'process_name', 'line_id', 'line_code',
    'line_name', 'time_unit', 'lead_time_days', 'duration_min', 'is_coproduct_driver')
# 各列の元(テーブルの別名.列)。順序は PUBLISHED と同じ
SOURCES = (
    'i.id', 'i.bom_id', 'b.parent_product_id', 'pp.product_code', 'pp.product_name', 'b.version',
    'b.valid_from', 'b.valid_to', 'b.is_active', 'b.is_coproduct', 'i.child_product_id',
    'cp.product_code', 'cp.product_name', 'i.quantity', 'i.loss_rate', 'i.sourcing_type', 'i.supplier_id',
    's.supplier_code', 's.supplier_name', 'i.process_id', 'pr.process_code', 'pr.process_name', 'i.line_id',
    'l.line_code', 'l.line_name', 'i.time_unit', 'i.lead_time_days', 'i.duration_min', 'i.is_coproduct_driver')
# 非公開(ビューに含めない): m_bom_item の remark・created_at・updated_at、m_bom の created_at・updated_at、
# 結合先(仕入先)の担当者・電話・メール
HIDDEN = (
    'remark', 'created_at', 'updated_at', 'contact_person', 'phone_number', 'order_email')
# BOM明細ビュー追加前の、既存7ビューのAIへ渡す定義(fields付き)のJSONのSHA-256。1文字でも変わると不一致になる。
# v_ai_bom_item の追加は既存ビューの列・説明を変えないため、稼働カレンダビューの試験の固定値と同じ値のまま
EXISTING_DEFINITION_SHA256 = 'db31acbfe065946a26dc439a40b4076ca41530869749bedf1f92e06600a410ed'
MIGRATION = Path(__file__).parent / 'migrations' / '0041_ai_bom_item_view.py'


def migration_sql():
    return MIGRATION.read_text(encoding='utf-8').split('CREATE_VIEW = """')[1].split('"""')[0]


class BomItemViewDefinitionTest(SimpleTestCase):
    def test_bom_item_view_is_registered_without_date_and_quantity_field(self):
        definition = ANALYSIS_VIEWS[BOM_ITEM]
        self.assertIsNone(definition['date_field'])
        self.assertIsNone(definition['quantity_field'])
        self.assertEqual(definition['label'], 'BOM明細')

    def test_column_types_match_published_columns_exactly(self):
        self.assertEqual(BASE_SQL_SCHEMA[BOM_ITEM], PUBLISHED)
        self.assertEqual(len(PUBLISHED), 29)
        self.assertEqual(set(service.ANALYSIS_COLUMN_TYPES[BOM_ITEM]), set(BASE_SQL_SCHEMA[BOM_ITEM]))
        self.assertEqual(service.ANALYSIS_COLUMN_TYPES[BOM_ITEM], {
            'id': 'BIGINT', 'bom_id': 'BIGINT', 'parent_product_id': 'BIGINT', 'parent_product_code': 'VARCHAR',
            'parent_product_name': 'VARCHAR', 'bom_version': 'VARCHAR', 'bom_valid_from': 'DATE',
            'bom_valid_to': 'DATE', 'bom_is_active': 'BIGINT', 'bom_is_coproduct': 'BIGINT',
            'child_product_id': 'BIGINT', 'child_product_code': 'VARCHAR', 'child_product_name': 'VARCHAR',
            'quantity': 'DECIMAL(18,3)', 'loss_rate': 'DECIMAL(18,3)', 'sourcing_type': 'VARCHAR',
            'supplier_id': 'BIGINT', 'supplier_code': 'VARCHAR', 'supplier_name': 'VARCHAR',
            'process_id': 'BIGINT', 'process_code': 'VARCHAR', 'process_name': 'VARCHAR', 'line_id': 'BIGINT',
            'line_code': 'VARCHAR', 'line_name': 'VARCHAR', 'time_unit': 'VARCHAR', 'lead_time_days': 'BIGINT',
            'duration_min': 'BIGINT', 'is_coproduct_driver': 'BIGINT'})

    def test_bool_and_id_types_match_existing_views(self):
        # bool列(tinyint(1))・id列は既存ビューと同じ。同じ元の列(コード・名称)も既存の単純ビューと同じ型
        types = service.ANALYSIS_COLUMN_TYPES
        self.assertEqual(types[BOM_ITEM]['id'], types['v_ai_customer']['id'])
        for column in ('bom_is_active', 'bom_is_coproduct', 'is_coproduct_driver'):
            self.assertEqual(types[BOM_ITEM][column], types['v_ai_customer']['is_active'])
        for column, other, other_column in (
                ('supplier_code', 'v_ai_supplier', 'supplier_code'), ('supplier_name', 'v_ai_supplier', 'supplier_name'),
                ('process_code', 'v_ai_process', 'process_code'), ('process_name', 'v_ai_process', 'process_name'),
                ('line_code', 'v_ai_line', 'line_code'), ('line_name', 'v_ai_line', 'line_name'),
                ('child_product_code', 'v_ai_product', 'product_code'), ('parent_product_name', 'v_ai_product', 'product_name'),
                ('supplier_id', 'v_ai_supplier', 'id'), ('process_id', 'v_ai_process', 'id'), ('line_id', 'v_ai_line', 'id')):
            self.assertEqual(types[BOM_ITEM][column], types[other][other_column], column)

    def test_ai_definition_omits_none_keys(self):
        definition = ai_view_definition(BOM_ITEM)
        self.assertEqual(set(definition), {'label', 'description'})
        self.assertNotIn(None, definition.values())

    def test_existing_views_output_is_unchanged(self):
        schema = {view: {**ai_view_definition(view), 'fields': BASE_SQL_SCHEMA[view]} for view in EXISTING_VIEWS}
        digest = hashlib.sha256(json.dumps(schema, ensure_ascii=False).encode('utf-8')).hexdigest()
        self.assertEqual(digest, EXISTING_DEFINITION_SHA256)

    def test_description_has_required_notes_and_no_hidden_or_fixed_values(self):
        for text in (ANALYSIS_VIEWS[BOM_ITEM]['description'], TABLE_NOTES[BOM_ITEM]):
            for part in (
                    'BOM明細1行', '明細が1行もないBOM', '実際より少ない', 'bom_valid_from', 'v_auto_', '数字の大小',
                    'BUY', 'SUBCON', '仕入先が必ずある',
                    'MAKE=自社製造', 'lead_time_days', '0の行はありうる', 'duration_min', 'サイクル時間', 'DAY', 'MINUTE',
                    '合計しても業務上の意味はない', '(1+ロス率)', 'v_ai_product', 'v_ai_supplier', 'v_ai_process', 'v_ai_line',
                    'bom_id', 'parent_product_id', 'child_product_id', '未確認'):
                self.assertIn(part, text)
            # 非公開列は説明に書かない。具体的な品番コード・名称・件数の事実も、説明に固定しない
            for hidden in ('remark', 'created_at', 'updated_at', 'contact_person', 'phone_number', 'order_email',
                           '3,428', '3428', '1,323', '1323', '1,314', '1314'):
                self.assertNotIn(hidden, text)
            self.assertIsNone(re.search(r'[0-9]{3,}', text))  # 件数などの3桁以上の数字を書かない
            self.assertNotIn('v_auto_20', text)  # 具体的な版の値は書かない

    def test_origin_table_permissions_are_not_replaced(self):
        # 元テーブル m_bom・m_bom_item の許可と列は、ビューの追加後も変わらない
        self.assertEqual(BASE_SQL_SCHEMA['m_bom'], (
            'id', 'parent_product_id', 'version', 'valid_from', 'valid_to', 'is_active', 'is_coproduct'))
        self.assertEqual(BASE_SQL_SCHEMA['m_bom_item'], (
            'id', 'bom_id', 'child_product_id', 'quantity', 'loss_rate', 'sourcing_type', 'supplier_id',
            'process_id', 'line_id', 'time_unit', 'lead_time_days', 'duration_min', 'is_coproduct_driver', 'remark'))
        self.assertNotIn('m_bom', SCREEN_SQL_TABLES['production'])
        self.assertNotIn(BOM_ITEM, SCREEN_SQL_TABLES['production'])
        self.assertIn(BOM_ITEM, SCREEN_SQL_TABLES['ai_home'])

    def test_validate_datasets_without_date_field(self):
        # 日付なしのビュー: 期間の根拠の列は不要。公開列だけを指定できる
        datasets = [{'view': BOM_ITEM, 'fields': ['id', 'bom_id', 'quantity']}]
        self.assertEqual(validate_datasets(datasets, *PERIOD), datasets)
        for hidden in HIDDEN:
            with self.assertRaises(AnalysisError):
                validate_datasets([{'view': BOM_ITEM, 'fields': ['id', hidden]}], *PERIOD)

    def test_build_where_does_not_filter_by_period(self):
        # 日付なしのため、期間で絞らず全行(稼働カレンダ・顧客など他のビューとの違い)
        self.assertEqual(build_where(BOM_ITEM, *PERIOD), ('', []))
        self.assertEqual(build_where(BOM_ITEM, *PERIOD, last_id=5), (' WHERE `id` > %s', [5]))

    def test_consult_prompt_has_bom_item_view(self):
        prompt = consult._system_prompt([])
        self.assertIn(BOM_ITEM, prompt)

    def test_setup_command_treats_bom_item_as_join_view(self):
        # v_ai_shipment と同様の結合ビュー: 単純なマスタビューに入れず(再作成しない)、確認の対象にする
        self.assertIn(BOM_ITEM, cmd.EXISTING_JOIN_VIEWS)
        self.assertNotIn(BOM_ITEM, cmd.SIMPLE_MASTER_VIEWS)
        # 元テーブルの列権限が REVOKE されないよう、使う列を OTHER_VIEW_COLUMNS に持つ
        self.assertEqual(cmd.OTHER_VIEW_COLUMNS['m_bom'], {
            'id', 'parent_product_id', 'version', 'valid_from', 'valid_to', 'is_active', 'is_coproduct'})
        self.assertEqual(cmd.OTHER_VIEW_COLUMNS['m_bom_item'], {
            'id', 'bom_id', 'child_product_id', 'quantity', 'loss_rate', 'sourcing_type', 'supplier_id',
            'process_id', 'line_id', 'time_unit', 'lead_time_days', 'duration_min', 'is_coproduct_driver'})
        self.assertEqual(len(cmd.wanted_columns('m_bom')), 7)
        self.assertEqual(len(cmd.wanted_columns('m_bom_item')), 13)
        for column in ('remark', 'created_at', 'updated_at'):
            self.assertNotIn(column, cmd.wanted_columns('m_bom_item'))

    def test_published_columns_equal_union_of_source_columns(self):
        # m_bom_item の13列(結合キー以外はそのまま)と m_bom の6列(id は結合キー)は、そのまま公開列に出る
        item, bom = cmd.OTHER_VIEW_COLUMNS['m_bom_item'], cmd.OTHER_VIEW_COLUMNS['m_bom']
        plain = set(PUBLISHED) - {c for c, s in zip(PUBLISHED, SOURCES) if s.startswith(('pp.', 'cp.', 's.', 'pr.', 'l.', 'b.'))}
        self.assertEqual(plain, item)
        self.assertEqual({s.split('.')[1] for s in SOURCES if s.startswith('b.')}, bom - {'id'})

    def test_migration_is_standard_left_join_without_hidden_columns(self):
        source = MIGRATION.read_text(encoding='utf-8')
        sql = migration_sql()
        for banned in ('`', 'DEFINER', 'SQL SECURITY', 'WHERE', 'pm_db', 'INNER', 'RIGHT', 'CROSS', 'GROUP', 'UNION'):
            self.assertNotIn(banned, sql)
        self.assertIn('CREATE OR REPLACE VIEW v_ai_bom_item AS', sql)
        self.assertEqual(sql.count('JOIN'), 6)
        self.assertEqual(len(re.findall(r'\bLEFT JOIN\b', sql)), 6)
        self.assertIn('FROM m_bom_item i', sql)
        for join in (
                'LEFT JOIN m_bom b ON b.id = i.bom_id',
                'LEFT JOIN m_product pp ON pp.id = b.parent_product_id',
                'LEFT JOIN m_product cp ON cp.id = i.child_product_id',
                'LEFT JOIN m_process pr ON pr.id = i.process_id',
                'LEFT JOIN m_line l ON l.id = i.line_id',
                'LEFT JOIN m_supplier s ON s.id = i.supplier_id'):
            self.assertIn(join, sql)
        # 公開列は、この順序・この元・この別名(別名なしの列は元の列名と同じ)
        body = re.search(r'SELECT(.*?)FROM', sql, re.S).group(1)
        columns = [c.strip() for c in body.split(',') if c.strip()]
        self.assertEqual(len(columns), 29)
        names, sources = [], []
        for column in columns:
            source_column, _, alias = column.partition(' AS ')
            sources.append(source_column.strip())
            names.append(alias.strip() or source_column.split('.')[1])
        self.assertEqual(names, list(PUBLISHED))
        self.assertEqual(sources, list(SOURCES))
        for hidden in HIDDEN:
            self.assertNotIn(hidden, sql)
        self.assertIn("DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_bom_item'", source)
        self.assertIn("('ai', '0040_ai_calendar_day_view')", source)
        self.assertIn("('masters', '0086_add_is_order_day_to_calendar_day')", source)

    def test_migration_dependency_exists_and_covers_source_columns(self):
        masters = Path(__file__).parent.parent / 'masters' / 'migrations'
        self.assertTrue((masters / '0086_add_is_order_day_to_calendar_day.py').exists())
        self.assertEqual(sorted(p.name for p in masters.glob('00*.py'))[-1], '0086_add_is_order_day_to_calendar_day.py')
        self.assertIn("'is_coproduct_driver'", (masters / '0029_bomitem_is_coproduct_driver.py').read_text(encoding='utf-8'))
        self.assertIn("'is_coproduct'", (masters / '0013_add_coproduct_fields.py').read_text(encoding='utf-8'))

    def test_existing_view_definitions_in_migrations_are_unchanged(self):
        # 既存ビューのマイグレーションに v_ai_bom_item が混入していない
        for path in (Path(__file__).parent / 'migrations').glob('00[0-3]*.py'):
            self.assertNotIn(BOM_ITEM, path.read_text(encoding='utf-8'), path.name)
        self.assertNotIn(BOM_ITEM, (Path(__file__).parent / 'migrations' / '0040_ai_calendar_day_view.py').read_text(encoding='utf-8'))
