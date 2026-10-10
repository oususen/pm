"""ラインマスタのビュー v_ai_line の登録を検証する。

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

LINE = 'v_ai_line'
EXISTING_VIEWS = ('v_ai_shipment', 'v_ai_purchase_receipt', 'v_ai_product', 'v_ai_process')
PERIOD = ('2026-09-01', '2026-09-30')
PUBLISHED = ('id', 'line_code', 'line_name', 'calendar_id', 'line_type', 'is_active')
HIDDEN = ('lead_time_days', 'use_direct_process', 'created_at', 'updated_at')
# v_ai_line 追加前の、既存4ビューのAIへ渡す定義(fields付き)のJSONのSHA-256。1文字でも変わると不一致になる
# (2026-10-10 v_ai_product を32列から30列へ修正したため、値を更新)
EXISTING_DEFINITION_SHA256 = '12dd177030beb76568354de6fe0b35a96a4de4fc974f22dc7a178a05f005bd1a'


class LineViewDefinitionTest(SimpleTestCase):
    def test_line_view_is_registered_without_date_field(self):
        definition = ANALYSIS_VIEWS[LINE]
        self.assertIsNone(definition['date_field'])
        self.assertIsNone(definition['quantity_field'])
        self.assertEqual(definition['label'], 'ラインマスタ')

    def test_column_types_match_published_columns_exactly(self):
        self.assertEqual(BASE_SQL_SCHEMA[LINE], PUBLISHED)
        self.assertEqual(set(service.ANALYSIS_COLUMN_TYPES[LINE]), set(BASE_SQL_SCHEMA[LINE]))
        self.assertEqual(service.ANALYSIS_COLUMN_TYPES[LINE], {
            'id': 'BIGINT', 'line_code': 'VARCHAR', 'line_name': 'VARCHAR', 'calendar_id': 'BIGINT',
            'line_type': 'VARCHAR', 'is_active': 'BIGINT'})

    def test_ai_definition_omits_none_keys(self):
        definition = ai_view_definition(LINE)
        self.assertEqual(set(definition), {'label', 'description'})
        self.assertNotIn(None, definition.values())

    def test_existing_views_output_is_unchanged(self):
        schema = {view: {**ai_view_definition(view), 'fields': BASE_SQL_SCHEMA[view]} for view in EXISTING_VIEWS}
        digest = hashlib.sha256(json.dumps(schema, ensure_ascii=False).encode('utf-8')).hexdigest()
        self.assertEqual(digest, EXISTING_DEFINITION_SHA256)

    def test_description_has_required_notes_and_no_hidden_text(self):
        for text in (ANALYSIS_VIEWS[LINE]['description'], TABLE_NOTES[LINE]):
            for part in ('1ライン', 'is_active=1', '先頭ゼロ', '000044', 'PROD=社内ライン', 'PURCHASE=仕入先の購買ライン',
                         '仕入先コード', '仕入先の会社名', 'OUTSOURCE=外作ライン', '削除予定', 'OTHER=クボタ納期調整',
                         '意味の文章は未確認', 'calendar_id', 'v_ai_process'):
                self.assertIn(part, text)
            for hidden in HIDDEN + ('000196',):
                self.assertNotIn(hidden, text)
            # 購買ラインの is_active の扱いは書かない(ER図と実データが食い違うため)
            self.assertNotIn('意図的', text)

    def test_origin_table_permissions_are_not_replaced(self):
        self.assertIn('m_line', BASE_SQL_SCHEMA)
        self.assertIn('m_line', TABLE_NOTES)
        # 元テーブルm_lineの許可は、ビューの追加後も残る(置き換えない)
        for screen in ('ai_home', 'production', 'quality', 'purchase', 'masters'):
            self.assertIn('m_line', SCREEN_SQL_TABLES[screen])

    def test_validate_datasets_accepts_line_without_date_field(self):
        datasets = [{'view': LINE, 'fields': ['id', 'line_code']}]
        self.assertEqual(validate_datasets(datasets, *PERIOD), datasets)
        self.assertEqual(build_where(LINE, *PERIOD), ('', []))

    def test_consult_prompt_has_no_null_keys(self):
        prompt = consult._system_prompt([])
        self.assertIn(LINE, prompt)
        self.assertNotIn('"date_field": null', prompt)
        self.assertNotIn('"quantity_field": null', prompt)

    def test_migration_is_standard_sql_without_hidden_columns(self):
        source = (Path(__file__).parent / 'migrations' / '0036_ai_line_view.py').read_text(encoding='utf-8')
        sql = source.split('CREATE_VIEW = """')[1].split('"""')[0]
        self.assertIn('FROM m_line', sql)
        for banned in ('`', 'DEFINER', 'SQL SECURITY', 'WHERE', 'JOIN', 'pm_db'):
            self.assertNotIn(banned, sql)
        self.assertEqual(sql.count(' AS'), 1)  # 列の別名なし(ビュー名の AS だけ)
        for column in PUBLISHED:
            self.assertIn(f'    {column}', sql)
        for hidden in HIDDEN:
            self.assertNotIn(hidden, sql)
        self.assertIn("DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_line'", source)
