"""開発PCだけの明示的な実行枠復旧。既定は確認のみ。"""
from django.core.management.base import BaseCommand, CommandError

from ai.services.analysis_recovery_service import recover_slot


class Command(BaseCommand):
    help = '停止・残骸不在・DB後始末を確認する。解除にはジョブIDと--applyが必須。'

    def add_arguments(self, parser):
        parser.add_argument('--job-id', required=True)
        parser.add_argument('--apply', action='store_true', help='安全確認に合格した対象の実行枠だけを解除する')

    def handle(self, *args, **options):
        try:
            result = recover_slot(options['job_id'], options['apply'])
        except Exception:
            raise CommandError('復旧条件を確認できませんでした。解除しません。ワーカー・launcher停止、ジョブID、Docker残骸、DB後始末、履歴を確認してください。') from None
        self.stdout.write('実行枠を解除しました。' if result['released'] else '確認に合格しました。確認のみで、実行枠は解除していません。')
