"""分析案の固定失敗診断と、応答本文を残さないことを検証する。"""
import json
import logging
from copy import deepcopy
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.views import exception_handler

from ai.services import analysis_planning_service as planning
from ai.services.analysis_data_service import validate_datasets
from ai.services.analysis_plan_store import AnalysisError


PERIOD = ('2026-10-14', '2026-10-14')
SECRET = 'NONPUBLIC_SENTINEL_73451'
GOOD = {
    'title': '工程照合', 'steps': ['同じルーティング内で自己結合する'], 'outputs': ['すべての一致'],
    'datasets': [{'view': 'v_ai_routing_step', 'fields': ['routing_id', 'parent_product_code', 'output_product_code']}],
}


class AnalysisPlanningReasonsTest(SimpleTestCase):
    def assert_rejected(self, raw, reason):
        with self.assertRaises(AnalysisError) as caught:
            planning.validate_proposal(raw, '目的', *PERIOD)
        error = caught.exception
        self.assertEqual(error.status_code, 502)
        self.assertEqual(error.reason, reason)
        self.assertEqual(str(error.detail['reason']), reason)
        response = exception_handler(error, {})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.data, error.detail)
        self.assertNotIn(SECRET, str(error.detail))
        self.assertIsNone(error.__cause__)
        self.assertTrue(error.__suppress_context__)
        return error

    def test_proposal_structure_reasons(self):
        cases = [(SECRET, 'proposal_json_invalid'), (None, 'proposal_json_invalid'),
                 ('[]', 'proposal_keys_invalid'), ('{}', 'proposal_keys_invalid'),
                 (json.dumps({'unsupported': SECRET}), 'proposal_unsupported')]
        for field, values in [('title', [None, '', []]), ('steps', [[], '', [SECRET, None]]),
                              ('outputs', [[], '', [SECRET, None]])]:
            for value in values:
                cases.append((json.dumps({**GOOD, field: value}), f'proposal_{field}_invalid'))
        cases.append((json.dumps({**GOOD, SECRET: SECRET}), 'proposal_keys_invalid'))
        for raw, reason in cases:
            with self.subTest(reason=reason, raw_type=type(raw).__name__):
                self.assert_rejected(raw, reason)

    def test_dataset_reasons_and_legacy_compatibility(self):
        view = 'v_ai_routing_step'
        dataset = {'view': view, 'fields': ['routing_id']}
        cases = [
            ([], 'datasets_missing', '利用ビューが指定されていません。'),
            (None, 'datasets_missing', '利用ビューが指定されていません。'),
            ([{SECRET: SECRET}], 'dataset_invalid', '利用ビュー・フィールドの指定が不正です。'),
            ([{'view': SECRET, 'fields': ['id']}], 'view_unknown', '未公開または重複したビューは分析できません。'),
            ([{'view': [], 'fields': ['id']}], 'view_unknown', '未公開または重複したビューは分析できません。'),
            ([dataset, dataset], 'view_duplicate', '未公開または重複したビューは分析できません。'),
            ([{'view': view, 'fields': []}], 'fields_invalid', '未公開または重複したフィールドは分析できません。'),
            ([{'view': view, 'fields': SECRET}], 'fields_invalid', '未公開または重複したフィールドは分析できません。'),
            ([{'view': view, 'fields': [SECRET]}], 'field_unknown', '未公開または重複したフィールドは分析できません。'),
            ([{'view': view, 'fields': [[]]}], 'field_unknown', '未公開または重複したフィールドは分析できません。'),
            ([{'view': view, 'fields': ['id', 'id']}], 'field_duplicate', '未公開または重複したフィールドは分析できません。'),
            ([{'view': 'v_ai_shipment', 'fields': ['id']}], 'date_field_missing', '対象期間の根拠となる日付フィールドが必要です。'),
        ]
        for datasets, reason, legacy_detail in cases:
            with self.subTest(reason=reason):
                self.assert_rejected(json.dumps({**GOOD, 'datasets': datasets}), reason)
                # 既存の承認・取得などはreasonなしの従来応答のまま。
                with self.assertRaises(AnalysisError) as caught:
                    validate_datasets(datasets, *PERIOD)
                self.assertEqual(caught.exception.status_code, 400)
                self.assertEqual(str(caught.exception.detail), legacy_detail)
                self.assertFalse(hasattr(caught.exception, 'reason'))
                with self.assertRaises(AnalysisError) as diagnosed:
                    validate_datasets(datasets, *PERIOD, include_reason=True)
                self.assertEqual(diagnosed.exception.status_code, 400)
                self.assertEqual(diagnosed.exception.reason, reason)

    def test_valid_proposal_and_management_columns_unchanged(self):
        original = deepcopy(GOOD)
        result = planning.validate_proposal(json.dumps(GOOD), '目的', *PERIOD)
        self.assertEqual(GOOD, original)
        self.assertEqual(result['datasets'][0]['fields'], ['id', *GOOD['datasets'][0]['fields']])
        self.assertEqual(result['steps'], GOOD['steps'])
        self.assertEqual(result['outputs'], GOOD['outputs'])
        self.assertEqual(result['purpose'], '目的')
        self.assertEqual(result['date_from'], PERIOD[0])
        self.assertEqual(result['materials'], [])
        self.assertEqual(validate_datasets(GOOD['datasets'], *PERIOD), GOOD['datasets'])
        self.assertEqual(validate_datasets(GOOD['datasets'], *PERIOD, include_reason=True), GOOD['datasets'])

    def test_failed_generation_not_saved_retried_or_logged(self):
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        logger = logging.getLogger()
        logger.addHandler(handler)
        self.addCleanup(logger.removeHandler, handler)
        with patch.object(planning, 'AnalysisPlanStore') as store_class, \
                patch.object(planning, 'resolve_planning_provider', return_value=('qwen', 'test-model')), \
                patch.object(planning, 'get_analysis_execution_policy', return_value=SimpleNamespace(plan_cache_ttl_minutes=60)), \
                patch.object(planning.analysis_llm, 'get_analysis_temperature', return_value=0), \
                patch.object(planning, 'get_qwen_analysis_timeout', return_value=90), \
                patch.object(planning.chat_service, '_chat', return_value=json.dumps({'unsupported': SECRET})) as request:
            with self.assertRaises(AnalysisError) as caught:
                planning.create_plan(3, {'purpose': '目的', 'date_from': PERIOD[0], 'date_to': PERIOD[1]})
            self.assertEqual(caught.exception.reason, 'proposal_unsupported')
            request.assert_called_once()
            store_class.return_value.check_connection.assert_called_once()
            store_class.return_value.create.assert_not_called()
            store_class.return_value.update.assert_not_called()
            self.assertNotIn(SECRET, str(caught.exception.detail))
        self.assertNotIn(SECRET, stream.getvalue())

    def test_external_failure_not_saved_or_retried(self):
        # 社外AIの正規呼出しも、一回の返答を診断するだけ。確認済み目的の送信を維持する。
        with patch.object(planning, 'AnalysisPlanStore') as store_class, \
                patch.object(planning, 'resolve_planning_provider', return_value=('anthropic', 'test-model')), \
                patch.object(planning, '_external_purpose', return_value='置換後の目的'), \
                patch.object(planning, 'get_analysis_execution_policy', return_value=SimpleNamespace(plan_cache_ttl_minutes=60)), \
                patch.object(planning.analysis_llm, 'get_analysis_temperature', return_value=1), \
                patch.object(planning.analysis_llm, 'request_external_json', return_value=json.dumps({'unsupported': SECRET})) as request:
            confirmation = planning._confirmation(3, '目的', *PERIOD, 'anthropic', 'test-model', '置換後の目的')
            with self.assertRaises(AnalysisError) as caught:
                planning.create_plan(3, {'purpose': '目的', 'date_from': PERIOD[0], 'date_to': PERIOD[1],
                                         'external_confirmation': confirmation})
            self.assertEqual(caught.exception.reason, 'proposal_unsupported')
            request.assert_called_once()
            self.assertEqual(request.call_args.kwargs['json_schema'], planning.ANTHROPIC_PLAN_SCHEMA)
            self.assertNotIn(SECRET, str(caught.exception.detail))
            store_class.return_value.create.assert_not_called()
            store_class.return_value.update.assert_not_called()
