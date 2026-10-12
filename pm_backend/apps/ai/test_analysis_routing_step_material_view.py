"""工程別部品消費のビュー v_ai_routing_step_material の登録を検証する。

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

VIEW = 'v_ai_routing_step_material'
EXISTING_VIEWS = (
    'v_ai_shipment', 'v_ai_purchase_receipt', 'v_ai_product', 'v_ai_process', 'v_ai_line', 'v_ai_supplier',
    'v_ai_customer')
PERIOD = ('2026-09-01', '2026-09-30')
PUBLISHED = (
    'id', 'routing_step_id', 'routing_id', 'routing_code', 'routing_product_id', 'routing_product_code',
    'routing_product_name', 'step_no', 'step_process_id', 'step_process_code', 'step_process_name',
    'step_output_product_id', 'step_output_product_code', 'step_output_product_name', 'step_parent_product_code',
    'component_id', 'component_code', 'component_name', 'quantity', 'consume_timing')
# 各列の元(テーブルの別名.列)。順序は PUBLISHED と同じ
SOURCES = (
    'm.id', 'm.routing_step_id', 's.routing_id', 'r.routing_code', 'r.product_id', 'rp.product_code',
    'rp.product_name', 's.step_no', 's.process_id', 'pr.process_code', 'pr.process_name',
    's.output_product_id', 'op.product_code', 'op.product_name', 's.remark',
    'm.component_id', 'cp.product_code', 'cp.product_name', 'm.quantity', 'm.consume_timing')
# 非公開(ビューに含めない): m_routing_step_material の remark・created_at・updated_at、m_routing_step の step_type・created_at・updated_at 等
HIDDEN = ('step_type', 'created_at', 'updated_at', 'description', 'contact_person', 'phone_number', 'order_email')
# 既存7ビューのAIへ渡す定義(fields付き)のJSONのSHA-256。ルーティングの2ビューの追加で変わらない
EXISTING_DEFINITION_SHA256 = 'db31acbfe065946a26dc439a40b4076ca41530869749bedf1f92e06600a410ed'
MIGRATION = Path(__file__).parent / 'migrations' / '0043_ai_routing_step_material_view.py'


# 説明文に出てよい英大文字の語(列の説明のID、モデルのラベルの値DAY・MINUTE・START・END、BOM明細)。
# 具体的な工程コード(PURCHASE・G・レーザ1など)は、ルーティングのビューの説明に入れない
ALLOWED_UPPER_WORDS = {'ID', 'DAY', 'MINUTE', 'START', 'END', 'BOM'}


def check_no_fixed_values(case, text):
    """説明文に実データ由来の値(件数・具体コード)が混入していないことを検査する。"""
    # 2桁以上の数字は、単位の有無にかかわらず書かない(「33工程」「38件」「123行」など)。1桁は「1行=1工程」だけ許す
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


class RoutingStepMaterialViewDefinitionTest(SimpleTestCase):
    def test_view_is_registered_without_date_and_quantity_field(self):
        definition = ANALYSIS_VIEWS[VIEW]
        self.assertIsNone(definition['date_field'])
        self.assertIsNone(definition['quantity_field'])
        self.assertEqual(definition['label'], 'ルーティング工程の材料')

    def test_column_types_match_published_columns_exactly(self):
        self.assertEqual(BASE_SQL_SCHEMA[VIEW], PUBLISHED)
        self.assertEqual(len(PUBLISHED), 20)
        self.assertEqual(len(set(PUBLISHED)), 20)
        self.assertEqual(set(service.ANALYSIS_COLUMN_TYPES[VIEW]), set(BASE_SQL_SCHEMA[VIEW]))
        self.assertEqual(service.ANALYSIS_COLUMN_TYPES[VIEW], {
            'id': 'BIGINT', 'routing_step_id': 'BIGINT', 'routing_id': 'BIGINT', 'routing_code': 'VARCHAR',
            'routing_product_id': 'BIGINT', 'routing_product_code': 'VARCHAR', 'routing_product_name': 'VARCHAR',
            'step_no': 'BIGINT', 'step_process_id': 'BIGINT', 'step_process_code': 'VARCHAR',
            'step_process_name': 'VARCHAR', 'step_output_product_id': 'BIGINT',
            'step_output_product_code': 'VARCHAR', 'step_output_product_name': 'VARCHAR',
            'step_parent_product_code': 'VARCHAR', 'component_id': 'BIGINT', 'component_code': 'VARCHAR',
            'component_name': 'VARCHAR', 'quantity': 'DECIMAL(18,3)', 'consume_timing': 'VARCHAR'})

    def test_types_match_step_view_and_existing_views(self):
        # 工程ビューと同じ元の列は、同じ型
        types = service.ANALYSIS_COLUMN_TYPES
        for column, other_column in (
                ('routing_id', 'routing_id'), ('routing_code', 'routing_code'), ('routing_product_id', 'routing_product_id'),
                ('routing_product_code', 'routing_product_code'), ('routing_product_name', 'routing_product_name'),
                ('step_no', 'step_no'), ('step_process_id', 'process_id'), ('step_process_code', 'process_code'),
                ('step_process_name', 'process_name'), ('step_output_product_id', 'output_product_id'),
                ('step_output_product_code', 'output_product_code'), ('step_output_product_name', 'output_product_name'),
                ('step_parent_product_code', 'parent_product_code')):
            self.assertEqual(types[VIEW][column], types['v_ai_routing_step'][other_column], column)
        self.assertEqual(types[VIEW]['quantity'], types['v_ai_bom_item']['quantity'])
        self.assertEqual(types[VIEW]['component_id'], types['v_ai_product']['id'])
        self.assertEqual(types[VIEW]['component_code'], types['v_ai_product']['product_code'])
        self.assertEqual(types[VIEW]['component_name'], types['v_ai_product']['product_name'])
        self.assertEqual(types[VIEW]['routing_step_id'], types['v_ai_routing_step']['id'])

    def test_ai_definition_omits_none_keys(self):
        definition = ai_view_definition(VIEW)
        self.assertEqual(set(definition), {'label', 'description'})
        self.assertNotIn(None, definition.values())

    def test_existing_views_output_is_unchanged(self):
        schema = {view: {**ai_view_definition(view), 'fields': BASE_SQL_SCHEMA[view]} for view in EXISTING_VIEWS}
        digest = hashlib.sha256(json.dumps(schema, ensure_ascii=False).encode('utf-8')).hexdigest()
        self.assertEqual(digest, EXISTING_DEFINITION_SHA256)

    def test_description_has_usage_quantity_and_no_sum_notes_and_no_fixed_values(self):
        for text in (ANALYSIS_VIEWS[VIEW]['description'], TABLE_NOTES[VIEW]):
            for part in (
                    '1行は1工程の1材料' if text is ANALYSIS_VIEWS[VIEW]['description'] else '1行=1工程の1材料',
                    'component_', '消費する部品の品番', 'consume_timing', 'START=工程開始', 'END=工程完了',
                    # 使用個数の求め方: 画面の使用個数と同じとは限らない。ビューだけで求める方法(親品コードによる探し方)
                    '画面の使用個数と同じとは限らない', '親品コードによる探し方', '同じルーティング(routing_id)の中で',
                    'output_product_code', 'parent_product_code', 'step_parent_product_code', 'component_id',
                    'output_product_id', 'step_output_product_id', 'quantity', '合計が必要',
                    '親の工程が見つからない、または該当する材料がない場合は、この方法では求められない',
                    '階層パス(hierarchy_path)', 'BOM明細の数量', '画面の使用個数と値が異なる場合がある',
                    # 合計しない注意
                    '工程の列(step_noなど)が材料の数だけ繰り返される' if text is ANALYSIS_VIEWS[VIEW]['description']
                    else '工程の列(step_no など)が材料の数だけ繰り返される',
                    '合計しない(二重に数える)', '工程の数・工程の時間は', 'v_ai_routing_step',
                    # 材料のない工程
                    '材料のない工程は、このビューに行がない', '登録された材料がない', '業務上の意味は未確認',
                    'routing_step_id にない行を探す' if text is TABLE_NOTES[VIEW] else 'routing_step_idにない行を探す',
                    'v_ai_product',
                    # 連産品の判定は、routing_step_id で工程ビューと結び、工程ビューの加工後品と v_ai_bom_item で行う(AI用ビュー作成計画 §30)
                    '連産品の判定は、',
                    'routing_step_idで工程ビューv_ai_routing_stepのidと結んで、工程ビューの加工後品output_product_codeとBOM明細ビューv_ai_bom_itemで行う(このビューにはない)'
                    if text is ANALYSIS_VIEWS[VIEW]['description']
                    else 'routing_step_id で工程ビュー v_ai_routing_step の id と結んで、工程ビューの加工後品 output_product_code とBOM明細ビュー v_ai_bom_item で行う(このビューにはない)'):
                self.assertIn(part, text)
            # 元のBOM明細(source_bom_item_id)での判定は書かない(判定に使わない)
            self.assertNotIn('source_bom_item_id', text)
            # 材料自身の remark と、工程の非公開列は説明に書かない(step_parent_product_code の元として工程の remark を述べる)
            for hidden in ('step_type', 'created_at', 'updated_at', 'description', 'contact_person', 'phone_number',
                           'order_email', 'FLOW', 'PARALLEL_POOL'):
                self.assertNotIn(hidden, text)
            # 材料自身の remark は公開しない旨があり、「公開する」とは書かれていない
            self.assertIn('材料自身のremarkは公開しない' if text is ANALYSIS_VIEWS[VIEW]['description']
                          else '材料自身の remark は公開しない', text)
            self.assertNotIn('公開する', text)
            self.assertIsNone(re.search(r'材料自身の\s*remark[^。]*(?:公開する|公開している|公開します)', text))
            check_no_fixed_values(self, text)  # 件数・具体コードを書かない

    def test_origin_table_permissions_are_not_replaced(self):
        self.assertEqual(BASE_SQL_SCHEMA['m_routing'], ('id', 'product_id', 'is_active'))
        self.assertNotIn('m_routing_step_material', BASE_SQL_SCHEMA)
        self.assertNotIn(VIEW, SCREEN_SQL_TABLES['production'])
        self.assertIn(VIEW, SCREEN_SQL_TABLES['ai_home'])

    def test_validate_datasets_without_date_field(self):
        datasets = [{'view': VIEW, 'fields': ['id', 'routing_step_id', 'quantity']}]
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
        self.assertEqual(cmd.OTHER_VIEW_COLUMNS['m_routing_step_material'], {
            'id', 'routing_step_id', 'component_id', 'quantity', 'consume_timing'})
        self.assertEqual(len(cmd.wanted_columns('m_routing_step_material')), 5)
        for column in ('remark', 'created_at', 'updated_at'):
            self.assertNotIn(column, cmd.wanted_columns('m_routing_step_material'))

    def test_published_columns_equal_source_columns(self):
        # m_routing_step_material の5列は、そのまま公開列に出る。工程・ルーティングの列は、setup_ai_views の列権限に含まれる
        material = cmd.OTHER_VIEW_COLUMNS['m_routing_step_material']
        self.assertEqual({s.split('.')[1] for s in SOURCES if s.startswith('m.')}, material)
        step, routing = cmd.OTHER_VIEW_COLUMNS['m_routing_step'], cmd.OTHER_VIEW_COLUMNS['m_routing']
        self.assertTrue({s.split('.')[1] for s in SOURCES if s.startswith('s.')} - {'remark'} <= step)
        self.assertTrue({s.split('.')[1] for s in SOURCES if s.startswith('r.')} <= routing)

    def test_migration_is_standard_left_join_without_hidden_columns(self):
        source = MIGRATION.read_text(encoding='utf-8')
        sql = migration_sql()
        for banned in ('`', 'DEFINER', 'SQL SECURITY', 'WHERE', 'pm_db', 'INNER', 'RIGHT', 'CROSS', 'GROUP', 'UNION'):
            self.assertNotIn(banned, sql)
        self.assertIn('CREATE OR REPLACE VIEW v_ai_routing_step_material AS', sql)
        self.assertEqual(sql.count('JOIN'), 6)
        self.assertEqual(len(re.findall(r'\bLEFT JOIN\b', sql)), 6)
        self.assertIn('FROM m_routing_step_material m', sql)
        # 結合キーは、すべて結合先の主キー(id)
        joins = re.findall(r'LEFT JOIN (\w+) (\w+) ON (\w+)\.(\w+) = (\w+)\.(\w+)', sql)
        self.assertEqual(len(joins), 6)
        for _table, alias, left_alias, left_column, _right_alias, _right_column in joins:
            self.assertEqual(alias, left_alias)
            self.assertEqual(left_column, 'id')
        for join in (
                'LEFT JOIN m_routing_step s ON s.id = m.routing_step_id',
                'LEFT JOIN m_routing r ON r.id = s.routing_id',
                'LEFT JOIN m_product rp ON rp.id = r.product_id',
                'LEFT JOIN m_process pr ON pr.id = s.process_id',
                'LEFT JOIN m_product op ON op.id = s.output_product_id',
                'LEFT JOIN m_product cp ON cp.id = m.component_id'):
            self.assertIn(join, sql)
        body = re.search(r'SELECT(.*?)FROM', sql, re.S).group(1)
        columns = [c.strip() for c in body.split(',') if c.strip()]
        self.assertEqual(len(columns), 20)
        names, sources = [], []
        for column in columns:
            source_column, _, alias = column.partition(' AS ')
            sources.append(source_column.strip())
            names.append(alias.strip() or source_column.split('.')[1])
        self.assertEqual(names, list(PUBLISHED))
        self.assertEqual(sources, list(SOURCES))
        for hidden in HIDDEN:
            self.assertNotIn(hidden, sql)
        # 材料自身の remark は含めない(工程の s.remark だけが、別名で入る)
        self.assertNotIn('m.remark', sql)
        self.assertEqual(sql.count('remark'), 1)
        self.assertIn("DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_routing_step_material'", source)
        self.assertIn("('ai', '0042_ai_routing_step_view')", source)
        self.assertIn("('masters', '0086_add_is_order_day_to_calendar_day')", source)

    def test_migration_dependency_exists_and_covers_source_columns(self):
        masters = Path(__file__).parent.parent / 'masters' / 'migrations'
        self.assertTrue((Path(__file__).parent / 'migrations' / '0042_ai_routing_step_view.py').exists())
        self.assertTrue((masters / '0087_routingstep_parent_product.py').exists())
        text = (masters / '0008_routingstepmaterial.py').read_text(encoding='utf-8')
        for column in ('routing_step', 'component', 'quantity', 'consume_timing'):
            self.assertIn(f"'{column}'", text)

    def test_existing_view_definitions_in_migrations_are_unchanged(self):
        for path in (Path(__file__).parent / 'migrations').glob('00[0-3]*.py'):
            self.assertNotIn(VIEW, path.read_text(encoding='utf-8'), path.name)
        for name in ('0040_ai_calendar_day_view.py', '0041_ai_bom_item_view.py', '0042_ai_routing_step_view.py'):
            self.assertNotIn(VIEW, (Path(__file__).parent / 'migrations' / name).read_text(encoding='utf-8'), name)
