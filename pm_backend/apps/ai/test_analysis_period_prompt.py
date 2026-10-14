"""共通期間とビューごとの期間適用を区別する送信指示を検証する。実AIは呼ばない。"""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from ai.services import analysis_planning_service as planning
from ai.services.analysis_plan_store import AnalysisError


class AnalysisPeriodPromptTest(SimpleTestCase):
    def setUp(self):
        self.proposal = {
            'title': '工程照合', 'steps': ['同一ルーティングで親品と他工程の加工後品を照合する'],
            'outputs': ['すべての元工程と一致工程'],
            'datasets': [{'view': 'v_ai_routing_step', 'fields': ['id', 'routing_id', 'parent_product_code', 'output_product_code']}],
        }

    def test_all_providers_receive_same_period_rules_without_payload_changes(self):
        systems = []
        for provider in ('qwen', 'deepseek', 'openrouter', 'anthropic'):
            with self.subTest(provider=provider):
                store = MagicMock()
                store.create.side_effect = lambda owner, content, ttl, **kwargs: content
                raw = json.dumps(self.proposal, ensure_ascii=False)
                with (patch.object(planning, '_planning_input', return_value=('親品を照合', '2026-10-14', '2026-10-14', provider, 'test')),
                      patch.object(planning, '_external_purpose', side_effect=lambda purpose: purpose),
                      patch.object(planning, '_confirmation', return_value='confirmed'),
                      patch.object(planning, 'AnalysisPlanStore', return_value=store),
                      patch.object(planning, 'get_analysis_execution_policy', return_value=SimpleNamespace(plan_cache_ttl_minutes=60)),
                      patch.object(planning, 'get_qwen_analysis_timeout', return_value=90),
                      patch.object(planning.analysis_llm, 'get_analysis_temperature', return_value=0),
                      patch.object(planning.analysis_llm, 'request_external_json', return_value=raw) as external,
                      patch.object(planning.chat_service, '_chat', return_value=raw) as local):
                    result = planning.create_plan(1, {'external_confirmation': 'confirmed'})
                messages = local.call_args.args[0] if provider == 'qwen' else external.call_args.args[2]
                system = messages[0]['content']
                systems.append(system)
                for rule in (
                    'userのdate_from・date_toは分析案APIの共通項目',
                    'date_fieldの無いビューには、この共通期間を適用せず全行を使う',
                    '共通期間が送られていることだけを理由に、日付のないビューの分析をunsupportedにしない',
                    '目的文が、日付列のないビューを期間で絞ることを明示的に要求する場合は、期間を無視して別の分析にせずunsupportedを返す',
                    '日付のあるビューは、その日付列(date_field)をfieldsに必ず含める',
                ):
                    self.assertIn(rule, system)
                self.assertEqual(json.loads(messages[1]['content']), {
                    'purpose': '親品を照合', 'date_from': '2026-10-14', 'date_to': '2026-10-14',
                })
                self.assertEqual(result['conditions'], '全行（期間で絞らない。追加の絞り条件なし）')
                self.assertEqual(result['date_from'], '2026-10-14')
                self.assertEqual(result['date_to'], '2026-10-14')
                if provider == 'qwen':
                    external.assert_not_called()
                else:
                    local.assert_not_called()
        self.assertEqual(len(set(systems)), 1)

    def test_mixed_views_still_require_date_column_only_for_dated_view(self):
        dated = {'view': 'v_ai_shipment', 'fields': ['id', 'quantity', 'shipment_date']}
        proposal = {**self.proposal, 'datasets': [*self.proposal['datasets'], dated]}
        result = planning.validate_proposal(json.dumps(proposal), '照合と出荷', '2026-10-14', '2026-10-14')
        self.assertEqual(result['datasets'], proposal['datasets'])
        dated['fields'] = ['id', 'quantity']
        with self.assertRaises(AnalysisError):
            planning.validate_proposal(json.dumps(proposal), '照合と出荷', '2026-10-14', '2026-10-14')

    def test_unsupported_is_not_replaced_by_another_analysis(self):
        with self.assertRaises(AnalysisError):
            planning.validate_proposal('{"unsupported": "日付列がないため目的の期間で絞れない"}',
                                       '今日のルーティング工程だけを照合', '2026-10-14', '2026-10-14')
