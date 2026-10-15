"""設備マスタのビュー v_ai_equipment の登録を検証する。

偽のDB接続・定義の検査だけを使い、開発DBへは接続しない(SimpleTestCaseのみ)。実データの確認は、別に開発DBで読み取りだけを行う。

注記: 前回のevaluatorの指摘(AI用ビュー作成計画 §32の条件付き合格)により、TABLE_NOTES[EQUIPMENT] を追加し、
本ファイルにも他の単純マスタビューの試験(例: test_analysis_line_view.py)と同様に TABLE_NOTES の検証を追加した。
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

EQUIPMENT = 'v_ai_equipment'
EXISTING_VIEWS = (
    'v_ai_shipment', 'v_ai_purchase_receipt', 'v_ai_product', 'v_ai_process', 'v_ai_line', 'v_ai_supplier',
    'v_ai_customer',
)
PERIOD = ('2026-09-01', '2026-09-30')
PUBLISHED = ('id', 'equipment_code', 'equipment_name', 'is_active', 'line_id', 'process_id')
HIDDEN = ('display_order', 'notes', 'created_at', 'updated_at')
# v_ai_equipment 追加前の、既存7ビューのAIへ渡す定義(fields付き)のJSONのSHA-256。1文字でも変わると不一致になる
EXISTING_DEFINITION_SHA256 = 'db31acbfe065946a26dc439a40b4076ca41530869749bedf1f92e06600a410ed'


class EquipmentViewDefinitionTest(SimpleTestCase):
    def test_equipment_view_is_registered_without_date_field(self):
        definition = ANALYSIS_VIEWS[EQUIPMENT]
        self.assertIsNone(definition['date_field'])
        self.assertIsNone(definition['quantity_field'])
        self.assertEqual(definition['label'], '設備マスタ')

    def test_column_types_match_published_columns_exactly(self):
        self.assertEqual(BASE_SQL_SCHEMA[EQUIPMENT], PUBLISHED)
        self.assertEqual(set(service.ANALYSIS_COLUMN_TYPES[EQUIPMENT]), set(BASE_SQL_SCHEMA[EQUIPMENT]))
        self.assertEqual(service.ANALYSIS_COLUMN_TYPES[EQUIPMENT], {
            'id': 'BIGINT', 'equipment_code': 'VARCHAR', 'equipment_name': 'VARCHAR',
            'is_active': 'BIGINT', 'line_id': 'BIGINT', 'process_id': 'BIGINT'})

    def test_ai_definition_omits_none_keys(self):
        definition = ai_view_definition(EQUIPMENT)
        self.assertEqual(set(definition), {'label', 'description'})
        self.assertNotIn(None, definition.values())

    def test_existing_views_output_is_unchanged(self):
        schema = {view: {**ai_view_definition(view), 'fields': BASE_SQL_SCHEMA[view]} for view in EXISTING_VIEWS}
        digest = hashlib.sha256(json.dumps(schema, ensure_ascii=False).encode('utf-8')).hexdigest()
        self.assertEqual(digest, EXISTING_DEFINITION_SHA256)

    def test_description_has_required_notes_and_no_hidden_text(self):
        text = ANALYSIS_VIEWS[EQUIPMENT]['description']
        for part in ('1設備', 'is_active=1', '設備コード', '設備名', 'v_ai_line', 'v_ai_process',
                     'YB-006/009/010', 'process_idが単一に決まらずNULL', '有効(1)'):
            self.assertIn(part, text)
        for hidden in HIDDEN:
            self.assertNotIn(hidden, text)

    def test_table_notes_entry_exists_and_is_not_empty(self):
        # 他の単純マスタビューの試験(例: test_analysis_line_view.py)と同様に、TABLE_NOTES への登録を検証する
        self.assertIn(EQUIPMENT, TABLE_NOTES)
        text = TABLE_NOTES[EQUIPMENT]
        self.assertTrue(text)
        for part in ('1設備', 'is_active=1', '設備コード', '設備名', 'v_ai_line', 'v_ai_process',
                     'YB-006・YB-009・YB-010', 'process_code 4010・4040', '空(NULL)', '有効(1)・無効(0)'):
            self.assertIn(part, text)
        for hidden in HIDDEN:
            self.assertNotIn(hidden, text)
        self.assertNotIn('クボタ', text)

    def test_table_notes_entry_is_included_in_ai_home_schema_text(self):
        # 前回のevaluator指摘: AI_HOME_EXCLUDED_TABLES に含まれないため、ai_home画面の自由SQL生成プロンプトに含まれるはず
        from ai.services.sql_queries import AI_HOME_EXCLUDED_TABLES, schema_text
        self.assertNotIn(EQUIPMENT, AI_HOME_EXCLUDED_TABLES)
        text = schema_text('ai_home')
        self.assertIn(f'- {EQUIPMENT}:', text)
        self.assertIn(TABLE_NOTES[EQUIPMENT], text)

    def test_origin_table_permissions_are_not_replaced(self):
        # m_equipment は、このビュー追加以前からどの画面にも直接の許可を持たない(置き換えの対象がない)
        self.assertNotIn('m_equipment', BASE_SQL_SCHEMA)
        for screen, tables in SCREEN_SQL_TABLES.items():
            if screen == 'ai_home':
                continue
            self.assertNotIn(EQUIPMENT, tables)

    def test_validate_datasets_accepts_equipment_without_date_field(self):
        datasets = [{'view': EQUIPMENT, 'fields': ['id', 'equipment_code']}]
        self.assertEqual(validate_datasets(datasets, *PERIOD), datasets)
        self.assertEqual(build_where(EQUIPMENT, *PERIOD), ('', []))

    def test_consult_prompt_has_no_null_keys(self):
        prompt = consult._system_prompt([])
        self.assertIn(EQUIPMENT, prompt)
        self.assertNotIn('"date_field": null', prompt)
        self.assertNotIn('"quantity_field": null', prompt)

    def test_setup_command_covers_equipment_view(self):
        self.assertEqual(cmd.SIMPLE_MASTER_VIEWS[EQUIPMENT], 'm_equipment')
        self.assertEqual(cmd.wanted_columns('m_equipment'), set(PUBLISHED))

    def test_migration_is_standard_sql_without_hidden_columns(self):
        source = (Path(__file__).parent / 'migrations' / '0054_ai_equipment_view.py').read_text(encoding='utf-8')
        sql = source.split('CREATE_VIEW = """')[1].split('"""')[0]
        self.assertIn('FROM m_equipment', sql)
        for banned in ('`', 'DEFINER', 'SQL SECURITY', 'WHERE', 'JOIN', 'pm_db'):
            self.assertNotIn(banned, sql)
        self.assertEqual(sql.count(' AS'), 1)  # 列の別名なし(ビュー名の AS だけ)
        for column in PUBLISHED:
            self.assertIn(f'    {column}', sql)
        for hidden in HIDDEN:
            self.assertNotIn(hidden, sql)
        self.assertIn("DROP_VIEW = 'DROP VIEW IF EXISTS v_ai_equipment'", source)

    def test_existing_view_definitions_in_migrations_are_unchanged(self):
        # 既存ビューのマイグレーションに v_ai_equipment が混入していない
        for path in (Path(__file__).parent / 'migrations').glob('0[0-4]*.py'):
            if path.name.startswith('0054'):
                continue
            self.assertNotIn(EQUIPMENT, path.read_text(encoding='utf-8'), path.name)
