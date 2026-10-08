"""目的の月と、期間(画面の開始日・終了日)の食い違いの警告(2026-10-08、BOSS承認)を検証する。

実機の試験で、「8月の出荷数量」を、期間欄が7/31〜9/30のまま実行し、8月以外も含まれた。機械的な検査で、承認の前に、警告を出す(承認は妨げない)。
"""
import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from ai.services.analysis_data_service import _mentioned_months, period_warnings
from ai.services.analysis_plan_store import AnalysisPlanStore, public_plan
from ai.services.analysis_planning_service import create_plan
from ai.test_analysis_planning import FakeRedis


class MentionedMonthsTests(SimpleTestCase):
    def test_months_ranges_and_non_months(self):
        cases = {
            '8月の出荷数量': {8},
            '2026年8月と9月を比べて': {8, 9},
            '8月〜9月の出荷': {8, 9}, '8月～10月': {8, 9, 10}, '8月から10月まで': {8, 9, 10}, '8月-9月': {8, 9},
            '12月と1月': {12, 1},
            '品番の出荷を比べて': set(),
            '直近2か月の出荷': set(), '12ヶ月の推移': set(), '2か月分': set(),   # 月の前が数字だけで、「月」が続かない
            '期間: 2026-08-01 〜 2026-09-30': set(),                              # 日付の形の期間は、月の記述ではない
            '13月': set(),                                                          # 存在しない月
            '11月と12月': {11, 12},
            '10月': {10},
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(_mentioned_months(text), expected)


class PeriodWarningTests(SimpleTestCase):
    def test_a_period_wider_than_the_month_in_the_purpose_is_warned(self):
        # 実機の試験T3: 目的は8月、期間欄は7/31〜9/30
        found = period_warnings('8月の出荷数量を、日ごとに集計して', '2026-07-31', '2026-09-30')
        self.assertEqual(len(found), 1)
        self.assertIn('8月', found[0]); self.assertIn('7月・9月の分も含まれます', found[0])

    def test_a_month_of_the_purpose_missing_from_the_period_is_warned(self):
        # 実機の入荷出荷の比較: 目的は8月と9月、期間欄は9/1〜9/30だけ
        found = period_warnings('2026年8月と9月の出荷を比べて', '2026-09-01', '2026-09-30')
        self.assertEqual(len(found), 1)
        self.assertIn('8月が、期間', found[0]); self.assertIn('含まれていません', found[0])

    def test_both_directions_can_be_warned_together(self):
        found = period_warnings('8月の出荷数量', '2026-09-01', '2026-10-31')
        self.assertEqual(len(found), 2)

    def test_matching_periods_are_not_warned(self):
        for purpose, start, end in (('8月の出荷数量', '2026-08-01', '2026-08-31'), ('8月と9月の出荷を比べて', '2026-08-01', '2026-09-30'),
                                    ('8月〜9月の出荷', '2026-08-01', '2026-09-30'), ('9月の前半と後半を比べて', '2026-09-01', '2026-09-30'),
                                    ('8月の出荷数量', '2026-08-05', '2026-08-20')):   # 月の一部の期間は、その月の中なので、よい
            with self.subTest(purpose=purpose):
                self.assertEqual(period_warnings(purpose, start, end), [])

    def test_no_month_in_the_purpose_means_no_check(self):
        self.assertEqual(period_warnings('品番ごとの出荷を集計して', '2026-07-31', '2026-09-30'), [])
        self.assertEqual(period_warnings('直近2か月の出荷', '2026-07-31', '2026-09-30'), [])

    def test_a_period_over_a_year_end_is_handled(self):
        self.assertEqual(period_warnings('12月と1月の出荷', '2026-12-01', '2027-01-31'), [])
        self.assertEqual(len(period_warnings('12月の出荷', '2026-12-01', '2027-01-31')), 1)

    def test_the_period_line_added_by_the_screen_does_not_count_as_a_month(self):
        # 画面が、目的文に「期間: 2026-08-01 〜 2026-09-30」の行を足しても、月の記述としては読まない
        self.assertEqual(period_warnings('品番ごとに集計して\n期間: 2026-08-01 〜 2026-09-30', '2026-08-01', '2026-09-30'), [])


@override_settings(AI_ANALYSIS_REDIS_URL='redis://test.invalid/0')
class PlanIntegrationTests(SimpleTestCase):
    def setUp(self):
        self.redis = FakeRedis()
        for target, kwargs in (('ai.services.analysis_plan_store.Redis.from_url', {'return_value': self.redis}),
                               ('ai.services.analysis_planning_service.get_analysis_execution_policy', {'return_value': SimpleNamespace(plan_cache_ttl_minutes=60, max_fetch_rows=100000)}),
                               ('ai.services.analysis_planning_service.planning_options', {'return_value': {'available': True}}),
                               ('ai.services.analysis_planning_service.get_qwen_analysis_timeout', {'return_value': 240}),
                               ('ai.services.analysis_llm.get_analysis_temperature', {'return_value': 0.3})):
            patcher = patch(target, **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.raw = json.dumps({'title': 't', 'steps': ['日ごとに集計'], 'outputs': ['日付、数量'],
                               'datasets': [{'view': 'v_ai_shipment', 'fields': ['shipment_date', 'quantity']}]})

    def create(self, purpose, start, end):
        with patch('ai.services.analysis_planning_service.chat_service._chat', return_value=self.raw):
            return create_plan(3, {'purpose': purpose, 'date_from': start, 'date_to': end})

    def test_the_warning_is_stored_with_the_plan_and_does_not_block_the_approval(self):
        plan = self.create('8月の出荷数量を、日ごとに集計して', '2026-07-31', '2026-09-30')
        self.assertEqual(len(plan['warnings']), 1)
        self.assertIn('7月・9月の分も含まれます', plan['warnings'][0])
        self.assertEqual(public_plan(AnalysisPlanStore().get(plan['id'], 3))['warnings'], plan['warnings'])
        self.assertEqual(plan['status'], 'awaiting_method')  # 警告は、承認を妨げない

    def test_no_warning_key_when_the_period_matches(self):
        plan = self.create('8月の出荷数量を、日ごとに集計して', '2026-08-01', '2026-08-31')
        self.assertNotIn('warnings', plan)

    def test_it_is_added_after_the_column_warnings(self):
        raw = json.dumps({'title': 't', 'steps': ['customer_codeで集計'], 'outputs': ['納入場の合計'],
                          'datasets': [{'view': 'v_ai_shipment', 'fields': ['shipment_date', 'quantity']}]})
        with patch('ai.services.analysis_planning_service.chat_service._chat', return_value=raw):
            plan = create_plan(3, {'purpose': '8月の納入場ごとの出荷数量', 'date_from': '2026-07-31', 'date_to': '2026-09-30'})
        self.assertGreaterEqual(len(plan['warnings']), 2)
        self.assertIn('ship_to_code', plan['warnings'][0])        # 列の食い違い
        self.assertIn('期間', plan['warnings'][-1])               # 期間の食い違い
