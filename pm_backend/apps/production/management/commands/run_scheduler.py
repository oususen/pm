"""
定時タスクスケジューラ
APSchedulerを使用して、DBに保存された設定に基づいてタスクを実行する

使い方:
  python manage.py run_scheduler
"""
import logging
import signal
import time

from django.core.management.base import BaseCommand

logger = logging.getLogger('production')


class Command(BaseCommand):
    help = '定時タスクスケジューラを起動します'

    def handle(self, *args, **options):
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        from production.models_schedule_config import ScheduleConfig

        self.stdout.write(self.style.SUCCESS('スケジューラを起動しています...'))

        scheduler = BackgroundScheduler(timezone='Asia/Tokyo')
        self._last_config = None

        # DBから設定を読み込んでジョブを登録
        self._register_jobs(scheduler)

        # 設定変更の定期チェック（5分ごと）
        scheduler.add_job(
            self._check_config_changes,
            CronTrigger(minute='*/5', timezone='Asia/Tokyo'),
            id='config_checker',
            args=[scheduler],
            replace_existing=True,
        )

        scheduler.start()
        self.stdout.write(self.style.SUCCESS('スケジューラが起動しました'))

        # シグナルハンドリング（graceful shutdown）
        def shutdown(signum, frame):
            self.stdout.write('シャットダウン中...')
            scheduler.shutdown(wait=True)
            self.stdout.write(self.style.SUCCESS('スケジューラを停止しました'))
            raise SystemExit(0)

        signal.signal(signal.SIGTERM, shutdown)
        signal.signal(signal.SIGINT, shutdown)

        # メインスレッドを生かしておく
        try:
            while True:
                time.sleep(60)
        except SystemExit:
            pass

    def _register_jobs(self, scheduler):
        """DBの設定に基づいてジョブを登録"""
        from apscheduler.triggers.cron import CronTrigger
        from production.models_schedule_config import ScheduleConfig
        from production.scheduler.tasks import run_inventory_recalculation

        config, created = ScheduleConfig.objects.get_or_create(
            task_name='INVENTORY_RECALC',
            defaults={
                'scheduled_hour': 7,
                'scheduled_minute': 0,
                'is_enabled': True,
            },
        )

        job_id = 'inventory_recalc'

        if config.is_enabled:
            trigger = CronTrigger(
                hour=config.scheduled_hour,
                minute=config.scheduled_minute,
                timezone='Asia/Tokyo',
            )
            scheduler.add_job(
                run_inventory_recalculation,
                trigger,
                id=job_id,
                replace_existing=True,
                misfire_grace_time=3600,
            )
            self.stdout.write(
                f'ジョブ登録: {job_id} - '
                f'{config.scheduled_hour:02d}:{config.scheduled_minute:02d}'
            )
            logger.info(
                f'ジョブ登録: {job_id} - '
                f'{config.scheduled_hour:02d}:{config.scheduled_minute:02d}'
            )
        else:
            try:
                scheduler.remove_job(job_id)
            except Exception:
                pass
            self.stdout.write(f'ジョブ無効: {job_id}')
            logger.info(f'ジョブ無効: {job_id}')

        self._last_config = {
            'hour': config.scheduled_hour,
            'minute': config.scheduled_minute,
            'enabled': config.is_enabled,
        }

    def _check_config_changes(self, scheduler):
        """DB設定の変更を検知してジョブを再登録"""
        from production.models_schedule_config import ScheduleConfig

        try:
            config = ScheduleConfig.objects.filter(
                task_name='INVENTORY_RECALC'
            ).first()
            if not config:
                return

            current = {
                'hour': config.scheduled_hour,
                'minute': config.scheduled_minute,
                'enabled': config.is_enabled,
            }

            if current != self._last_config:
                logger.info(f'設定変更を検知: {self._last_config} -> {current}')
                self._register_jobs(scheduler)
        except Exception as e:
            logger.error(f'設定チェックエラー: {e}')
