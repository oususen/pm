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
        from production.scheduler.tasks_safety_stock import run_auto_safety_stock
        from production.scheduler.tasks_purchase_actual_reconcile import run_purchase_actual_reconcile_check
        from production.scheduler.tasks_production_actual_reconcile import run_production_actual_reconcile_check
        from purchase.order_proposal_views import run_auto_purchase_order_check

        # 既存ジョブ（設定チェックを除く）をクリア
        for job in scheduler.get_jobs():
            if job.id == 'config_checker':
                continue
            try:
                scheduler.remove_job(job.id)
            except Exception:
                pass

        inventory_jobs = [
            ('INVENTORY_RECALC', 'inventory_recalc', {'scheduled_hour': 7, 'scheduled_minute': 0, 'is_enabled': True}),
            ('PICKUP_ONLY', 'pickup_only', {'scheduled_hour': 7, 'scheduled_minute': 30, 'is_enabled': False}),
            ('INVENTORY_ONLY', 'inventory_only', {'scheduled_hour': 8, 'scheduled_minute': 0, 'is_enabled': False}),
            ('PROGRESS_ONLY', 'progress_only', {'scheduled_hour': 8, 'scheduled_minute': 30, 'is_enabled': False}),
        ]
        for task_name, job_id, defaults in inventory_jobs:
            cfg, _ = ScheduleConfig.objects.get_or_create(
                task_name=task_name,
                line=None,
                defaults=defaults,
            )
            if not cfg.is_enabled:
                logger.info(f'ジョブ無効: {job_id}')
                continue
            trigger = CronTrigger(
                hour=cfg.scheduled_hour,
                minute=cfg.scheduled_minute,
                timezone='Asia/Tokyo',
            )
            scheduler.add_job(
                run_inventory_recalculation,
                trigger,
                id=job_id,
                replace_existing=True,
                misfire_grace_time=3600,
                kwargs={'task_name': task_name},
            )
            logger.info(f'ジョブ登録: {job_id} - {cfg.scheduled_hour:02d}:{cfg.scheduled_minute:02d}')

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

        safety_jobs = [
            (
                'AUTO_SAFETY_STOCK_INTERNAL',
                'auto_safety_stock_internal',
                {'scheduled_dom': 1, 'scheduled_hour': 3, 'scheduled_minute': 0, 'is_enabled': False, 'average_days_window': 60, 'safety_days': 1},
            ),
            (
                'AUTO_SAFETY_STOCK_PURCHASE',
                'auto_safety_stock_purchase',
                {'scheduled_dom': 1, 'scheduled_hour': 3, 'scheduled_minute': 30, 'is_enabled': False, 'average_days_window': 60, 'safety_days': 1},
            ),
        ]
        for task_name, job_id, defaults in safety_jobs:
            cfg, _ = ScheduleConfig.objects.get_or_create(
                task_name=task_name,
                line=None,
                defaults=defaults,
            )
            if not cfg.is_enabled:
                logger.info(f'ジョブ無効: {job_id}')
                continue
            trigger = CronTrigger(
                day=cfg.scheduled_dom if cfg.scheduled_dom is not None else 1,
                hour=cfg.scheduled_hour,
                minute=cfg.scheduled_minute,
                timezone='Asia/Tokyo',
            )
            scheduler.add_job(
                run_auto_safety_stock,
                trigger,
                id=job_id,
                replace_existing=True,
                misfire_grace_time=3600,
                kwargs={'task_name': task_name},
            )
            logger.info(
                f'ジョブ登録: {job_id} - 毎月{cfg.scheduled_dom if cfg.scheduled_dom is not None else 1}日 '
                f'{cfg.scheduled_hour:02d}:{cfg.scheduled_minute:02d}'
            )

        purchase_check_cfg, _ = ScheduleConfig.objects.get_or_create(
            task_name='AUTO_PURCHASE_ORDER_CHECK',
            line=None,
            defaults={
                'scheduled_hour': 6,
                'scheduled_minute': 30,
                'is_enabled': False,
            },
        )
        if purchase_check_cfg.is_enabled:
            trigger = CronTrigger(
                hour=purchase_check_cfg.scheduled_hour,
                minute=purchase_check_cfg.scheduled_minute,
                timezone='Asia/Tokyo',
            )
            scheduler.add_job(
                run_auto_purchase_order_check,
                trigger,
                id='auto_purchase_order_check',
                replace_existing=True,
                misfire_grace_time=3600,
            )
            logger.info(
                f'ジョブ登録: auto_purchase_order_check - '
                f'{purchase_check_cfg.scheduled_hour:02d}:{purchase_check_cfg.scheduled_minute:02d}'
            )
        else:
            logger.info('ジョブ無効: auto_purchase_order_check')

        purchase_actual_reconcile_cfg, _ = ScheduleConfig.objects.get_or_create(
            task_name='PURCHASE_ACTUAL_RECONCILE_CHECK',
            line=None,
            defaults={
                'scheduled_hour': 2,
                'scheduled_minute': 0,
                'is_enabled': False,
            },
        )
        if purchase_actual_reconcile_cfg.is_enabled:
            trigger = CronTrigger(
                hour=purchase_actual_reconcile_cfg.scheduled_hour,
                minute=purchase_actual_reconcile_cfg.scheduled_minute,
                timezone='Asia/Tokyo',
            )
            scheduler.add_job(
                run_purchase_actual_reconcile_check,
                trigger,
                id='purchase_actual_reconcile_check',
                replace_existing=True,
                misfire_grace_time=3600,
                kwargs={'apply_fix': False},
            )
            logger.info(
                f'ジョブ登録: purchase_actual_reconcile_check - '
                f'{purchase_actual_reconcile_cfg.scheduled_hour:02d}:{purchase_actual_reconcile_cfg.scheduled_minute:02d}'
            )
        else:
            logger.info('ジョブ無効: purchase_actual_reconcile_check')

        production_actual_reconcile_cfg, _ = ScheduleConfig.objects.get_or_create(
            task_name='PRODUCTION_ACTUAL_RECONCILE_CHECK',
            line=None,
            defaults={
                'scheduled_hour': 2,
                'scheduled_minute': 30,
                'is_enabled': False,
            },
        )
        if production_actual_reconcile_cfg.is_enabled:
            trigger = CronTrigger(
                hour=production_actual_reconcile_cfg.scheduled_hour,
                minute=production_actual_reconcile_cfg.scheduled_minute,
                timezone='Asia/Tokyo',
            )
            scheduler.add_job(
                run_production_actual_reconcile_check,
                trigger,
                id='production_actual_reconcile_check',
                replace_existing=True,
                misfire_grace_time=3600,
                kwargs={'apply_fix': False},
            )
            logger.info(
                f'ジョブ登録: production_actual_reconcile_check - '
                f'{production_actual_reconcile_cfg.scheduled_hour:02d}:{production_actual_reconcile_cfg.scheduled_minute:02d}'
            )
        else:
            logger.info('ジョブ無効: production_actual_reconcile_check')

    def _check_config_changes(self, scheduler):
        """DB設定の変更を検知してジョブを再登録"""
        try:
            self._register_jobs(scheduler)
        except Exception as e:
            logger.error(f'設定チェックエラー: {e}', exc_info=True)
