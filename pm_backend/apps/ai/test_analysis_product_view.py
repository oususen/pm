"""品番マスタのビュー v_ai_product の登録(サイクルC)を検証する。

偽のDB接続だけを使い、開発DBへは接続しない(SimpleTestCaseのみ)。実データの確認は、別に開発DBで読み取りだけを行う。
"""
import hashlib
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from ai.services import analysis_data_service as data_service
from ai.services import analysis_codegen_service as codegen
from ai.services import analysis_consult_service as consult
from ai.services import analysis_execution_service as service
from ai.services.analysis_data_service import ANALYSIS_VIEWS, ai_view_definition, build_where, count_target_rows, validate_datasets
from ai.services.analysis_planning_service import _conditions_text
from ai.services.sql_queries import BASE_SQL_SCHEMA

PRODUCT = 'v_ai_product'
DATED_VIEWS = ('v_ai_purchase_receipt', 'v_ai_shipment')
PERIOD = ('2026-09-01', '2026-09-30')
# サイクルC着手前(既存2ビュー)の、AIへ渡す定義(fields付き)のJSONのSHA-256。1文字でも変わると不一致になる
DATED_DEFINITION_SHA256 = '167854774bfa048ade19cfeaff68502b4abe21a83b58c0cb67db1aecc91094bc'


class ProductViewDefinitionTest(SimpleTestCase):
    def test_product_view_is_registered_without_date_field(self):
        definition = ANALYSIS_VIEWS[PRODUCT]
        self.assertIsNone(definition['date_field'])
        self.assertIsNone(definition['quantity_field'])
        self.assertEqual(definition['label'], '品番マスタ')

    def test_column_types_match_published_columns_exactly(self):
        self.assertEqual(set(service.ANALYSIS_COLUMN_TYPES[PRODUCT]), set(BASE_SQL_SCHEMA[PRODUCT]))
        self.assertEqual(len(BASE_SQL_SCHEMA[PRODUCT]), 30)

    def test_hidden_columns_are_not_in_view_dictionary_or_description(self):
        # 非公開6列(BOSS判断。作成日・更新日は2026-10-10に非公開へ修正)が、辞書・列型・説明に入らない
        from ai.services.sql_queries import TABLE_NOTES
        hidden = ('image_url', 'product_name_halfwidth', 'is_phantom', 'self_lt_days', 'created_at', 'updated_at')
        description = ANALYSIS_VIEWS[PRODUCT]['description']
        for name in hidden:
            self.assertNotIn(name, BASE_SQL_SCHEMA[PRODUCT])
            self.assertNotIn(name, service.ANALYSIS_COLUMN_TYPES[PRODUCT])
            self.assertNotIn(name, description)
            self.assertNotIn(name, TABLE_NOTES[PRODUCT])

    def test_migration_0037_is_standard_sql_with_30_published_columns(self):
        from pathlib import Path
        source = (Path(__file__).parent / 'migrations' / '0037_ai_product_view_remove_dates.py').read_text(encoding='utf-8')
        sql = source.split('CREATE_VIEW = """')[1].split('"""')[0]
        self.assertIn('FROM m_product', sql)
        for banned in ('`', 'DEFINER', 'SQL SECURITY', 'WHERE', 'JOIN', 'pm_db'):
            self.assertNotIn(banned, sql)
        self.assertEqual(sql.count(' AS'), 1)  # 列の別名なし(ビュー名の AS だけ)
        body = sql.split('SELECT')[1].split('FROM')[0]
        columns = [line.strip().rstrip(',') for line in body.strip().splitlines()]
        self.assertEqual(tuple(columns), BASE_SQL_SCHEMA[PRODUCT])
        for hidden in ('image_url', 'product_name_halfwidth', 'is_phantom', 'self_lt_days', 'created_at', 'updated_at'):
            self.assertNotIn(hidden, sql)
        # ロールバック用の32列(0034と同じ)には、作成日・更新日が入る
        restore = source.split('RESTORE_VIEW_32 = """')[1].split('"""')[0]
        self.assertIn('created_at', restore)
        self.assertIn('updated_at', restore)

    def test_description_has_required_notes_and_no_personal_text(self):
        text = ANALYSIS_VIEWS[PRODUCT]['description']
        for part in ('1行は1品番', '全行が対象', 'is_active=1', 'product_id', 'unit_price=単価(空の品番が多い)', 'line_id=ラインのID(空の品番がある)',
                     'process_id=工程のID(空の品番がある)', '業務上の意味は未確認'):
            self.assertIn(part, text)
        self.assertNotIn('image_url', text)
        self.assertNotIn('000196', text)

    def test_ai_definition_omits_none_keys_for_product_only(self):
        definition = ai_view_definition(PRODUCT)
        self.assertEqual(set(definition), {'label', 'description'})
        for view in DATED_VIEWS:
            self.assertEqual(ai_view_definition(view), ANALYSIS_VIEWS[view])  # 日付ありは、従来と同じ内容(キーの順序も同じ)
            self.assertEqual(list(ai_view_definition(view)), list(ANALYSIS_VIEWS[view]))

    def test_dated_views_definition_output_is_unchanged(self):
        schema = {view: {**ai_view_definition(view), 'fields': BASE_SQL_SCHEMA[view]} for view in DATED_VIEWS}
        digest = hashlib.sha256(json.dumps(schema, ensure_ascii=False).encode('utf-8')).hexdigest()
        self.assertEqual(digest, DATED_DEFINITION_SHA256)

    def test_consult_prompt_has_no_null_keys(self):
        prompt = consult._system_prompt([])
        self.assertIn(PRODUCT, prompt)
        self.assertNotIn('null, "quantity_field"', prompt)
        self.assertNotIn('"date_field": null', prompt)
        self.assertNotIn('"quantity_field": null', prompt)
        self.assertIn('"date_field": "shipment_date"', prompt)  # 日付ありは従来どおり

    def test_validate_datasets_accepts_product_without_date_field(self):
        datasets = [{'view': PRODUCT, 'fields': ['id', 'product_code']}]
        self.assertEqual(validate_datasets(datasets, *PERIOD), datasets)

    def test_build_where_for_product_has_no_period(self):
        self.assertEqual(build_where(PRODUCT, *PERIOD), ('', []))


class PeriodAppliedAndConditionsTest(SimpleTestCase):
    def _count(self, datasets, rows):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.side_effect = [(n,) for n in rows]
        connection = MagicMock()
        connection.cursor.return_value = cursor
        with patch.object(data_service, 'settings', SimpleNamespace(DATABASES={'ai_reader': {'USER': 'pm_ai_reader'}})), patch.object(
                data_service, 'connections', {'ai_reader': connection}):
            return count_target_rows({'datasets': datasets, 'date_from': PERIOD[0], 'date_to': PERIOD[1]}), cursor

    def test_count_response_has_period_applied(self):
        preview, cursor = self._count([
            {'view': 'v_ai_shipment', 'fields': ['id', 'shipment_date']}, {'view': PRODUCT, 'fields': ['id', 'product_code']}], [5, 2850])
        self.assertEqual(preview['datasets'], [
            {'view': 'v_ai_shipment', 'rows': 5, 'period_applied': True}, {'view': PRODUCT, 'rows': 2850, 'period_applied': False}])
        self.assertEqual(preview['total_rows'], 2855)
        self.assertEqual(cursor.execute.call_args_list[1].args, ('SELECT COUNT(*) FROM `v_ai_product`', []))

    def test_conditions_text(self):
        dated = {'view': 'v_ai_shipment', 'fields': ['id']}
        product = {'view': PRODUCT, 'fields': ['id']}
        self.assertEqual(_conditions_text([dated]), '指定期間の全登録行（追加の絞り条件なし）')  # 従来と同じ文
        self.assertEqual(_conditions_text([product]), '全行（期間で絞らない。追加の絞り条件なし）')
        self.assertIn('日付のないビューは全行', _conditions_text([dated, product]))


class CodegenDatelessRuleTest(SimpleTestCase):
    def _plan(self, datasets):
        return {'owner_id': 1, 'proposal': {
            'purpose': '品番の一覧', 'steps': ['集計する'], 'outputs': ['表'], 'date_from': PERIOD[0], 'date_to': PERIOD[1],
            'datasets': datasets}}

    def test_rule_added_only_when_dateless_view_is_included(self):
        dated = codegen.build_messages(self._plan([{'view': 'v_ai_shipment', 'fields': ['id', 'shipment_date']}]), False)
        self.assertEqual(dated[0]['content'], codegen.SYSTEM_PROMPT)  # 日付ありだけなら、従来と同じ指示
        mixed = codegen.build_messages(self._plan([
            {'view': 'v_ai_shipment', 'fields': ['id', 'shipment_date']}, {'view': PRODUCT, 'fields': ['id', 'product_code', 'unit_price']}]), False)
        self.assertEqual(mixed[0]['content'], codegen.SYSTEM_PROMPT + codegen.DATELESS_VIEW_RULE)
        payload = json.loads(mixed[1]['content'])
        product = next(item for item in payload['datasets'] if item['view'] == PRODUCT)
        self.assertEqual(product['columns'], [
            {'name': 'id', 'type': 'BIGINT'}, {'name': 'product_code', 'type': 'VARCHAR'}, {'name': 'unit_price', 'type': 'DECIMAL(18,2)'}])
