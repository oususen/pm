"""補完コマンドの既定動作は照合のみ。適用オプションは実行しない。"""
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from quality.models_scrap import ScrapRecord


class ScrapOperatorBackfillTest(TestCase):
    def test_default_matches_exact_unique_names_without_updates(self):
        get_user_model().objects.create_user(username='000175', last_name='一致', first_name='太郎')
        for username in ('000176', '000177'):
            get_user_model().objects.create_user(username=username, last_name='同姓', first_name='同名')
        for name in ('一致 太郎', '同姓 同名', '不明', '一致太郎'):
            ScrapRecord.objects.create(operator_name=name)
        ScrapRecord.objects.create(operator_name='一致 太郎', operator_login_id='existing')
        out = StringIO()
        call_command('backfill_scrap_operator_login_id', stdout=out)
        self.assertEqual(ScrapRecord.objects.filter(operator_login_id__isnull=True).count(), 4)
        self.assertTrue(ScrapRecord.objects.filter(operator_login_id='existing').exists())
        output = out.getvalue()
        self.assertIn('対象件数=4 候補件数=1 曖昧件数=1 不一致件数=2 更新件数=0', output)
        self.assertIn('一致件数=2', output)
        self.assertIn("operator_name='一致太郎' 一致件数=0", output)
