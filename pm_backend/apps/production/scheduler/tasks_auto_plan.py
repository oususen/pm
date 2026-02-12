"""
定時タスク: 生産計画自動生成（需要取り込みのみ）
"""
import logging
from datetime import datetime, timedelta

from production.models_schedule_config import ScheduleConfig
from production.management.commands.generate_production_plan import Command as GeneratePlanCommand
from notifications.models import Notification

logger = logging.getLogger('production')


def _month_range_from(base_date, months_ahead):
    """基準日から指定月数先の月初〜月末を返す"""
    first = base_date.replace(day=1)
    for _ in range(months_ahead):
        first = (first + timedelta(days=32)).replace(day=1)
    start = first
    end = (first + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    return start, end


def _selected_month_offsets(config):
    months = []
    if getattr(config, 'include_next_month', True):
        months.append(1)
    if getattr(config, 'include_second_month', False):
        months.append(2)
    if getattr(config, 'include_third_month', False):
        months.append(3)
    if not months:
        months.append(1)
    return months


def run_auto_plan(force=False, config_id=None):
    """
    指定ライン・期間で生産計画を自動生成する。

    ScheduleConfig(task_name='AUTO_PLAN', line=対象ライン) の設定を使用:
      - scheduled_dom: 実行する日（1-31）。None の場合は毎日対象。
      - include_*_month: 対象期間（翌月/翌々月/翌々翌月）
    """
    qs = ScheduleConfig.objects.filter(task_name='AUTO_PLAN')
    if config_id:
        qs = qs.filter(id=config_id)
    config = qs.select_related('line').first()
    if not config:
        logger.info('[AUTO_PLAN] 対象設定が存在しないためスキップ')
        return

    today = datetime.now().date()
    if not force and config.scheduled_dom and today.day != config.scheduled_dom:
        logger.info(f'[AUTO_PLAN] 本日({today.day})は実行日({config.scheduled_dom})ではないためスキップ (cfg_id={config.id})')
        return
    if not config.line_id:
        logger.warning('[AUTO_PLAN] 対象ラインが設定されていないためスキップ')
        return

    # 実行開始を記録
    config.last_run_at = datetime.now()
    config.last_run_status = 'RUNNING'
    config.last_run_message = '実行中...'
    config.save(update_fields=['last_run_at', 'last_run_status', 'last_run_message'])

    start_time = datetime.now()
    errors = []
    line_stats = []
    success = True

    months = _selected_month_offsets(config)

    try:
        for offset in months:
            start, end = _month_range_from(today, offset)
            cmd = GeneratePlanCommand()
            cmd.handle(
                run_date=str(today),
                start=str(start),
                end=str(end),
                lines=[config.line_id],
                stats=line_stats,
            )
    except Exception as e:
        logger.error(f'[AUTO_PLAN] 実行中にエラー (cfg_id={config.id})', exc_info=True)
        errors.append(str(e))
        success = False

    duration = (datetime.now() - start_time).total_seconds()
    config.last_run_status = 'SUCCESS' if success else 'FAILED'
    config.last_run_duration_seconds = duration
    if success:
        if line_stats:
            msg = [
                f"ライン:{st['line_code']}({st['line_id']}) 期間:{st['start']}~{st['end']} 作成:{st['created']} 更新:{st['updated']}"
                for st in line_stats
            ]
            config.last_run_message = '\n'.join(msg)
        else:
            config.last_run_message = '対象ライン需要無し（後ラインの計画入力漏れの可能性があります）'
    else:
        config.last_run_message = '\n'.join(errors) if errors else '失敗'
    config.save(update_fields=[
        'last_run_status', 'last_run_message', 'last_run_duration_seconds'
    ])

    # 通知条件: 失敗時 または 対象ライン需要無しのとき
    if config.notify_users.exists() and (not success or not line_stats):
        today = datetime.now().date()
        line_label = ''
        if config.line:
            line_label = f"{config.line.line_code} {config.line.line_name or ''}".strip()
        else:
            line_label = '未設定'
        notification = Notification.objects.create(
            title=f"[自動タスク{'失敗' if not success else '結果なし'}] 生産計画自動生成（{line_label}）",
            category='システム',
            domain='生産',
            description=(config.last_run_message or '詳細なし'),
            valid_from=None,  # 下限なしにして表示漏れを防ぐ
            valid_to=today + timedelta(days=7),
            operator_name='admin',
        )
        notification.target_users.set(config.notify_users.all())

    return {
        'success': success,
        'errors': errors,
        'duration': duration,
        'lines': line_stats,
        'months': months,
        'config_id': config.id,
    }
