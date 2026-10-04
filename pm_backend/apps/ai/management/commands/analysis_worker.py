"""開発限定の分析専用ワーカーを明示起動する。"""
from django.core.management.base import BaseCommand, CommandError
from ai.services.analysis_job_service import worker_loop


class Command(BaseCommand):
    help = '承認済みAI分析を処理する開発専用ワーカー(1件、待ち行列なし)'

    def handle(self, *args, **options):
        self.stdout.write('分析専用ワーカーを起動します。本番では実行できません。')
        try:
            worker_loop()
        except KeyboardInterrupt:
            self.stdout.write('ワーカーを終了しました。実行中の状態は履歴で確認してください。')
        except Exception as exc:
            raise CommandError('分析専用ワーカーが停止しました。状態・後始末を確認してください。') from exc
