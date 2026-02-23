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
        from production.scheduler.tasks_auto_plan import run_auto_plan
        from production.scheduler.tasks_order_expansion import run_order_expansion

        # 既存ジョブ（設定チェックを除く）をクリア
        for job in scheduler.get_jobs():
            if job.id == 'config_checker':
                continue
            try:
                scheduler.remove_job(job.id)
            except Exception:
                pass

        inv_cfg, _ = ScheduleConfig.objects.get_or_create(
            task_name='INVENTORY_RECALC',
            defaults={
                'scheduled_hour': 7,
                'scheduled_minute': 0,
                'is_enabled': True,
            },
        )
        if inv_cfg.is_enabled:
            trigger = CronTrigger(
                hour=inv_cfg.scheduled_hour,
                minute=inv_cfg.scheduled_minute,
                timezone='Asia/Tokyo',
            )
            scheduler.add_job(
                run_inventory_recalculation,
                trigger,
                id='inventory_recalc',
                replace_existing=True,
                misfire_grace_time=3600,
            )
            logger.info(f'ジョブ登録: inventory_recalc - {inv_cfg.scheduled_hour:02d}:{inv_cfg.scheduled_minute:02d}')
        else:
            logger.info('ジョブ無効: inventory_recalc')

        auto_configs = ScheduleConfig.objects.filter(task_name='AUTO_PLAN', line__isnull=False)
        for cfg in auto_configs:
            if not cfg.is_enabled:
                continue
            trigger = CronTrigger(
                day=cfg.scheduled_dom if cfg.scheduled_dom is not None else '*',
                hour=cfg.scheduled_hour,
                minute=cfg.scheduled_minute,
                timezone='Asia/Tokyo',
            )
            job_id = f'auto_plan_{cfg.id}'
            scheduler.add_job(
                run_auto_plan,
                trigger,
                id=job_id,
                replace_existing=True,
                misfire_grace_time=3600,
                kwargs={'config_id': cfg.id},
            )
            logger.info(
                f'ジョブ登録: {job_id} - {cfg.scheduled_hour:02d}:{cfg.scheduled_minute:02d} '
                f'(line={cfg.line.line_code if cfg.line_id else "-"})'
            )

        order_cfg, _ = ScheduleConfig.objects.get_or_create(
            task_name='ORDER_EXPANSION',
            line=None,
            defaults={
                'scheduled_hour': 6,
                'scheduled_minute': 0,
                'is_enabled': False,
            },
        )
        if order_cfg.is_enabled:
            trigger = CronTrigger(
                hour=order_cfg.scheduled_hour,
                minute=order_cfg.scheduled_minute,
                timezone='Asia/Tokyo',
            )
            scheduler.add_job(
                run_order_expansion,
                trigger,
                id='order_expansion',
                replace_existing=True,
                misfire_grace_time=3600,
            )
            logger.info(f'ジョブ登録: order_expansion - {order_cfg.scheduled_hour:02d}:{order_cfg.scheduled_minute:02d}')
        else:
            logger.info('ジョブ無効: order_expansion')

    def _check_config_changes(self, scheduler):
        """DB設定の変更を検知してジョブを再登録"""
        try:
            self._register_jobs(scheduler)
        except Exception as e:
            logger.error(f'設定チェックエラー: {e}', exc_info=True)
