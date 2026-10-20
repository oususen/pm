"""公開データの取得範囲とコンテナ内の分析条件の境界。実API・実DBは使わない。"""
import json
from contextlib import ExitStack
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from ai.services import analysis_consult_service as consult
from ai.services import analysis_planning_service as planning
from ai.services.analysis_data_service import build_where
from ai.services.analysis_plan_store import AnalysisError


PURPOSE = '一般工程の生産実績を連産品は代表品のみ、品番ST始まりを除外して工程別に集計する'
PROPOSAL = {
    'title': '工程別生産数',
    'steps': ['公開BOMを子品番で代表品判定用に集約し、生産実績に結合して代表品以外とST始まりを除外し集計する'],
    'outputs': ['工程別生産数量'],
    'datasets': [
        {'view': 'v_ai_process_production_actual', 'fields': ['id', 'business_day', 'process_id', 'product_code', 'product_name', 'qty']},
        {'view': 'v_ai_bom_item', 'fields': ['id', 'child_product_code', 'bom_is_coproduct', 'is_coproduct_driver']},
    ],
}


class AnalysisScopePromptTest(SimpleTestCase):
    def assert_scope_rules(self, system):
        self.assertIn('未公開の元テーブル・結合先・列', system)
        self.assertIn('説明にない業務上の意味を推測しない', system)
        self.assertIn('日付のあるビューは指定期間の全登録行', system)
        self.assertIn('取得後の分析用コンテナ内では、公開列による絞り込み・品番の除外・公開ビュー同士の結合・集計ができる', system)
        self.assertIn('適用目的が限定された規則は、その目的に該当する場合だけ適用し、別目的の必須条件へ広げない', system)
        self.assertIn('実データや計算結果を事前に知らないだけで分析不可にしない', system)
        self.assertNotIn('生産・仕損・中断・追加資料は利用できない', system)
        self.assertNotIn('追加の絞り条件が必要', system)
        self.assertNotIn('元テーブル、結合先の参照', system)

    def test_consult_all_providers_share_scope_and_keep_user_payload(self):
        systems = []
        messages = [{'role': 'user', 'content': PURPOSE}]
        raw = json.dumps({'reply': '分析の目的文を整えます', 'draft_purpose': PURPOSE,
                          'date_from': '2026-09-01', 'date_to': '2026-09-30', 'template_ids': []})
        for provider in ('qwen', 'deepseek', 'openrouter', 'anthropic'):
            with self.subTest(provider=provider), ExitStack() as stack:
                redactor = SimpleNamespace(redact_text=lambda text, **kwargs: text)
                for name, value in (
                    ('resolve_planning_provider', (provider, 'test')),
                    ('_approved_templates', []), ('_redactor', redactor), ('get_qwen_analysis_timeout', 90),
                ):
                    stack.enter_context(patch.object(consult, name, return_value=value))
                external = stack.enter_context(patch.object(consult.analysis_llm, 'request_external_json', return_value=raw))
                local = stack.enter_context(patch.object(consult.chat_service, '_chat', return_value=raw))
                result = consult.consult({'messages': messages, 'external_confirmed': True})
                sent = local.call_args.args[0] if provider == 'qwen' else external.call_args.args[2]
                systems.append(sent[0]['content'])
                self.assert_scope_rules(sent[0]['content'])
                self.assertIn('数値・結果・SQL・Pythonは作らない', sent[0]['content'])
                self.assertIn('後続の分析で計算する目的文として整える', sent[0]['content'])
                self.assertIn('集計・標準偏差・最大最小差などを求められたら、公開列から後続の分析で算出する目的文を整える', sent[0]['content'])
                self.assertEqual(sent[1:], messages)
                self.assertEqual(result['draft']['purpose'], PURPOSE)
                self.assertEqual((local.call_count, external.call_count), (1, 0) if provider == 'qwen' else (0, 1))
        self.assertEqual(len(set(systems)), 1)

    def test_planning_all_providers_share_scope_and_accept_mixed_public_views(self):
        systems = []
        for provider in ('qwen', 'deepseek', 'openrouter', 'anthropic'):
            with self.subTest(provider=provider), ExitStack() as stack:
                store = MagicMock()
                store.create.side_effect = lambda owner, content, ttl, **kwargs: content
                values = {
                    '_planning_input': (PURPOSE, '2026-09-01', '2026-09-30', provider, 'test'),
                    '_confirmation': 'confirmed', 'AnalysisPlanStore': store,
                    'get_analysis_execution_policy': SimpleNamespace(plan_cache_ttl_minutes=60),
                    'get_qwen_analysis_timeout': 90,
                }
                for name, value in values.items():
                    stack.enter_context(patch.object(planning, name, return_value=value))
                stack.enter_context(patch.object(planning, '_external_purpose', side_effect=lambda purpose: purpose))
                stack.enter_context(patch.object(planning.analysis_llm, 'get_analysis_temperature', return_value=0))
                raw = json.dumps(PROPOSAL)
                external = stack.enter_context(patch.object(planning.analysis_llm, 'request_external_json', return_value=raw))
                local = stack.enter_context(patch.object(planning.chat_service, '_chat', return_value=raw))
                result = planning.create_plan(1, {'external_confirmation': 'confirmed'})
                sent = local.call_args.args[0] if provider == 'qwen' else external.call_args.args[2]
                systems.append(sent[0]['content'])
                self.assert_scope_rules(sent[0]['content'])
                self.assertIn('必要な公開列と結合キーをdatasetsのfieldsに含め', sent[0]['content'])
                self.assertIn('集計・標準偏差・最大最小差などは公開列から算出する手順を計画する', sent[0]['content'])
                self.assertEqual(json.loads(sent[1]['content']), {
                    'purpose': PURPOSE, 'date_from': '2026-09-01', 'date_to': '2026-09-30',
                })
                self.assertEqual(result['datasets'], PROPOSAL['datasets'])
                self.assertEqual(result['steps'], PROPOSAL['steps'])
                self.assertIn('追加の絞り条件なし', result['conditions'])
                self.assertEqual((local.call_count, external.call_count), (1, 0) if provider == 'qwen' else (0, 1))
        self.assertEqual(len(set(systems)), 1)

    def test_missing_date_unknown_or_duplicate_data_and_unsupported_still_rejected(self):
        cases = []
        for change in ('missing_date', 'unknown_view', 'unknown_field', 'duplicate_view', 'duplicate_field'):
            proposal = deepcopy(PROPOSAL)
            dataset = proposal['datasets'][0]
            if change == 'missing_date':
                dataset['fields'].remove('business_day')
            elif change == 'unknown_view':
                dataset['view'] = 't_process_realtime_record'
            elif change == 'unknown_field':
                dataset['fields'].append('unpublished_column')
            elif change == 'duplicate_view':
                proposal['datasets'].append(deepcopy(dataset))
            else:
                dataset['fields'].append('qty')
            cases.append(proposal)
        for proposal in [*cases, {'unsupported': '未公開の情報が必要'}]:
            with self.subTest(proposal=proposal), self.assertRaises(AnalysisError) as caught:
                planning.validate_proposal(json.dumps(proposal), PURPOSE, '2026-09-01', '2026-09-30')
            self.assertEqual(caught.exception.status_code, 502)

    def test_database_where_keeps_only_period_and_id_paging(self):
        self.assertEqual(build_where('v_ai_process_production_actual', '2026-09-01', '2026-09-30', 5), (
            ' WHERE `business_day` >= %s AND `business_day` <= %s AND `id` > %s', ['2026-09-01', '2026-09-30', 5],
        ))
        self.assertEqual(build_where('v_ai_bom_item', '2026-09-01', '2026-09-30'), ('', []))
        self.assertEqual(build_where('v_ai_bom_item', '2026-09-01', '2026-09-30', 5), (' WHERE `id` > %s', [5]))
