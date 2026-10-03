"""試行回数を生成回数に加算しないことを、実サービスの状態更新で確認する。

Redis・AI・launcherは模擬する。生成コードは実行しない。
"""
import copy
import json
from unittest.mock import patch

from django.test import SimpleTestCase

from ai.services import analysis_codegen_service as cg
from ai.services.analysis_plan_store import AnalysisError
from ai.test_analysis_codegen import DATASETS, GOOD_PYTHON, GOOD_STEPS, POLICY, OWNER, VIEWS


class TrialGenerationCountTests(SimpleTestCase):
    def test_repeated_passed_failed_unverified_trials_do_not_consume_generation(self):
        bundle = cg.make_bundle(GOOD_STEPS, GOOD_PYTHON, VIEWS)
        plan = {'id': 'trial-count', 'owner_id': OWNER, 'revision': 3, 'status': 'data_approved',
                'proposal': {'datasets': DATASETS},
                'codegen': {'status': 'generated', 'attempts': 2, 'inflight': None,
                            'steps': GOOD_STEPS, 'python': GOOD_PYTHON,
                            'executed_code_sha256': bundle.executed_code_sha256}}

        def get(plan_id, owner_id):
            self.assertEqual((plan_id, owner_id), (plan['id'], OWNER))
            return copy.deepcopy(plan)

        def update(plan_id, owner_id, revision, apply):
            current = get(plan_id, owner_id)
            if revision != current['revision']:
                raise AnalysisError('版が異なります', 409)
            apply(current)
            current['revision'] += 1
            plan.clear()
            plan.update(current)
            return copy.deepcopy(current)

        reports = [({'status': 'ok', 'result': {'report': json.dumps({'trial': 'passed'})}}, 'passed'),
                   ({'status': 'ok', 'result': {'report': json.dumps({'trial': 'failed', 'reason': 'query_failed'})}}, 'failed'),
                   ({'status': 'error', 'reason': 'busy'}, 'unverified')]
        with patch.object(cg, 'AnalysisPlanStore') as store, patch.object(cg, '_call_ai') as ai, \
                patch.object(cg, 'launcher_endpoint', return_value=('127.0.0.1', 8091)), \
                patch.object(cg, 'get_analysis_execution_policy', return_value=POLICY), patch.object(cg, '_transmit') as transmit:
            store.return_value.get.side_effect = get
            store.return_value.update.side_effect = update
            for report, expected in reports * 2:
                with self.subTest(status=expected, revision=plan['revision']):
                    transmit.return_value = (200, report)
                    before = plan['revision']
                    returned, trial = cg.run_trial(OWNER, plan['id'], before)
                    self.assertEqual(trial['status'], expected)
                    self.assertEqual(returned['revision'], before + 1)
                    self.assertEqual(plan['codegen']['trial'], trial)
                    self.assertEqual(plan['codegen']['attempts'], 2)
                    self.assertEqual(returned['codegen']['attempts'], 2)
                    self.assertEqual(returned['codegen']['executed_code_sha256'], bundle.executed_code_sha256)
            self.assertEqual(transmit.call_count, 6)
            ai.assert_not_called()
