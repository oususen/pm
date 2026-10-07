"""列の意味・言葉の対応表・食い違いの警告(BOSS承認 2026-10-07)を検証する。

AIの実際の応答は使わない(模擬)。目的の言葉と列の食い違いは、サーバーの機械的な検査で見つける。
"""
import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from ai.services import analysis_consult_service as consult
from ai.services.analysis_data_service import ANALYSIS_VIEWS, TERM_COLUMNS, column_warnings, term_guide_text
from ai.services.analysis_plan_store import AnalysisPlanStore, public_plan
from ai.services.analysis_planning_service import create_plan
from ai.test_analysis_planning import FakeRedis

SHIPMENT = 'v_ai_shipment'


def proposal(fields, steps=('抽出して集計する',), outputs=('一覧',), view=SHIPMENT):
    return {'title': 't', 'steps': list(steps), 'outputs': list(outputs), 'datasets': [{'view': view, 'fields': list(fields)}]}


class DescriptionTests(SimpleTestCase):
    def test_columns_have_meanings_and_ship_to_and_customer_are_not_confused(self):
        text = ANALYSIS_VIEWS[SHIPMENT]['description']
        for part in ('ship_to_code=納入場(納入地)のコード', 'customer_code=得意先(顧客・客先・出荷先)のコード', 'quantity=出荷数量', 'product_code=品番', '混同しない'):
            self.assertIn(part, text)
        receipt = ANALYSIS_VIEWS['v_ai_purchase_receipt']['description']
        for part in ('qty=入荷数量', 'supplier_id=仕入先(外作先)のID', 'arrival_date=入荷日'):
            self.assertIn(part, receipt)

    def test_no_real_data_note_and_no_unconfirmed_meaning(self):
        joined = ''.join(view['description'] for view in ANALYSIS_VIEWS.values())
        self.assertNotIn('000196', joined)      # 実データの注記は渡さない
        self.assertNotIn('クボタ', joined)
        self.assertNotIn('process_id', joined)  # 意味が確認できていない列は書かない

    def test_term_guide_follows_the_boss_table(self):
        guide = term_guide_text()
        for part in ('納入地・納入場・納入場所=ship_to_code', '顧客・得意先・客先・出荷先=customer_code', '品番・部番=product_code',
                     '製品名・品名=product_name', '出荷数量・出荷数=quantity', '入荷数量・入荷数=qty', '仕入先・外作先=supplier_id'):
            self.assertIn(part, guide)
        self.assertNotIn('納入先=', guide)  # 「納入先」は対応表に載せない
        self.assertIn('「納入先」は対応表にない', guide)
        self.assertEqual(len(TERM_COLUMNS), 9)


class WarningTests(SimpleTestCase):
    def test_missing_column_for_a_term_in_the_purpose_is_warned(self):
        found = column_warnings('品番V1の納入場ごとの出荷数量', proposal(['id', 'shipment_date', 'product_code', 'quantity']))
        self.assertEqual(len(found), 1)
        self.assertIn('「納入場」', found[0]); self.assertIn('ship_to_code', found[0])

    def test_no_warning_when_the_columns_are_there(self):
        self.assertEqual(column_warnings('品番V1の納入場ごとの出荷数量', proposal(['id', 'shipment_date', 'product_code', 'ship_to_code', 'quantity'],
                                                                      steps=['ship_to_codeごとに合計する'])), [])

    def test_the_wrong_column_in_the_steps_is_warned_even_when_the_field_is_fetched(self):
        # 納入場が目的なのに、手順がcustomer_codeで集計している(Qwen 30Bの誤り)
        found = column_warnings('納入場ごとの出荷数量', proposal(['id', 'shipment_date', 'ship_to_code', 'customer_code', 'quantity'],
                                                                 steps=['customer_codeごとにquantityを合計する'], outputs=['納入先(customer_code)']))
        self.assertEqual(len(found), 1)
        self.assertIn('customer_code', found[0]); self.assertIn('ship_to_code', found[0])

    def test_the_qwen_mistake_gets_both_warnings(self):
        found = column_warnings('納入地ごとの出荷数量', proposal(['id', 'shipment_date', 'quantity'], steps=['customer_codeごとにquantityを合計する']))
        self.assertEqual(len(found), 2)

    def test_the_reverse_mistake_is_warned(self):
        found = column_warnings('顧客ごとの出荷数量', proposal(['id', 'shipment_date', 'customer_code', 'quantity'], steps=['ship_to_codeごとに合計する']))
        self.assertEqual(len(found), 1)
        self.assertIn('顧客', found[0])

    def test_shipping_destination_means_the_customer(self):
        # 出荷先は客先(顧客)。customer_codeが必要
        found = column_warnings('出荷先ごとの出荷数量', proposal(['id', 'shipment_date', 'quantity'], steps=['集計する']))
        self.assertEqual(len(found), 1)
        self.assertIn('customer_code', found[0]); self.assertIn('「出荷先」', found[0])
        self.assertEqual(column_warnings('出荷先ごとの出荷数量', proposal(['id', 'shipment_date', 'customer_code', 'quantity'], steps=['customer_codeで集計'])), [])

    def test_a_purpose_with_both_terms_is_not_judged_for_the_wrong_column(self):
        self.assertEqual(column_warnings('顧客と納入場ごとの出荷数量', proposal(['id', 'shipment_date', 'customer_code', 'ship_to_code', 'quantity'],
                                                                      steps=['customer_codeで集計'])), [])

    def test_ship_to_alone_without_a_term_is_not_judged(self):
        # 「納入先」は対応表にないため、検査しない(AIの判断に任せる)
        self.assertEqual(column_warnings('納入先ごとの出荷数量', proposal(['id', 'shipment_date', 'quantity'], steps=['customer_codeで集計'])), [])

    def test_a_view_without_the_column_is_not_checked(self):
        found = column_warnings('納入場ごとの入荷数量', proposal(['id', 'arrival_date', 'qty'], view='v_ai_purchase_receipt'))
        self.assertEqual(found, [])  # 入荷実績に納入場の列はない(AIが対応できないと判断する範囲)

    def test_product_code_is_needed_for_the_product_number_in_either_view(self):
        self.assertEqual(len(column_warnings('品番V1の入荷', proposal(['id', 'arrival_date', 'qty'], view='v_ai_purchase_receipt'))), 1)
        self.assertEqual(column_warnings('品番V1の入荷', proposal(['id', 'arrival_date', 'qty', 'product_code'], view='v_ai_purchase_receipt')), [])

    def test_no_term_no_warning(self):
        self.assertEqual(column_warnings('月別の傾向を見る', proposal(['id', 'shipment_date'])), [])


@override_settings(AI_ANALYSIS_REDIS_URL='redis://test.invalid/0')
class PlanIntegrationTests(SimpleTestCase):
    def setUp(self):
        self.redis = FakeRedis()
        patcher = patch('ai.services.analysis_plan_store.Redis.from_url', return_value=self.redis)
        patcher.start()
        self.addCleanup(patcher.stop)
        policy = SimpleNamespace(plan_cache_ttl_minutes=60, max_fetch_rows=100000)
        for target, kwargs in (('get_analysis_execution_policy', {'return_value': policy}), ('planning_options', {'return_value': {'available': True}}),
                               ('get_qwen_analysis_timeout', {'return_value': 240})):
            patcher = patch(f'ai.services.analysis_planning_service.{target}', **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)

    def create(self, raw_proposal, purpose='納入場ごとの出荷数量'):
        raw = json.dumps(raw_proposal)
        with patch('ai.services.analysis_planning_service.chat_service._chat', return_value=raw) as chat:
            plan = create_plan(3, {'purpose': purpose, 'date_from': '2026-09-01', 'date_to': '2026-09-30'})
        return plan, chat.call_args.args[0]

    def test_warnings_are_stored_with_the_plan_and_shown_to_the_user(self):
        plan, messages = self.create(proposal(['shipment_date', 'quantity'], steps=['customer_codeごとに合計する']))
        self.assertEqual(len(plan['warnings']), 2)
        self.assertEqual(public_plan(AnalysisPlanStore().get(plan['id'], 3))['warnings'], plan['warnings'])
        self.assertEqual(plan['status'], 'awaiting_method')  # 警告は承認を妨げない

    def test_no_warning_key_when_the_plan_matches_the_purpose(self):
        plan, _ = self.create(proposal(['shipment_date', 'ship_to_code', 'quantity'], steps=['ship_to_codeごとに合計する']))
        self.assertNotIn('warnings', plan)

    def test_the_plan_prompt_has_the_work_order_the_term_table_and_the_meanings(self):
        _plan, messages = self.create(proposal(['shipment_date', 'ship_to_code', 'quantity'], steps=['ship_to_codeで集計']))
        system = messages[0]['content']
        for part in ('作業の順序: ①各ビューのdescription(列の意味)をすべて読む', '納入地・納入場・納入場所=ship_to_code', 'ship_to_code=納入場(納入地)のコード'):
            self.assertIn(part, system)
        self.assertNotIn('000196', system)

    def test_the_consult_prompt_has_the_term_table_and_asks_about_unclear_words(self):
        prompt = consult._system_prompt([])
        for part in ('納入地・納入場・納入場所=ship_to_code', '顧客・得意先・客先・出荷先=customer_code', '決められないときは、利用者に確認する', 'ship_to_code=納入場(納入地)のコード'):
            self.assertIn(part, prompt)
        self.assertNotIn('納入場(ship_to_code)かを判断する', prompt)  # 判断と確認の指示が並んで、矛盾しない
