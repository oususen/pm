"""ルーティング工程のビュー v_ai_routing_step の登録を検証する。

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

VIEW = 'v_ai_routing_step'
EXISTING_VIEWS = (
    'v_ai_shipment', 'v_ai_purchase_receipt', 'v_ai_product', 'v_ai_process', 'v_ai_line', 'v_ai_supplier',
    'v_ai_customer')
PERIOD = ('2026-09-01', '2026-09-30')
PUBLISHED = (
    'id', 'routing_id', 'routing_code', 'routing_product_id', 'routing_product_code', 'routing_product_name',
    'routing_is_default', 'routing_is_active', 'routing_valid_from_datetime', 'routing_valid_to_datetime',
    'step_no', 'parallel_group', 'parallel_count', 'hierarchy_depth', 'hierarchy_path', 'process_id',
    'process_code', 'process_name', 'line_id', 'line_code', 'line_name', 'supplier_id', 'supplier_code',
    'supplier_name', 'output_product_id', 'output_product_code', 'output_product_name', 'parent_product_code',
    'source_bom_item_id', 'time_unit', 'lead_time_days', 'start_offset_min', 'duration_min')
# 各列の元(テーブルの別名.列)。順序は PUBLISHED と同じ
SOURCES = (
    's.id', 's.routing_id', 'r.routing_code', 'r.product_id', 'rp.product_code', 'rp.product_name',
    'r.is_default', 'r.is_active', 'r.valid_from_datetime', 'r.valid_to_datetime',
    's.step_no', 's.parallel_group', 's.parallel_count', 's.hierarchy_depth', 's.hierarchy_path', 's.process_id',
    'pr.process_code', 'pr.process_name', 's.line_id', 'l.line_code', 'l.line_name', 's.supplier_id',
    'sp.supplier_code', 'sp.supplier_name', 's.output_product_id', 'op.product_code', 'op.product_name', 's.remark',
    's.source_bom_item_id', 's.time_unit', 's.lead_time_days', 's.start_offset_min', 's.duration_min')
# 非公開(ビューに含めない): m_routing_step の step_type・created_at・updated_at、m_routing の description・created_at・updated_at、
# 結合先(仕入先)の担当者・電話・メール
HIDDEN = (
    'step_type', 'created_at', 'updated_at', 'description', 'contact_person', 'phone_number', 'order_email')
# ルーティング工程のビュー追加前の、既存7ビューのAIへ渡す定義(fields付き)のJSONのSHA-256。1文字でも変わると不一致になる。
# v_ai_routing_step・v_ai_routing_step_material の追加は既存7ビューの列・説明を変えないため、BOM明細ビューの試験の固定値と同じ値のまま
EXISTING_DEFINITION_SHA256 = 'db31acbfe065946a26dc439a40b4076ca41530869749bedf1f92e06600a410ed'
MIGRATION = Path(__file__).parent / 'migrations' / '0042_ai_routing_step_view.py'


# 説明文に出てよい英大文字の語(列の説明のID、モデルのラベルの値DAY・MINUTE・START・END、BOM明細)。
# 具体的な工程コード(PURCHASE・G・レーザ1など)は、ルーティングのビューの説明に入れない
ALLOWED_UPPER_WORDS = {'ID', 'DAY', 'MINUTE', 'START', 'END', 'BOM'}


def check_no_fixed_values(case, text):
    """説明文に実データ由来の値(件数・具体コード)が混入していないことを検査する。"""
    # 2桁以上の数字は、単位の有無にかかわらず書かない(「33工程」「38件」「123行」など)。1桁は「1行=1工程」「1か0」だけ許す
    case.assertIsNone(re.search(r'[0-9]{2,}', text))
    # 1桁でも件数を表す形(N件・N種類・N行)は書かない。定義の文言の「1行」だけは許す
    case.assertIsNone(re.search(r'[0-9]+(?:件|種類)|(?<![0-9])(?:[02-9]|[0-9]{2,})行', text))
    case.assertIsNone(re.search(r'(?<![0-9])[02-9](?:工程|列|個|ルーティング|品番)', text))
    # 具体的な工程コード・工程名(PURCHASE・外作を示すG・レーザ1など)を書かない。許可する英大文字の語以外の大文字語も書かない
    for word in re.findall(r'(?<![A-Za-z_])[A-Z][A-Z0-9_]*(?![A-Za-z_])', text):
        case.assertIn(word, ALLOWED_UPPER_WORDS, word)
    for concrete in ('PURCHASE', 'OUTSOURCE', 'レーザ', 'FLOW', 'PARALLEL_POOL'):
        case.assertNotIn(concrete, text)


def migration_sql():
    return MIGRATION.read_text(encoding='utf-8').split('CREATE_VIEW = """')[1].split('"""')[0]


class RoutingStepViewDefinitionTest(SimpleTestCase):
    def test_view_is_registered_without_date_and_quantity_field(self):
        definition = ANALYSIS_VIEWS[VIEW]
        self.assertIsNone(definition['date_field'])
        self.assertIsNone(definition['quantity_field'])
        self.assertEqual(definition['label'], 'ルーティング工程')

    def test_column_types_match_published_columns_exactly(self):
        self.assertEqual(BASE_SQL_SCHEMA[VIEW], PUBLISHED)
        self.assertEqual(len(PUBLISHED), 33)
        self.assertEqual(len(set(PUBLISHED)), 33)
        self.assertEqual(set(service.ANALYSIS_COLUMN_TYPES[VIEW]), set(BASE_SQL_SCHEMA[VIEW]))
        self.assertEqual(service.ANALYSIS_COLUMN_TYPES[VIEW], {
            'id': 'BIGINT', 'routing_id': 'BIGINT', 'routing_code': 'VARCHAR', 'routing_product_id': 'BIGINT',
            'routing_product_code': 'VARCHAR', 'routing_product_name': 'VARCHAR', 'routing_is_default': 'BIGINT',
            'routing_is_active': 'BIGINT', 'routing_valid_from_datetime': 'TIMESTAMP',
            'routing_valid_to_datetime': 'TIMESTAMP', 'step_no': 'BIGINT', 'parallel_group': 'BIGINT',
            'parallel_count': 'BIGINT', 'hierarchy_depth': 'BIGINT', 'hierarchy_path': 'VARCHAR',
            'process_id': 'BIGINT', 'process_code': 'VARCHAR', 'process_name': 'VARCHAR', 'line_id': 'BIGINT',
            'line_code': 'VARCHAR', 'line_name': 'VARCHAR', 'supplier_id': 'BIGINT', 'supplier_code': 'VARCHAR',
            'supplier_name': 'VARCHAR', 'output_product_id': 'BIGINT', 'output_product_code': 'VARCHAR',
            'output_product_name': 'VARCHAR', 'parent_product_code': 'VARCHAR', 'source_bom_item_id': 'BIGINT',
            'time_unit': 'VARCHAR', 'lead_time_days': 'BIGINT', 'start_offset_min': 'BIGINT',
            'duration_min': 'BIGINT'})

    def test_types_match_existing_views(self):
        # bool列・id列・datetime列・同じ元の列(コード・名称)は既存ビューと同じ型
        types = service.ANALYSIS_COLUMN_TYPES
        self.assertEqual(types[VIEW]['id'], types['v_ai_customer']['id'])
        for column in ('routing_is_default', 'routing_is_active'):
            self.assertEqual(types[VIEW][column], types['v_ai_customer']['is_active'])
        for column in ('routing_valid_from_datetime', 'routing_valid_to_datetime'):
            self.assertEqual(types[VIEW][column], types['v_ai_purchase_receipt']['registered_at'])
        self.assertEqual(types[VIEW]['time_unit'], types['v_ai_bom_item']['time_unit'])
        self.assertEqual(types[VIEW]['lead_time_days'], types['v_ai_bom_item']['lead_time_days'])
        self.assertEqual(types[VIEW]['duration_min'], types['v_ai_bom_item']['duration_min'])
        for column, other, other_column in (
                ('supplier_code', 'v_ai_supplier', 'supplier_code'), ('supplier_name', 'v_ai_supplier', 'supplier_name'),
                ('process_code', 'v_ai_process', 'process_code'), ('process_name', 'v_ai_process', 'process_name'),
                ('line_code', 'v_ai_line', 'line_code'), ('line_name', 'v_ai_line', 'line_name'),
                ('output_product_code', 'v_ai_product', 'product_code'), ('routing_product_name', 'v_ai_product', 'product_name'),
                ('supplier_id', 'v_ai_supplier', 'id'), ('process_id', 'v_ai_process', 'id'), ('line_id', 'v_ai_line', 'id'),
                ('output_product_id', 'v_ai_product', 'id')):
            self.assertEqual(types[VIEW][column], types[other][other_column], column)

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
                    '1行は1工程' if text is ANALYSIS_VIEWS[VIEW]['description'] else '1行=1工程',
                    'routing_', 'output_product_', '加工後品', 'parent_product_code', '親品の品番コード',
                    'v_ai_product', '品番マスタにない値があり得る', 'v_ai_process', 'v_ai_line', 'v_ai_supplier',
                    'parallel_group', 'parallel_count', 'hierarchy_', 'source_bom_item_id', 'start_offset_min',
                    'time_unit', 'DAY=日', 'MINUTE=分', 'lead_time_days', 'duration_min', '未確認',
                    '工程の数', 'v_ai_routing_step_material', 'routing_step_id', '材料のない工程'):
                self.assertIn(part, text)
            # 非公開列は説明に書かない(remark は parent_product_code の別名として公開しているため説明してよい)。
            # 具体的なコード・件数の事実も、説明に固定しない
            for hidden in ('step_type', 'created_at', 'updated_at', 'description', 'contact_person', 'phone_number',
                           'order_email', 'FLOW', 'PARALLEL_POOL'):
                self.assertNotIn(hidden, text)
            check_no_fixed_values(self, text)  # 件数・具体コードを書かない
            # 意味が未確認の項目は、項目名だけを書く(意味の推測を書かない)
            self.assertIn('業務上の意味は未確認(項目名のみ)', text)

    def test_origin_table_permissions_are_not_replaced(self):
        # 元テーブル m_routing の許可と列は、ビューの追加後も変わらない(m_routing_step・m_routing_step_material は元から許可なし)
        self.assertEqual(BASE_SQL_SCHEMA['m_routing'], ('id', 'product_id', 'is_active'))
        self.assertNotIn('m_routing_step', BASE_SQL_SCHEMA)
        self.assertNotIn('m_routing_step_material', BASE_SQL_SCHEMA)
        self.assertEqual(SCREEN_SQL_TABLES['orders'], frozenset({'m_customer', 'm_product', 'm_routing', 't_order', 't_order_line'}))
        self.assertNotIn('m_routing', SCREEN_SQL_TABLES['production'])
        self.assertNotIn(VIEW, SCREEN_SQL_TABLES['production'])
        self.assertIn(VIEW, SCREEN_SQL_TABLES['ai_home'])

    def test_validate_datasets_without_date_field(self):
        # 日付なしのビュー: 期間の根拠の列は不要。公開列だけを指定できる
        datasets = [{'view': VIEW, 'fields': ['id', 'routing_id', 'parent_product_code']}]
        self.assertEqual(validate_datasets(datasets, *PERIOD), datasets)
        for hidden in HIDDEN + ('remark',):
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
        # 元テーブルの列権限が REVOKE されないよう、使う列を OTHER_VIEW_COLUMNS に持つ
        self.assertEqual(cmd.OTHER_VIEW_COLUMNS['m_routing'], {
            'id', 'product_id', 'routing_code', 'is_default', 'is_active', 'valid_from_datetime', 'valid_to_datetime'})
        self.assertEqual(cmd.OTHER_VIEW_COLUMNS['m_routing_step'], {
            'duration_min', 'hierarchy_depth', 'hierarchy_path', 'id', 'lead_time_days', 'line_id',
            'output_product_id', 'parallel_count', 'parallel_group', 'process_id', 'remark', 'routing_id',
            'source_bom_item_id', 'start_offset_min', 'step_no', 'supplier_id', 'time_unit'})
        self.assertEqual(len(cmd.wanted_columns('m_routing')), 7)
        self.assertEqual(len(cmd.wanted_columns('m_routing_step')), 17)
        for column in ('step_type', 'created_at', 'updated_at'):
            self.assertNotIn(column, cmd.wanted_columns('m_routing_step'))
        for column in ('description', 'created_at', 'updated_at'):
            self.assertNotIn(column, cmd.wanted_columns('m_routing'))

    def test_joined_master_columns_are_granted_by_simple_master_views(self):
        # 結合先のコード・名称の列は、既存の単純なマスタビューの公開列に含まれる(足りなければ OTHER_VIEW_COLUMNS が必要)
        for table, columns in (
                ('m_product', ('id', 'product_code', 'product_name')),
                ('m_process', ('id', 'process_code', 'process_name')),
                ('m_line', ('id', 'line_code', 'line_name')),
                ('m_supplier', ('id', 'supplier_code', 'supplier_name'))):
            for column in columns:
                self.assertIn(column, cmd.wanted_columns(table), (table, column))

    def test_published_columns_equal_source_columns(self):
        # m_routing_step の17列(結合キー以外はそのまま・remark は別名)と m_routing の列が、そのまま/結合して公開列に出る
        step, routing = cmd.OTHER_VIEW_COLUMNS['m_routing_step'], cmd.OTHER_VIEW_COLUMNS['m_routing']
        self.assertEqual({s.split('.')[1] for s in SOURCES if s.startswith('s.')}, step)
        self.assertEqual({s.split('.')[1] for s in SOURCES if s.startswith('r.')}, routing - {'id'})

    def test_migration_is_standard_left_join_without_hidden_columns(self):
        source = MIGRATION.read_text(encoding='utf-8')
        sql = migration_sql()
        for banned in ('`', 'DEFINER', 'SQL SECURITY', 'WHERE', 'pm_db', 'INNER', 'RIGHT', 'CROSS', 'GROUP', 'UNION'):
            self.assertNotIn(banned, sql)
        self.assertIn('CREATE OR REPLACE VIEW v_ai_routing_step AS', sql)
        self.assertEqual(sql.count('JOIN'), 6)
        self.assertEqual(len(re.findall(r'\bLEFT JOIN\b', sql)), 6)
        self.assertIn('FROM m_routing_step s', sql)
        # 結合キーは、すべて結合先の主キー(id)
        joins = re.findall(r'LEFT JOIN (\w+) (\w+) ON (\w+)\.(\w+) = (\w+)\.(\w+)', sql)
        self.assertEqual(len(joins), 6)
        for _table, alias, left_alias, left_column, _right_alias, _right_column in joins:
            self.assertEqual(alias, left_alias)
            self.assertEqual(left_column, 'id')
        for join in (
                'LEFT JOIN m_routing r ON r.id = s.routing_id',
                'LEFT JOIN m_product rp ON rp.id = r.product_id',
                'LEFT JOIN m_process pr ON pr.id = s.process_id',
                'LEFT JOIN m_line l ON l.id = s.line_id',
                'LEFT JOIN m_supplier sp ON sp.id = s.supplier_id',
                'LEFT JOIN m_product op ON op.id = s.output_product_id'):
            self.assertIn(join, sql)
        # 公開列は、この順序・この元・この別名(別名なしの列は元の列名と同じ)
        body = re.search(r'SELECT(.*?)FROM', sql, re.S).group(1)
        columns = [c.strip() for c in body.split(',') if c.strip()]
        self.assertEqual(len(columns), 33)
        names, sources = [], []
        for column in columns:
            source_column, _, alias = column.partition(' AS ')
            sources.append(source_column.strip())
            names.append(alias.strip() or source_column.split('.')[1])
        self.assertEqual(names, list(PUBLISHED))
        self.assertEqual(sources, list(SOURCES))
        for hidden in HIDDEN:
            self.assertNotIn(hidden, sql)
        self.assertIn("DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_routing_step'", source)
        self.assertIn("('ai', '0041_ai_bom_item_view')", source)
        self.assertIn("('masters', '0086_add_is_order_day_to_calendar_day')", source)

    def test_migration_dependency_exists_and_covers_source_columns(self):
        masters = Path(__file__).parent.parent / 'masters' / 'migrations'
        self.assertTrue((masters / '0086_add_is_order_day_to_calendar_day.py').exists())
        self.assertEqual(sorted(p.name for p in masters.glob('00*.py'))[-1], '0086_add_is_order_day_to_calendar_day.py')
        self.assertTrue((Path(__file__).parent / 'migrations' / '0041_ai_bom_item_view.py').exists())
        for name, column in (
                ('0043_routingstep_source_bom_item.py', 'source_bom_item'), ('0047_routingstep_supplier.py', 'supplier'),
                ('0007_routingstep_output_product.py', 'output_product'), ('0021_routingstep_parallel_group.py', 'parallel_group'),
                ('0020_routingstep_parallel_count.py', 'parallel_count'),
                ('0010_routingstep_hierarchy_fields.py', 'hierarchy_depth'),
                ('0041_routing_valid_from_datetime_and_more.py', 'valid_from_datetime')):
            self.assertIn(f"'{column}'", (masters / name).read_text(encoding='utf-8'), name)

    def test_existing_view_definitions_in_migrations_are_unchanged(self):
        # 既存ビューのマイグレーションに v_ai_routing_step が混入していない(0042 の自分自身と、材料ビューの 0043 だけが参照する)
        for path in (Path(__file__).parent / 'migrations').glob('00[0-3]*.py'):
            self.assertNotIn(VIEW, path.read_text(encoding='utf-8'), path.name)
        self.assertNotIn(VIEW, (Path(__file__).parent / 'migrations' / '0040_ai_calendar_day_view.py').read_text(encoding='utf-8'))
        self.assertNotIn(VIEW, (Path(__file__).parent / 'migrations' / '0041_ai_bom_item_view.py').read_text(encoding='utf-8'))
