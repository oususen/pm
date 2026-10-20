"""自動修正の同意・回数・候補隔離。AI・実データは模擬する。"""
import json
from unittest.mock import patch
from ai.services import analysis_codegen_service as cg
from ai.services import analysis_template_reference_service as reference
from ai.services.analysis_plan_store import AnalysisError, public_plan
from ai.test_analysis_codegen import CodegenBase, GOOD_RESPONSE, OWNER, FakeRedactor

class AutoRepairTest(CodegenBase):
    def setUp(self):
        super().setUp()
        for item in (patch.object(cg.analysis_llm, 'get_analysis_temperature', return_value=0.3),
                     patch.object(reference, 'build_analysis_code_redactor', return_value=FakeRedactor())):
            item.start()
            self.addCleanup(item.stop)

    def initial(self, auto=True, reason=cg.REPAIR_REASON):
        plan = self.new_plan()
        preview = cg.preview(OWNER, plan['id'], plan['revision'], auto)
        with patch.object(cg, '_call_ai', return_value=GOOD_RESPONSE), patch.object(cg, '_validate_generated_sql', return_value=[reason]):
            return cg.generate(OWNER, plan['id'], plan['revision'], preview['confirmation'], auto)

    def repair(self, plan, reasons=()):
        with patch.object(cg, '_call_ai', return_value=GOOD_RESPONSE) as call, patch.object(cg, '_validate_generated_sql', return_value=list(reasons)):
            result = cg.generate(OWNER, plan['id'], plan['revision'], auto_repair=True, repair_token=cg.describe_codegen(plan)['repair_token'])
        return result, call

    def test_consent_distinct_from_single_send(self):
        plan = self.new_plan()
        normal = cg.preview(OWNER, plan['id'], plan['revision'])['confirmation']
        self.assertNotEqual(normal, cg.preview(OWNER, plan['id'], plan['revision'], True)['confirmation'])
        with patch.object(cg, '_call_ai') as call, self.assertRaises(AnalysisError):
            cg.generate(OWNER, plan['id'], plan['revision'], normal, True)
        call.assert_not_called()

    def test_hidden_candidate_repair_and_ttl(self):
        failed = self.initial()
        ttl = self.store.client.ttl(self.store._key(failed['id']))
        self.assertIn('_repair_candidate', failed['codegen'])
        self.assertNotIn('_repair_candidate', public_plan(failed)['codegen'])
        self.assertNotIn('_repair_authorization', public_plan(failed)['codegen'])
        self.assertNotIn('steps', failed['codegen'])
        result, call = self.repair(failed)
        self.assertEqual(result['codegen']['status'], 'generated')
        self.assertEqual(result['codegen']['attempts'], 2)
        self.assertIsNone(result['codegen']['trial'])
        self.assertNotIn('_repair_candidate', result['codegen'])
        self.assertLessEqual(self.store.client.ttl(self.store._key(failed['id'])), ttl)
        payload = json.loads(call.call_args.args[2][1]['content'])
        self.assertEqual(payload['repair_candidate']['parameters'], [])
        self.assertEqual(payload['repair_candidate']['reason'], cg.REPAIR_REASON)
        self.assertNotIn('2724', json.dumps(payload))

    def test_only_consented_target_retains_candidate(self):
        for auto, reason in [(False, cg.REPAIR_REASON), (True, 'sql_validation_failed'), (True, 'ai_request_failed')]:
            plan = self.initial(auto, reason)
            self.assertIsNone(cg.describe_codegen(plan)['repair_token'])
            self.assertNotIn('_repair_candidate', plan['codegen'])

    def test_four_total_and_stale_token(self):
        plan = self.initial()
        stale, rev = cg.describe_codegen(plan)['repair_token'], plan['revision']
        plan, _ = self.repair(plan, [cg.REPAIR_REASON])
        with patch.object(cg, '_call_ai') as call, self.assertRaises(AnalysisError):
            cg.generate(OWNER, plan['id'], rev, auto_repair=True, repair_token=stale)
        call.assert_not_called()
        plan, _ = self.repair(plan, [cg.REPAIR_REASON])
        plan, _ = self.repair(plan, [cg.REPAIR_REASON])
        self.assertEqual(plan['codegen']['attempts'], 4)
        self.assertIsNone(cg.describe_codegen(plan)['repair_token'])
        self.assertNotIn('_repair_candidate', plan['codegen'])

    def test_bad_token_redaction_failure_stop_before_send(self):
        plan = self.initial()
        for token, fail in [('tampered', False), (cg.describe_codegen(plan)['repair_token'], True)]:
            with patch.object(reference, 'redact_code_payload', side_effect=AnalysisError('置換不可')) if fail else patch.object(cg, 'REPAIR_RULE', cg.REPAIR_RULE):
                with patch.object(cg, '_call_ai') as call, self.assertRaises(AnalysisError):
                    cg.generate(OWNER, plan['id'], plan['revision'], auto_repair=True, repair_token=token)
                call.assert_not_called()
        self.assertEqual(self.current(plan)['codegen']['attempts'], 1)

    def test_communication_failure_drops_candidate(self):
        plan = self.initial()
        with patch.object(cg, '_call_ai', side_effect=cg.chat_service.LocalAIError('SECRET')):
            result = cg.generate(OWNER, plan['id'], plan['revision'], auto_repair=True, repair_token=cg.describe_codegen(plan)['repair_token'])
        self.assertEqual(result['codegen']['attempts'], 2)
        self.assertIsNone(cg.describe_codegen(result)['repair_token'])
        self.assertNotIn('SECRET', json.dumps(result))

    def test_parameter_source_is_sent_without_substitution(self):
        plan = self.initial()
        source = {'steps': [{'name': 'w_daily', 'query': 'SELECT shipment_date, quantity FROM v_ai_shipment WHERE shipment_date >= {{period_from}}'}],
                  'python': 'rows = con.sql("SELECT shipment_date, quantity FROM w_daily").fetchall()\nfor a, b, c in rows:\n    emit_report(str(a))',
                  'parameters': [{'name': 'period_from', 'type': 'date', 'label': '開始日', 'default': '2026-01-01'}]}
        def change(current):
            current['codegen']['_repair_candidate'] = source
            current['codegen']['_repair_authorization']['candidate_sha256'] = cg._repair_digest(source)
        plan = self.store.update(plan['id'], OWNER, plan['revision'], change)
        result, call = self.repair(plan)
        sent = json.loads(call.call_args.args[2][1]['content'])['repair_candidate']
        self.assertIn('{{period_from}}', sent['sql_steps'][0]['query'])
        self.assertNotIn("'2026-01-01'", sent['sql_steps'][0]['query'])
        self.assertEqual(sent['parameters'], source['parameters'])

    def test_candidate_provider_and_owner_tokens_cannot_be_reused(self):
        for field in ['candidate', 'provider']:
            plan = self.initial()
            old = cg.describe_codegen(plan)['repair_token']
            def change(current):
                if field == 'candidate':
                    current['codegen']['_repair_candidate']['python'] += '\nemit_report("changed")'
                else:
                    current['proposal']['provider'] = 'anthropic'
            changed = self.store.update(plan['id'], OWNER, plan['revision'], change)
            with patch.object(cg, '_call_ai') as call, self.assertRaises(AnalysisError):
                cg.generate(OWNER, changed['id'], changed['revision'], auto_repair=True, repair_token=old)
            call.assert_not_called()
        plan = self.initial()
        with patch.object(cg, '_call_ai') as call, self.assertRaises(AnalysisError):
            cg.generate(OWNER + 1, plan['id'], plan['revision'], auto_repair=True, repair_token=cg.describe_codegen(plan)['repair_token'])
        call.assert_not_called()

    def test_expired_or_disabled_stops_before_send(self):
        plan = self.initial()
        token = cg.describe_codegen(plan)['repair_token']
        with patch.object(cg, 'resolve_planning_provider', side_effect=AnalysisError('設定無効')), patch.object(cg, '_call_ai') as call, self.assertRaises(AnalysisError):
            cg.generate(OWNER, plan['id'], plan['revision'], auto_repair=True, repair_token=token)
        call.assert_not_called()
        self.store.client.delete(self.store._key(plan['id']))
        with patch.object(cg, '_call_ai') as call, self.assertRaises(AnalysisError):
            cg.generate(OWNER, plan['id'], plan['revision'], auto_repair=True, repair_token=token)
        call.assert_not_called()

    def test_failed_candidate_cannot_be_trialled_approved_or_bundled(self):
        plan = self.initial()
        for operation in [lambda: cg.run_trial(OWNER, plan['id'], plan['revision']),
                          lambda: cg.approve_code(OWNER, plan['id'], plan['revision'], 'not-approved')]:
            with self.assertRaises(AnalysisError):
                operation()
        with self.assertRaises(AnalysisError):
            cg.bundle_from_plan(plan)

    def test_inflight_duplicate_and_released_response_do_not_adopt(self):
        plan = self.initial()
        token = cg.describe_codegen(plan)['repair_token']
        def delayed(*args):
            with self.assertRaises(AnalysisError):
                cg.generate(OWNER, plan['id'], plan['revision'], auto_repair=True, repair_token=token)
            current = self.current(plan)
            def release(value):
                value['codegen'].update(status='failed', inflight=None, reasons=['inflight_released'])
            self.store.update(current['id'], OWNER, current['revision'], release)
            return GOOD_RESPONSE
        with patch.object(cg, '_call_ai', side_effect=delayed) as call, self.assertRaises(AnalysisError):
            cg.generate(OWNER, plan['id'], plan['revision'], auto_repair=True, repair_token=token)
        call.assert_called_once()
        state = self.current(plan)
        self.assertEqual(state['codegen']['attempts'], 2)
        self.assertEqual(state['codegen']['reasons'], ['inflight_released'])
        self.assertNotIn('_repair_candidate', state['codegen'])
