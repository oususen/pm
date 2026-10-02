"""社内AIの安全境界と根拠提示を守る回帰テスト。"""
from django.test import SimpleTestCase

from ai.context.screen_context import resolve_screen_context
from ai.services.chat_service import (
    _cross_screen_target_from_question, _grounding_unavailable_answer,
    _unavailable_data_reason, _unusable_model_answer_reason,
)
from ai.services.knowledge_retriever import knowledge_prompt
from ai.services.sql_queries import _validate_sql, allowed_tables_for_screen


class AIChatRegressionTest(SimpleTestCase):
    """モデルやプロンプトを変更しても、守るべき業務上の境界を検証する。"""

    def test_readonly_sql_adds_a_row_limit(self):
        statement, error = _validate_sql(
            'SELECT product_code FROM m_product', {'m_product'}, max_rows=30,
        )

        self.assertIsNone(error)
        self.assertEqual(statement, 'SELECT product_code FROM m_product LIMIT 30')

    def test_readonly_sql_rejects_writes_and_wildcards(self):
        for sql in (
            'DELETE FROM m_product',
            'SELECT * FROM m_product',
            'SELECT product_code FROM m_product; SELECT product_code FROM m_product',
        ):
            with self.subTest(sql=sql):
                statement, error = _validate_sql(sql, {'m_product'}, max_rows=30)
                self.assertIsNone(statement)
                self.assertTrue(error)

    def test_readonly_sql_rejects_tables_outside_the_screen_boundary(self):
        statement, error = _validate_sql(
            'SELECT product_code FROM m_product JOIN t_scrap_record ON m_product.id = t_scrap_record.product_id',
            {'m_product'}, max_rows=30,
        )

        self.assertIsNone(statement)
        self.assertIn('参照できないテーブル', error)

    def test_cross_screen_tables_are_added_only_for_the_approved_question(self):
        normal_tables = allowed_tables_for_screen('production')
        approved_tables = allowed_tables_for_screen('production', ('overtime',))

        self.assertNotIn('t_overtime_application', normal_tables)
        self.assertIn('t_overtime_application', approved_tables)

    def test_production_screen_does_not_include_overtime_without_cross_screen_approval(self):
        context = resolve_screen_context('/production/brake-line-input')

        self.assertNotIn('overtime', context['allowed_intents'])

    def test_overtime_screen_requests_production_access_for_brake_worker_questions(self):
        context = resolve_screen_context('/overtime/menu')

        self.assertEqual(
            _cross_screen_target_from_question('ブレーキ工程の作業者別・日別の残業時間を確認したい', context),
            'production',
        )

    def test_brake_worker_overtime_without_a_defined_worker_mapping_explains_the_reason(self):
        reason = _unavailable_data_reason('ブレーキ工程の作業者別・日別の残業時間を確認したい')
        answer = _grounding_unavailable_answer(reason)

        self.assertIn('正規データが未定義', answer)
        self.assertIn('仮の一覧は表示しません', answer)

    def test_production_and_overtime_trend_is_not_judged_without_a_defined_same_population(self):
        reason = _unavailable_data_reason('ブレーキ工程の直近の生産数と残業時間の推移を比較したい')

        self.assertIn('工程と残業申請対象者を結び付ける正規データがない', reason)

    def test_general_production_and_overtime_question_is_left_to_the_ai(self):
        reason = _unavailable_data_reason('生産数が少ない日に、残業申請時間は増えている？')

        self.assertEqual(reason, '')

    def test_model_internal_thought_and_unfetched_rows_are_rejected(self):
        self.assertTrue(_unusable_model_answer_reason('thought\n<channel|>調査します'))
        self.assertTrue(_unusable_model_answer_reason('| 氏名 | 時間 | 件数 |\n| A | - | - |\n※データ取得中'))

    def test_knowledge_prompt_requires_source_grounding(self):
        prompt = knowledge_prompt([{
            'path': 'AIナレッジ資料/工程手順.pdf', 'heading': '第1章', 'content': '検査は作業完了後に行う。',
        }])

        self.assertIn('根拠がある場合だけ回答に使い', prompt)
        self.assertIn('推測しないでください', prompt)
        self.assertIn('工程手順.pdf', prompt)
