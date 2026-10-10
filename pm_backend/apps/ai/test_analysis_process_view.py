"""工程マスタのビュー v_ai_process の登録を検証する。

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

PROCESS = 'v_ai_process'
EXISTING_VIEWS = ('v_ai_shipment', 'v_ai_purchase_receipt', 'v_ai_product')
PERIOD = ('2026-09-01', '2026-09-30')
PUBLISHED = ('id', 'process_code', 'process_name', 'line_id', 'management_unit', 'operating_rate',
             'equipment_count', 'two_person_only', 'is_active')
# 既存3ビューのAIへ渡す定義(fields付き)のJSONのSHA-256。1文字でも変わると不一致になる
# (2026-10-10 v_ai_product を32列から30列へ修正したため、値を更新。出荷・入荷の2ビューは test_analysis_product_view.py でも別に固定)
EXISTING_DEFINITION_SHA256 = '4d111066d0c283fc4a5ef5d6f4ca772d57d063f7d240fdf39529b97d1ddeb284'


class ProcessViewDefinitionTest(SimpleTestCase):
    def test_process_view_is_registered_without_date_field(self):
        definition = ANALYSIS_VIEWS[PROCESS]
        self.assertIsNone(definition['date_field'])
        self.assertIsNone(definition['quantity_field'])
        self.assertEqual(definition['label'], '工程マスタ')

    def test_column_types_match_published_columns_exactly(self):
        self.assertEqual(BASE_SQL_SCHEMA[PROCESS], PUBLISHED)
        self.assertEqual(set(service.ANALYSIS_COLUMN_TYPES[PROCESS]), set(BASE_SQL_SCHEMA[PROCESS]))
        self.assertEqual(service.ANALYSIS_COLUMN_TYPES[PROCESS], {
            'id': 'BIGINT', 'process_code': 'VARCHAR', 'process_name': 'VARCHAR', 'line_id': 'BIGINT',
            'management_unit': 'VARCHAR', 'operating_rate': 'DECIMAL(18,2)', 'equipment_count': 'BIGINT',
            'two_person_only': 'BIGINT', 'is_active': 'BIGINT'})

    def test_ai_definition_omits_none_keys(self):
        definition = ai_view_definition(PROCESS)
        self.assertEqual(set(definition), {'label', 'description'})
        self.assertNotIn(None, definition.values())

    def test_existing_views_output_is_unchanged(self):
        schema = {view: {**ai_view_definition(view), 'fields': BASE_SQL_SCHEMA[view]} for view in EXISTING_VIEWS}
        digest = hashlib.sha256(json.dumps(schema, ensure_ascii=False).encode('utf-8')).hexdigest()
        self.assertEqual(digest, EXISTING_DEFINITION_SHA256)

    def test_description_has_required_notes_and_no_hidden_text(self):
        for text in (ANALYSIS_VIEWS[PROCESS]['description'], TABLE_NOTES[PROCESS]):
            for part in ('1工程', 'is_active=1', '先頭ゼロ', '0801', 'DAY=日単位管理', 'MINUTE=分単位管理', '業務上の定義は未確認'):
                self.assertIn(part, text)
            for hidden in ('is_outsource', 'created_at', 'updated_at', '000196', 'クボタ', 'レーザ1'):
                self.assertNotIn(hidden, text)
            self.assertNotIn('外注かどうか', text)

    def test_origin_table_permissions_are_not_replaced(self):
        self.assertIn('m_process', BASE_SQL_SCHEMA)
        for screen in ('production', 'quality', 'masters'):
            self.assertIn('m_process', SCREEN_SQL_TABLES[screen])
            self.assertNotIn(PROCESS, SCREEN_SQL_TABLES[screen])

    def test_validate_datasets_accepts_process_without_date_field(self):
        datasets = [{'view': PROCESS, 'fields': ['id', 'process_code']}]
        self.assertEqual(validate_datasets(datasets, *PERIOD), datasets)
        self.assertEqual(build_where(PROCESS, *PERIOD), ('', []))

    def test_consult_prompt_has_no_null_keys(self):
        prompt = consult._system_prompt([])
        self.assertIn(PROCESS, prompt)
        self.assertNotIn('"date_field": null', prompt)
        self.assertNotIn('"quantity_field": null', prompt)

    def test_migration_is_standard_sql_without_hidden_columns(self):
        source = (Path(__file__).parent / 'migrations' / '0035_ai_process_view.py').read_text(encoding='utf-8')
        sql = source.split('CREATE_VIEW = """')[1].split('"""')[0]
        self.assertIn('FROM m_process', sql)
        for banned in ('`', 'DEFINER', 'SQL SECURITY', 'WHERE', 'JOIN', 'pm_db'):
            self.assertNotIn(banned, sql)
        self.assertEqual(sql.count(' AS'), 1)  # 列の別名なし(ビュー名の AS だけ)
        for column in PUBLISHED:
            self.assertIn(f'    {column}', sql)
        for hidden in ('is_outsource', 'created_at', 'updated_at'):
            self.assertNotIn(hidden, sql)
