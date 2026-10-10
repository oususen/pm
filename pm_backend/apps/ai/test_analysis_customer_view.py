"""得意先マスタのビュー v_ai_customer の登録を検証する。

偽のDB接続・定義の検査だけを使い、開発DBへは接続しない(SimpleTestCaseのみ)。実データの確認は、別に開発DBで読み取りだけを行う。
"""
import hashlib
import json
from pathlib import Path

from django.test import SimpleTestCase

from ai.management.commands import setup_ai_views as cmd
from ai.services import analysis_consult_service as consult
from ai.services import analysis_execution_service as service
from ai.services.analysis_data_service import ANALYSIS_VIEWS, ai_view_definition, build_where, validate_datasets
from ai.services.sql_queries import BASE_SQL_SCHEMA, SCREEN_SQL_TABLES, TABLE_NOTES

CUSTOMER = 'v_ai_customer'
EXISTING_VIEWS = (
    'v_ai_shipment', 'v_ai_purchase_receipt', 'v_ai_product', 'v_ai_process', 'v_ai_line', 'v_ai_supplier')
PERIOD = ('2026-09-01', '2026-09-30')
PUBLISHED = ('id', 'customer_code', 'customer_name', 'short_name', 'calendar_id', 'is_active')
HIDDEN = ('created_at', 'updated_at')
# v_ai_customer 追加前の、既存6ビューのAIへ渡す定義(fields付き)のJSONのSHA-256。1文字でも変わると不一致になる
# (v_ai_customer を追加する前後の両方で、独立に計算した値。仕入先ビューの試験の既存5ビューの値とは別)
EXISTING_DEFINITION_SHA256 = '8ca47c57f9e27a60ed1822ffca227599e41056c0774c8934ba814faaaa7d2de1'
SHIPMENT = 'v_ai_shipment'


class CustomerViewDefinitionTest(SimpleTestCase):
    def test_customer_view_is_registered_without_date_field(self):
        definition = ANALYSIS_VIEWS[CUSTOMER]
        self.assertIsNone(definition['date_field'])
        self.assertIsNone(definition['quantity_field'])
        self.assertEqual(definition['label'], '得意先マスタ')

    def test_column_types_match_published_columns_exactly(self):
        self.assertEqual(BASE_SQL_SCHEMA[CUSTOMER], PUBLISHED)
        self.assertEqual(set(service.ANALYSIS_COLUMN_TYPES[CUSTOMER]), set(BASE_SQL_SCHEMA[CUSTOMER]))
        self.assertEqual(service.ANALYSIS_COLUMN_TYPES[CUSTOMER], {
            'id': 'BIGINT', 'customer_code': 'VARCHAR', 'customer_name': 'VARCHAR', 'short_name': 'VARCHAR',
            'calendar_id': 'BIGINT', 'is_active': 'BIGINT'})

    def test_ai_definition_omits_none_keys(self):
        definition = ai_view_definition(CUSTOMER)
        self.assertEqual(set(definition), {'label', 'description'})
        self.assertNotIn(None, definition.values())

    def test_existing_views_output_is_unchanged(self):
        schema = {view: {**ai_view_definition(view), 'fields': BASE_SQL_SCHEMA[view]} for view in EXISTING_VIEWS}
        digest = hashlib.sha256(json.dumps(schema, ensure_ascii=False).encode('utf-8')).hexdigest()
        self.assertEqual(digest, EXISTING_DEFINITION_SHA256)

    def test_shipment_view_columns_and_description_are_unchanged(self):
        # 出荷実績ビューの customer_code は残り、得意先マスタの追加で列が増えていない
        self.assertIn('customer_code', BASE_SQL_SCHEMA[SHIPMENT])
        self.assertNotIn('customer_name', BASE_SQL_SCHEMA[SHIPMENT])
        self.assertNotIn('short_name', BASE_SQL_SCHEMA[SHIPMENT])
        self.assertNotIn(CUSTOMER, ANALYSIS_VIEWS[SHIPMENT]['description'])
        self.assertNotIn(CUSTOMER, TABLE_NOTES[SHIPMENT])

    def test_description_has_required_notes_and_no_hidden_text(self):
        for text in (ANALYSIS_VIEWS[CUSTOMER]['description'], TABLE_NOTES[CUSTOMER]):
            for part in ('1得意先', 'is_active=1', '先頭ゼロ', '数字として扱わない', '得意先コード', '会社名', '略称',
                         'v_ai_shipment', 'customer_code', '同じ文字列', 'calendar_id', '稼働カレンダ', '有効(1)'):
                self.assertIn(part, text)
            # 非公開列・具体的な得意先コード・得意先の名称は、説明に書かない(BOSS承認)
            for hidden in HIDDEN + ('000196', '000018', '000001', 'クボタ', 'リーデン', 'ティエラ'):
                self.assertNotIn(hidden, text)

    def test_origin_table_permissions_are_not_replaced(self):
        self.assertIn('m_customer', BASE_SQL_SCHEMA)
        self.assertEqual(BASE_SQL_SCHEMA['m_customer'], ('id', 'customer_code'))
        # 元テーブルm_customerの許可(受注画面)は、ビューの追加後も残る(置き換えない)
        self.assertIn('m_customer', SCREEN_SQL_TABLES['orders'])

    def test_validate_datasets_accepts_customer_without_date_field(self):
        datasets = [{'view': CUSTOMER, 'fields': ['id', 'customer_code']}]
        self.assertEqual(validate_datasets(datasets, *PERIOD), datasets)
        self.assertEqual(build_where(CUSTOMER, *PERIOD), ('', []))

    def test_consult_prompt_has_no_null_keys(self):
        prompt = consult._system_prompt([])
        self.assertIn(CUSTOMER, prompt)
        self.assertNotIn('"date_field": null', prompt)
        self.assertNotIn('"quantity_field": null', prompt)

    def test_setup_command_covers_customer_view(self):
        self.assertEqual(cmd.SIMPLE_MASTER_VIEWS[CUSTOMER], 'm_customer')
        self.assertEqual(cmd.wanted_columns('m_customer'), set(PUBLISHED))

    def test_migration_is_standard_sql_without_hidden_columns(self):
        source = (Path(__file__).parent / 'migrations' / '0039_ai_customer_view.py').read_text(encoding='utf-8')
        sql = source.split('CREATE_VIEW = """')[1].split('"""')[0]
        self.assertIn('FROM m_customer', sql)
        for banned in ('`', 'DEFINER', 'SQL SECURITY', 'WHERE', 'JOIN', 'pm_db'):
            self.assertNotIn(banned, sql)
        self.assertEqual(sql.count(' AS'), 1)  # 列の別名なし(ビュー名の AS だけ)
        for column in PUBLISHED:
            self.assertIn(f'    {column}', sql)
        for hidden in HIDDEN:
            self.assertNotIn(hidden, sql)
        self.assertIn("DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_customer'", source)

    def test_existing_view_definitions_in_migrations_are_unchanged(self):
        # 既存ビューのマイグレーションに v_ai_customer が混入していない
        for path in (Path(__file__).parent / 'migrations').glob('00[0-3]*.py'):
            if path.name.startswith('0039'):
                continue
            self.assertNotIn(CUSTOMER, path.read_text(encoding='utf-8'), path.name)
