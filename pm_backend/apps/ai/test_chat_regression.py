"""社内AIの安全境界と根拠提示を守る回帰テスト。"""
from django.test import SimpleTestCase

from ai.context.screen_context import resolve_screen_context
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

    def test_knowledge_prompt_requires_source_grounding(self):
        prompt = knowledge_prompt([{
            'path': 'AIナレッジ資料/工程手順.pdf', 'heading': '第1章', 'content': '検査は作業完了後に行う。',
        }])

        self.assertIn('根拠がある場合だけ回答に使い', prompt)
        self.assertIn('推測しないでください', prompt)
        self.assertIn('工程手順.pdf', prompt)
