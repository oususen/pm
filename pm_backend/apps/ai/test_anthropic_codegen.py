"""Claudeの構造化コード生成。外部APIは模擬し、既存の生成・確認・変数・SQL検査の経路を確認する。"""
import json
from urllib.error import HTTPError
from unittest.mock import patch

from ai.services import analysis_codegen_service as cg, chat_service
from ai.services.analysis_plan_store import AnalysisError
from ai.test_analysis_codegen import CodegenBase, GOOD_RESPONSE, GOOD_STEPS, GOOD_PYTHON, OWNER
from ai.test_anthropic_direct import DUMMY_KEY, claude_response


class AnthropicCodegenTests(CodegenBase):
    def setUp(self):
        super().setUp()
        for item in (
            patch.dict(chat_service.EXTERNAL_AGENT_PROVIDERS['anthropic'], {'api_key': DUMMY_KEY}),
            patch.object(cg.analysis_llm, 'get_analysis_temperature', return_value=0.3),
        ):
            item.start()
            self.addCleanup(item.stop)

    def run_response(self, raw=GOOD_RESPONSE, error=None):
        plan = self.new_plan(provider='anthropic', model='claude-haiku-5-5')
        confirmation = self.confirmation_for(plan)
        with patch('ai.services.anthropic_client.urlopen', return_value=claude_response(raw), side_effect=error) as api, \
                patch('ai.services.analysis_llm.urlopen') as other:
            result = cg.generate(OWNER, plan['id'], plan['revision'], confirmation)
        api.assert_called_once()
        other.assert_not_called()
        self.assertEqual(self.current(plan)['codegen']['attempts'], 1)
        self.assertIsNone(self.current(plan)['codegen']['inflight'])
        return result['codegen'], plan, api

    def test_no_parameters_schema_and_existing_sql_validation(self):
        with patch.object(cg, '_validate_generated_sql', return_value=[]) as sql:
            result, plan, api = self.run_response()
        self.assertEqual(result['status'], 'generated')
        sql.assert_called_once()
        state = self.current(plan)['codegen']
        self.assertIsNone(state['trial'])  # 生成成功でも手動試行・利用者承認を省略しない
        self.assertIsNone(state.get('approved_at'))
        body = json.loads(api.call_args.args[0].data)
        self.assertEqual(body['output_config']['format']['schema'], cg.ANTHROPIC_CODEGEN_SCHEMA)
        self.assertEqual(body['thinking'], {'type': 'disabled'})
        self.assertEqual(body['max_tokens'], chat_service.AGENT_MAX_TOKENS)
        for key in ('temperature', 'top_p', 'top_k'):
            self.assertNotIn(key, body)
        self.assertEqual(api.call_args.kwargs['timeout'], 90)

    def test_parameters_use_the_existing_normalization(self):
        steps = [{'name': 'w_daily', 'query': 'SELECT shipment_date, SUM(quantity) AS q FROM v_ai_shipment WHERE shipment_date BETWEEN {{period_from}} AND {{period_to}} GROUP BY shipment_date'}]
        parameters = [{'name': name, 'type': 'date', 'label': name} for name in ('period_from', 'period_to')]
        result, plan, _ = self.run_response(json.dumps({'steps': steps, 'python': GOOD_PYTHON, 'parameters': parameters}))
        self.assertEqual(result['status'], 'generated')
        state = self.current(plan)['codegen']
        self.assertEqual(len(state['template_source']['parameters']), 2)
        self.assertNotIn('{{', state['steps'][0]['query'])

    def test_unsupported_is_not_saved_as_generated(self):
        with patch.object(cg, '_validate_generated_sql') as sql:
            result, _, _ = self.run_response('{"unsupported":"synthetic unsupported"}')
        self.assertEqual(result['status'], 'failed')
        self.assertIn('ai_unsupported', result['reasons'])
        sql.assert_not_called()

    def test_malformed_and_extra_keys_still_fail(self):
        for raw in ('bad json', json.dumps({'steps': GOOD_STEPS, 'python': GOOD_PYTHON, 'extra': 1}),
                    json.dumps({'steps': GOOD_STEPS, 'python': GOOD_PYTHON, 'parameters': []})):
            with self.subTest(raw=raw):
                result, _, _ = self.run_response(raw)
                self.assertEqual(result['status'], 'failed')
                self.assertIn('response_invalid', result['reasons'])

    def test_http_error_has_no_retry_or_payload_in_history(self):
        error = HTTPError('https://api.anthropic.com/v1/messages', 400, 'SECRET', {}, None)
        result, plan, _ = self.run_response(error=error)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reasons'], ['ai_http'])
        history = json.dumps(self.current(plan)['codegen']['history'])
        self.assertNotIn('SECRET', history)
        self.assertNotIn(DUMMY_KEY, history)

    def test_sql_rejection_prevents_generated_status(self):
        with patch.object(cg, '_validate_generated_sql', return_value=['sql_validation_failed']):
            result, _, _ = self.run_response()
        self.assertEqual(result['status'], 'failed')
        self.assertIn('sql_validation_failed', result['reasons'])

    def test_unconfirmed_external_send_never_calls_api(self):
        plan = self.new_plan(provider='anthropic', model='claude-haiku-5-5')
        with patch('ai.services.anthropic_client.urlopen') as api, self.assertRaises(AnalysisError):
            cg.generate(OWNER, plan['id'], plan['revision'], 'wrong')
        api.assert_not_called()
        self.assertNotIn('codegen', self.current(plan))

    def test_other_external_providers_keep_the_same_call_signature(self):
        for provider in ('openrouter', 'deepseek'):
            with self.subTest(provider=provider), patch.object(cg.analysis_llm, 'request_external_json', return_value='{}') as api:
                cg._call_ai(provider, 'model', [{'role': 'user', 'content': 'x'}], 0.4)
                api.assert_called_once_with(provider, 'model', [{'role': 'user', 'content': 'x'}], 0.4)
