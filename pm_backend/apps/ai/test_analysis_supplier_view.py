"""仕入先マスタのビュー v_ai_supplier の登録を検証する。

偽のDB接続・定義の検査だけを使い、開発DBへは接続しない(SimpleTestCaseのみ)。実データの確認は、別に開発DBで読み取りだけを行う。
"""
import hashlib
import json
from pathlib import Path

from django.test import SimpleTestCase

from ai.services import analysis_consult_service as consult
from ai.services import analysis_execution_service as service
from ai.services.analysis_data_service import ANALYSIS_VIEWS, ai_view_definition, build_where, validate_datasets
from ai.services.sql_queries import BASE_SQL_SCHEMA, SCREEN_SQL_TABLES, TABLE_NOTES

SUPPLIER = 'v_ai_supplier'
EXISTING_VIEWS = ('v_ai_shipment', 'v_ai_purchase_receipt', 'v_ai_product', 'v_ai_process', 'v_ai_line')
PERIOD = ('2026-09-01', '2026-09-30')
PUBLISHED = ('id', 'supplier_code', 'supplier_name', 'supplier_type', 'calendar_id')
HIDDEN = ('contact_person', 'phone_number', 'order_email')
# v_ai_supplier 追加前の、既存5ビューのAIへ渡す定義(fields付き)のJSONのSHA-256。1文字でも変わると不一致になる
# (v_ai_supplier を追加する前の定義から、独立に計算した値。既存4ビューの値は test_analysis_line_view.py の値と一致を確認済み)
EXISTING_DEFINITION_SHA256 = 'aaed5cd71d844171d20fc26e92ab5a257bec3b4929b7c54e88781206a4abe454'
# 入荷実績ビューの定義(列・説明)。v_ai_supplier の追加で変わっていないこと
RECEIPT = 'v_ai_purchase_receipt'


class SupplierViewDefinitionTest(SimpleTestCase):
    def test_supplier_view_is_registered_without_date_field(self):
        definition = ANALYSIS_VIEWS[SUPPLIER]
        self.assertIsNone(definition['date_field'])
        self.assertIsNone(definition['quantity_field'])
        self.assertEqual(definition['label'], '仕入先マスタ')

    def test_column_types_match_published_columns_exactly(self):
        self.assertEqual(BASE_SQL_SCHEMA[SUPPLIER], PUBLISHED)
        self.assertEqual(set(service.ANALYSIS_COLUMN_TYPES[SUPPLIER]), set(BASE_SQL_SCHEMA[SUPPLIER]))
        self.assertEqual(service.ANALYSIS_COLUMN_TYPES[SUPPLIER], {
            'id': 'BIGINT', 'supplier_code': 'VARCHAR', 'supplier_name': 'VARCHAR', 'supplier_type': 'VARCHAR',
            'calendar_id': 'BIGINT'})

    def test_ai_definition_omits_none_keys(self):
        definition = ai_view_definition(SUPPLIER)
        self.assertEqual(set(definition), {'label', 'description'})
        self.assertNotIn(None, definition.values())

    def test_existing_views_output_is_unchanged(self):
        schema = {view: {**ai_view_definition(view), 'fields': BASE_SQL_SCHEMA[view]} for view in EXISTING_VIEWS}
        digest = hashlib.sha256(json.dumps(schema, ensure_ascii=False).encode('utf-8')).hexdigest()
        self.assertEqual(digest, EXISTING_DEFINITION_SHA256)

    def test_receipt_view_columns_and_description_are_unchanged(self):
        # 入荷実績ビューの supplier_id は残り、仕入先マスタの追加で列が増えていない
        self.assertIn('supplier_id', BASE_SQL_SCHEMA[RECEIPT])
        self.assertNotIn('supplier_code', BASE_SQL_SCHEMA[RECEIPT])
        self.assertNotIn('supplier_name', BASE_SQL_SCHEMA[RECEIPT])
        self.assertNotIn(SUPPLIER, ANALYSIS_VIEWS[RECEIPT]['description'])
        self.assertNotIn(SUPPLIER, TABLE_NOTES[RECEIPT])

    def test_description_has_required_notes_and_no_hidden_text(self):
        for text in (ANALYSIS_VIEWS[SUPPLIER]['description'], TABLE_NOTES[SUPPLIER]):
            for part in ('1仕入先', 'is_active', '先頭ゼロ', '000044', 'G00001', '数字として扱わない', '仕入先コード',
                         '会社名', 'purchase=購入', 'outsource=外作', 'both=両方', '購入先・外作先を分ける',
                         'calendar_id', '稼働カレンダ', 'v_ai_purchase_receipt', 'supplier_id', 'v_ai_line',
                         'PURCHASE', 'supplier_code', 'line_code', '同じ文字列', '1対1'):
                self.assertIn(part, text)
            for hidden in HIDDEN + ('000196', 'クボタ'):
                self.assertNotIn(hidden, text)

    def test_origin_table_permissions_are_not_replaced(self):
        self.assertIn('m_supplier', BASE_SQL_SCHEMA)
        self.assertIn('m_supplier', TABLE_NOTES)
        # 元テーブルm_supplierの許可は、ビューの追加後も残る(置き換えない)
        self.assertTrue(any('m_supplier' in tables for tables in SCREEN_SQL_TABLES.values()))
        self.assertIn('m_supplier', SCREEN_SQL_TABLES['purchase'])

    def test_validate_datasets_accepts_supplier_without_date_field(self):
        datasets = [{'view': SUPPLIER, 'fields': ['id', 'supplier_code']}]
        self.assertEqual(validate_datasets(datasets, *PERIOD), datasets)
        self.assertEqual(build_where(SUPPLIER, *PERIOD), ('', []))

    def test_consult_prompt_has_no_null_keys(self):
        prompt = consult._system_prompt([])
        self.assertIn(SUPPLIER, prompt)
        self.assertNotIn('"date_field": null', prompt)
        self.assertNotIn('"quantity_field": null', prompt)

    def test_migration_is_standard_sql_without_hidden_columns(self):
        source = (Path(__file__).parent / 'migrations' / '0038_ai_supplier_view.py').read_text(encoding='utf-8')
        sql = source.split('CREATE_VIEW = """')[1].split('"""')[0]
        self.assertIn('FROM m_supplier', sql)
        for banned in ('`', 'DEFINER', 'SQL SECURITY', 'WHERE', 'JOIN', 'pm_db'):
            self.assertNotIn(banned, sql)
        self.assertEqual(sql.count(' AS'), 1)  # 列の別名なし(ビュー名の AS だけ)
        for column in PUBLISHED:
            self.assertIn(f'    {column}', sql)
        for hidden in HIDDEN:
            self.assertNotIn(hidden, sql)
        self.assertIn("DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_supplier'", source)
