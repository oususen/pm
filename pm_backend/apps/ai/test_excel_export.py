"""社内AIの表Excel出力フラグを検証する。"""
from django.test import SimpleTestCase

from ai.services.chat_service import _is_qwen_my_overtime_followup, _qwen_excel_export_requested


class QwenExcelExportTest(SimpleTestCase):
    def test_enables_download_for_requested_markdown_table(self):
        answer = '| 品番 | 数量 |\n| --- | ---: |\n| 00833 | 1,272 |'

        self.assertTrue(_qwen_excel_export_requested('表で出して', answer))
        self.assertTrue(_qwen_excel_export_requested('Excelにして', answer))

    def test_does_not_enable_download_without_table_or_request(self):
        table_answer = '| 品番 | 数量 |\n| --- | ---: |\n| 00833 | 1,272 |'

        self.assertFalse(_qwen_excel_export_requested('教えて', table_answer))
        self.assertFalse(_qwen_excel_export_requested('Excelにして', '数量は1,272個です。'))

    def test_recognizes_only_contextual_my_overtime_followups(self):
        history = [{'role': 'assistant', 'content': '2026年9月のあなたの残業申請時間は合計 12時間です。'}]

        self.assertTrue(_is_qwen_my_overtime_followup('残業多いね', history))
        self.assertFalse(_is_qwen_my_overtime_followup('2026年8月の残業は？', history))
        self.assertFalse(_is_qwen_my_overtime_followup('板金グループの残業は？', history))
