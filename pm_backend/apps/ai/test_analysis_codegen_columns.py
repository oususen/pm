"""生成時の承認列・投影列検査。AI・実DBは呼ばず、隔離実行の送受信と採否を確認する。"""
import json
import os
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
from django.test import override_settings

from ai.services import analysis_codegen_service as cg
from ai.services.analysis_plan_store import AnalysisError
from ai.test_analysis_codegen import CodegenBase, GOOD_PYTHON, OWNER, POLICY
from ai.test_analysis_execution import split_frames

VALIDATE_SQL = cg._validate_generated_sql
ROUTING_FIELDS = ['id', 'routing_code', 'routing_product_code', 'step_no', 'process_name', 'output_product_code', 'parent_product_code']


def setUpModule():
    global _temperature_patch
    _temperature_patch = patch.object(cg.analysis_llm, 'get_analysis_temperature', return_value=0.3)
    _temperature_patch.start()


def tearDownModule():
    _temperature_patch.stop()


class GenerationColumnsTest(CodegenBase):
    def setUp(self):
        super().setUp()
        item = patch.object(cg, '_validate_generated_sql', VALIDATE_SQL)
        item.start()
        self.addCleanup(item.stop)
        self.sent = []
        self.reply = {'status': 'ok', 'result': {'report': json.dumps({'trial': 'passed', 'steps': 1})}}
        for item in (patch.object(cg, 'launcher_endpoint', return_value=('127.0.0.1', 1)),
                     patch.object(cg, '_transmit', side_effect=self.transmit)):
            item.start()
            self.addCleanup(item.stop)

    def transmit(self, host, port, length, frames, deadline, timeout):
        body = b''.join(frames)
        self.assertEqual(len(body), length)
        self.sent.append(split_frames(body))
        return 200, self.reply

    def test_success_sends_only_approved_schema_then_requires_separate_trial(self):
        plan = self.new_plan()
        result, call = self.generate(plan)
        call.assert_called_once()
        self.assertEqual(result['codegen']['status'], 'generated')
        self.assertIsNone(result['codegen']['trial'])
        self.assertEqual([kind for kind, _ in self.sent[0]], [b'H', b'E'])
        header = json.loads(self.sent[0][0][1])
        for dataset, view in zip(plan['proposal']['datasets'], header['views']):
            self.assertEqual([column['name'] for column in view['columns']], dataset['fields'])
            self.assertEqual(view['expected_rows'], 0)
        self.assertIn('"mode": "trial"', header['code'])
        with self.assertRaises(AnalysisError):
            cg.approve_code(OWNER, result['id'], result['revision'], result['codegen']['executed_code_sha256'])

    def test_failures_do_not_save_code_or_raw_diagnostics_and_clear_inflight(self):
        cases = [
            ({'status': 'ok', 'result': {'report': json.dumps({'trial': 'failed', 'reason': 'query_failed',
              'message': 'SECRET SQL SELECT m.id', 'step': 'w_secret'})}}, 'sql_validation_failed'),
            ({'status': 'refused', 'reason': 'busy'}, 'sql_validation_busy'),
            ({'status': 'refused', 'reason': 'launcher_disabled'}, 'sql_validation_unavailable'),
            ({'status': 'ok', 'result': {'report': '[]'}}, 'sql_validation_report_invalid'),
            ({'status': 'ok', 'result': {'report': '{"trial":"passed"}'}}, 'sql_validation_report_invalid'),
            ([], 'sql_validation_report_invalid'),
        ]
        for reply, expected in cases:
            with self.subTest(expected=expected, reply=reply):
                self.reply = reply
                plan = self.new_plan()
                result, call = self.generate(plan)
                call.assert_called_once()
                state = result['codegen']
                self.assertEqual((state['status'], state['attempts'], state['inflight']), ('failed', 1, None))
                self.assertEqual(state['reasons'], [expected])
                self.assertNotIn('steps', state)
                self.assertNotIn('trial', state)
                self.assertNotIn('SECRET', json.dumps(state))
                self.assertNotIn('w_secret', json.dumps(state))

    def test_normal_configuration_and_launcher_exceptions_finish_as_failure(self):
        for target in ('get_analysis_execution_policy', '_trial_sql'):
            with self.subTest(target=target), patch.object(cg, target, side_effect=RuntimeError('SECRET')):
                result, _ = self.generate(self.new_plan())
                self.assertEqual(result['codegen']['reasons'], ['sql_validation_unavailable'])
                self.assertIsNone(result['codegen']['inflight'])

    def test_validation_phase_uses_existing_launcher_wait_not_ai_timeout(self):
        plan = self.new_plan()
        def respond(*args):
            current = self.current(plan)
            inflight = current['codegen']['inflight']
            self.assertEqual(inflight['phase'], 'sql_validation')
            started = datetime.fromisoformat(inflight['phase_started_at'])
            seconds = cg._trial_wait_seconds(POLICY)
            self.assertEqual(cg.describe_codegen(current, started + timedelta(seconds=seconds - 1))['inflight_state'], 'running')
            self.assertEqual(cg.describe_codegen(current, started + timedelta(seconds=seconds + 1))['inflight_state'], 'unknown')
            return {'status': 'passed'}
        with patch.object(cg, '_trial_sql', side_effect=respond):
            result, _ = self.generate(plan)
        self.assertEqual(result['codegen']['status'], 'generated')

    def test_late_validation_result_after_release_is_discarded(self):
        plan = self.new_plan()
        def respond(*args):
            current = self.current(plan)
            def release(value):
                value['codegen'].update(status='failed', inflight=None, reasons=['inflight_released'])
            self.store.update(current['id'], OWNER, current['revision'], release)
            return {'status': 'passed'}
        with patch.object(cg, '_trial_sql', side_effect=respond), self.assertRaises(AnalysisError):
            self.generate(plan)
        self.assertEqual(self.current(plan)['codegen']['reasons'], ['inflight_released'])


@unittest.skipUnless(os.environ.get('AI_ANALYSIS_LAUNCHER_URL_FOR_TEST'), '実launcherの接続先指定時だけ実DuckDBを確認する')
class RealGenerationColumnsTest(CodegenBase):
    """承認列・CTE改名・中間投影を、実際の隔離DuckDBで生成採否まで確認する。"""
    def setUp(self):
        super().setUp()
        for item in (patch.object(cg, '_validate_generated_sql', VALIDATE_SQL),
                     override_settings(AI_ANALYSIS_LAUNCHER_URL=os.environ['AI_ANALYSIS_LAUNCHER_URL_FOR_TEST'])):
            item.enable() if hasattr(item, 'enable') else item.start()
            self.addCleanup(item.disable if hasattr(item, 'disable') else item.stop)

    def routing_generation(self, steps, fields=ROUTING_FIELDS):
        for _ in range(15):  # 既存実launcherテストと同じ、前ジョブの後始末待ち
            plan = self.new_plan()
            def dataset(current):
                current['proposal']['datasets'] = [{'view': 'v_ai_routing_step', 'fields': fields}]
            plan = self.store.update(plan['id'], OWNER, plan['revision'], dataset)
            response = json.dumps({'steps': steps, 'python': 'emit_report("確認")'})
            result, _ = self.generate(plan, response)
            if result['codegen'].get('reasons') != ['sql_validation_busy']:
                return result
            time.sleep(2)
        self.fail('実launcherの後始末を確認できません')

    def test_invalid_approved_and_projected_columns_are_rejected_at_generation(self):
        cases = [
            [{'name': 'w_a', 'query': 'SELECT routing_id FROM v_ai_routing_step'}],
            [{'name': 'w_a', 'query': 'WITH s AS (SELECT id AS engineering_id FROM v_ai_routing_step) SELECT s.id FROM s'}],
            [{'name': 'w_a', 'query': 'SELECT id AS matched_id FROM v_ai_routing_step'},
             {'name': 'w_b', 'query': 'SELECT m.id FROM w_a m'}],
        ]
        for steps in cases:
            with self.subTest(steps=steps):
                result = self.routing_generation(steps)
                self.assertEqual(result['codegen']['status'], 'failed')
                self.assertEqual(result['codegen']['reasons'], ['sql_validation_failed'])
                self.assertIsNone(result['codegen']['inflight'])

    def test_valid_cte_alias_and_sequential_join_are_generated_without_trial_approval(self):
        steps = [
            {'name': 'w_a', 'query': 'WITH s AS (SELECT id AS engineering_id, routing_id, output_product_code, parent_product_code FROM v_ai_routing_step) SELECT * FROM s'},
            {'name': 'w_b', 'query': 'SELECT b.engineering_id, a.engineering_id AS matched_id FROM w_a b LEFT JOIN w_a a ON b.routing_id = a.routing_id AND b.parent_product_code = a.output_product_code AND b.engineering_id <> a.engineering_id'},
        ]
        result = self.routing_generation(steps, [*ROUTING_FIELDS, 'routing_id'])
        self.assertEqual(result['codegen']['status'], 'generated', result['codegen'])
        self.assertIsNone(result['codegen']['trial'])
