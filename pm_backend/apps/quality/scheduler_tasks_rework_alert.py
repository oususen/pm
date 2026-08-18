"""
定時タスク: 修正流動率の閾値チェック＆Push通知
"""
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal

from django.db.models import Q

logger = logging.getLogger("quality")


def run_rework_alert_check(config_id=None):
    """修正流動率を計算し、閾値超過時にPush通知を送る"""
    from quality.models_integrated_checksheet import (
        ChecksheetReworkAlertConfig,
        IntegratedChecksheetCheck,
    )
    from notifications.models import PushSubscription
    from notifications.web_push import send_web_push

    if config_id:
        configs = ChecksheetReworkAlertConfig.objects.filter(id=config_id, is_enabled=True)
    else:
        configs = ChecksheetReworkAlertConfig.objects.filter(is_enabled=True)

    configs = configs.select_related("line").prefetch_related("notify_users")

    for cfg in configs:
        started_at = datetime.now()
        try:
            result = _check_and_notify(cfg)
            cfg.last_run_at = datetime.now()
            cfg.last_run_message = result
            cfg.save(update_fields=["last_run_at", "last_run_message", "updated_at"])
            logger.info("修正流動率チェック完了: config=%s line=%s => %s", cfg.id, cfg.line.line_code, result)
        except Exception as e:
            cfg.last_run_at = datetime.now()
            cfg.last_run_message = f"エラー: {e}"
            cfg.save(update_fields=["last_run_at", "last_run_message", "updated_at"])
            logger.exception("修正流動率チェック失敗: config=%s", cfg.id)


def _check_and_notify(cfg):
    from quality.models_integrated_checksheet import IntegratedChecksheetCheck
    from notifications.models import PushSubscription
    from notifications.web_push import send_web_push

    today = date.today()
    start_date = today - timedelta(days=cfg.lookback_days - 1)

    checks = IntegratedChecksheetCheck.objects.filter(
        unit__batch__line=cfg.line,
        unit__batch__plan_date__gte=start_date,
        unit__batch__plan_date__lte=today,
        judgement__in=["OK", "NG", "修正流動"],
    ).values_list("judgement", "unit_id")

    unit_judgements = {}
    for judgement, unit_id in checks:
        if unit_id not in unit_judgements:
            unit_judgements[unit_id] = {"has_rework": False}
        if judgement == "修正流動":
            unit_judgements[unit_id]["has_rework"] = True

    total_units = len(unit_judgements)
    rework_units = sum(1 for v in unit_judgements.values() if v["has_rework"])

    if total_units == 0:
        return f"対象台数0 ({start_date}～{today})"

    rework_rate = Decimal(rework_units) / Decimal(total_units) * 100

    threshold = cfg.threshold_rate
    if rework_rate < threshold:
        return (
            f"閾値以下: 修正流動率{rework_rate:.1f}% "
            f"(閾値{threshold}%) "
            f"台数{rework_units}/{total_units} "
            f"({start_date}～{today})"
        )

    notify_user_ids = list(cfg.notify_users.values_list("id", flat=True))
    if not notify_user_ids:
        return (
            f"閾値超過だが通知先未設定: 修正流動率{rework_rate:.1f}% "
            f"(閾値{threshold}%) "
            f"台数{rework_units}/{total_units}"
        )

    payload = {
        "title": f"修正流動率 閾値超過: {cfg.line.line_name}",
        "body": (
            f"修正流動率 {rework_rate:.1f}% (閾値 {threshold}%)\n"
            f"対象: {rework_units}/{total_units}台 "
            f"({start_date.strftime('%m/%d')}～{today.strftime('%m/%d')})"
        ),
        "tag": f"rework-alert-{cfg.line.line_code}",
        "url": "/quality/product-checksheet/integrated/weekly-monthly",
    }

    subs = PushSubscription.objects.filter(user_id__in=notify_user_ids)
    sent_count = 0
    for sub in subs:
        if send_web_push(sub, payload):
            sent_count += 1

    return (
        f"閾値超過通知送信: 修正流動率{rework_rate:.1f}% "
        f"(閾値{threshold}%) "
        f"台数{rework_units}/{total_units} "
        f"通知{sent_count}件 "
        f"({start_date}～{today})"
    )
