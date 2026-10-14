"""目的から導く判定・列参照の共通指示と、送信データの範囲を検証する。実AIは呼ばない。"""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from ai.services import analysis_codegen_service as codegen
from ai.services import analysis_planning_service as planning
from ai.test_analysis_codegen import FakeRedactor


class RequirementPromptTest(SimpleTestCase):
    def test_planning_sends_derivation_rules_and_keeps_source_fields_separate(self):
        proposal = {
            'title': '照合', 'steps': ['同じルーティング内で親品を加工後品と照合し元行を残す'],
            'outputs': ['親品空欄・一致工程なし・一致ありの判定'],
            'datasets': [{'view': 'v_ai_routing_step', 'fields': ['routing_id', 'output_product_code', 'parent_product_code']}],
        }
        store = MagicMock()
        store.create.side_effect = lambda owner, content, ttl, **kwargs: content
        with (patch.object(planning, '_planning_input', return_value=('親品と加工後品を照合', '2026-10-11', '2026-10-11', 'qwen', 'test')),
                patch.object(planning, 'AnalysisPlanStore', return_value=store),
                patch.object(planning, 'get_analysis_execution_policy', return_value=SimpleNamespace(plan_cache_ttl_minutes=60)),
                patch.object(planning, 'get_qwen_analysis_timeout', return_value=90),
                patch.object(planning.analysis_llm, 'get_analysis_temperature', return_value=0),
                patch.object(planning.chat_service, '_chat', return_value=json.dumps(proposal, ensure_ascii=False)) as call):
            result = planning.create_plan(1, {})
        system = call.call_args.args[0][0]['content']
        for text in ('派生項目は含めてよい', '未確認の業務意味は推測しない', '全行保持・複数一致',
                     '表示で区別する状態には判定項目', '派生項目名はfieldsに入れない',
                     '元行と一致相手の全組を明細行として保持', '元側と相手側を区別',
                     '各側の識別ID(公開列にある場合)', '要求された列を具体的に列挙',
                     '照合件数の集計で要求明細を置き換えない'):
            self.assertIn(text, system)
        self.assertEqual(result['outputs'], proposal['outputs'])
        self.assertEqual(result['datasets'][0]['fields'], ['id', 'routing_id', 'output_product_code', 'parent_product_code'])

    def test_codegen_rules_are_sent_without_expanding_external_payload(self):
        plan = {'owner_id': 123, 'preview': {'total_rows': 999}, 'proposal': {
            'title': 'ＳＥＣＲＥＴ題名', 'purpose': 'ＳＥＣＲＥＴ目的', 'external_purpose': 'CODE-目的', 'steps': ['ＳＥＣＲＥＴ手順'],
            'outputs': ['ＳＥＣＲＥＴ出力'], 'date_from': '2026-10-11', 'date_to': '2026-10-11',
            'datasets': [{'view': 'v_ai_routing_step', 'fields': ['id', 'routing_id', 'output_product_code', 'parent_product_code']}],
        }}
        with patch.object(codegen, 'build_analysis_code_redactor', return_value=FakeRedactor()):
            messages = codegen.build_messages(plan, external=True)
        system = messages[0]['content']
        for text in ('最終表示まで反映', '投影後の列名だけ', 'ASで改名した元の列名',
                     '最終SELECTの列順', 'emit_tableの見出しと行の順', '未確認の業務意味は推測しない',
                     '識別ID(承認列にある場合)', '中間SQLから最終結果表まで保持',
                     '元の行と一致相手の全組を別行で表示',
                     '要求した明細をGROUP BY・COUNT・DISTINCT・代表1件の抽出で置き換えない',
                     '集計も求められた場合は、明細とは別の表で表示'):
            self.assertIn(text, system)
        payload = json.loads(messages[1]['content'])
        self.assertEqual(set(payload), {'purpose', 'steps', 'outputs', 'date_from', 'date_to', 'datasets'})
        self.assertEqual(payload['purpose'], 'CODE-目的')
        self.assertNotIn('ＳＥＣＲＥＴ', messages[1]['content'])
        self.assertEqual(set(payload['datasets'][0]), {'view', 'description', 'columns'})
        self.assertEqual([column['name'] for column in payload['datasets'][0]['columns']],
                         plan['proposal']['datasets'][0]['fields'])
        for column in payload['datasets'][0]['columns']:
            self.assertEqual(set(column), {'name', 'type'})
