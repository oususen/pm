"""
定時タスク: 修正流動率の閾値チェック＆Push/メール通知（製品別集計）
"""
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal

logger = logging.getLogger("quality")


def run_rework_alert_check(config_id=None):
    """修正流動率を製品別に計算し、閾値超過時にPush通知（+メール）を送る"""
    from quality.models_integrated_checksheet import ChecksheetReworkAlertConfig

    if config_id:
        configs = ChecksheetReworkAlertConfig.objects.filter(id=config_id, is_enabled=True)
    else:
        configs = ChecksheetReworkAlertConfig.objects.filter(is_enabled=True)

    configs = configs.select_related("line").prefetch_related("notify_users")

    for cfg in configs:
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


def _build_product_stats(cfg):
    """製品別に修正流動率を集計し、閾値超過の製品リストを返す"""
    from quality.models_integrated_checksheet import IntegratedChecksheetCheck

    today = date.today()
    start_date = today - timedelta(days=cfg.lookback_days - 1)

    checks = (
        IntegratedChecksheetCheck.objects
        .filter(
            unit__batch__line=cfg.line,
            unit__batch__plan_date__gte=start_date,
            unit__batch__plan_date__lte=today,
            judgement__in=["OK", "NG", "修正流動"],
        )
        .values_list("judgement", "unit_id", "unit__batch__product__product_code")
    )

    product_units = {}
    for judgement, unit_id, product_code in checks:
        code = product_code or "不明"
        if code not in product_units:
            product_units[code] = {}
        if unit_id not in product_units[code]:
            product_units[code][unit_id] = False
        if judgement == "修正流動":
            product_units[code][unit_id] = True

    threshold = cfg.threshold_rate
    exceeded = []
    all_stats = []

    for product_code, units in sorted(product_units.items()):
        total = len(units)
        rework = sum(1 for has_rework in units.values() if has_rework)
        rate = Decimal(rework) / Decimal(total) * 100 if total > 0 else Decimal(0)
        stat = {
            "product_code": product_code,
            "total": total,
            "rework": rework,
            "rate": rate,
        }
        all_stats.append(stat)
        if rate >= threshold:
            exceeded.append(stat)

    return start_date, today, all_stats, exceeded


def _check_and_notify(cfg):
    from notifications.models import PushSubscription
    from notifications.web_push import send_web_push

    start_date, today, all_stats, exceeded = _build_product_stats(cfg)
    threshold = cfg.threshold_rate
    period_str = f"{start_date}～{today}"

    total_all = sum(s["total"] for s in all_stats)
    if total_all == 0:
        return f"対象台数0 ({period_str})"

    if not exceeded:
        summary_parts = [f"{s['product_code']}:{s['rate']:.1f}%" for s in all_stats[:5]]
        return (
            f"閾値以下 (閾値{threshold}%) "
            f"{' / '.join(summary_parts)} "
            f"({period_str})"
        )

    notify_user_ids = list(cfg.notify_users.values_list("id", flat=True))
    if not notify_user_ids:
        product_list = ", ".join(f"{s['product_code']}({s['rate']:.1f}%)" for s in exceeded)
        return f"閾値超過だが通知先未設定: {product_list} ({period_str})"

    exceeded_lines = []
    for s in exceeded:
        exceeded_lines.append(
            f"  {s['product_code']}: {s['rate']:.1f}% ({s['rework']}/{s['total']}台)"
        )

    body_text = (
        f"修正流動率が閾値 {threshold}% を超えた製品:\n"
        + "\n".join(exceeded_lines)
        + f"\n期間: {start_date.strftime('%m/%d')}～{today.strftime('%m/%d')}"
    )

    push_sent = 0
    for s in exceeded:
        payload = {
            "title": f"修正流動率 閾値超過: {cfg.line.line_name} {s['product_code']}",
            "body": (
                f"修正流動率 {s['rate']:.1f}% (閾値 {threshold}%)\n"
                f"対象: {s['rework']}/{s['total']}台 "
                f"({start_date.strftime('%m/%d')}～{today.strftime('%m/%d')})"
            ),
            "tag": f"rework-alert-{cfg.line.line_code}-{s['product_code']}",
            "url": "/quality/product-checksheet/integrated/weekly-monthly",
        }
        subs = PushSubscription.objects.filter(user_id__in=notify_user_ids)
        for sub in subs:
            if send_web_push(sub, payload):
                push_sent += 1

    email_result = ""
    if cfg.email_enabled:
        email_result = _send_alert_email(cfg, exceeded, start_date, today)

    product_list = ", ".join(f"{s['product_code']}({s['rate']:.1f}%)" for s in exceeded)
    return (
        f"閾値超過{len(exceeded)}製品: {product_list} "
        f"Push{push_sent}件 {email_result}"
        f"({period_str})"
    )


def _send_alert_email(cfg, exceeded, start_date, today):
    """閾値超過製品の一覧をメールで送信"""
    from shipping.services.email_service import EmailService
    from django.contrib.auth import get_user_model

    User = get_user_model()
    notify_users = cfg.notify_users.all()
    to_emails = []
    for user in notify_users:
        email = getattr(user, "email", "") or ""
        if email.strip():
            to_emails.append(email.strip())

    if not to_emails:
        return "メール送信先なし "

    subject = f"【修正流動率 閾値超過】{cfg.line.line_name} ({start_date.strftime('%m/%d')}～{today.strftime('%m/%d')})"

    lines = [
        f"修正流動率が閾値 {cfg.threshold_rate}% を超えた製品があります。",
        f"",
        f"ライン: {cfg.line.line_name} ({cfg.line.line_code})",
        f"期間: {start_date} ～ {today}",
        f"",
        f"{'製品コード':<16} {'修正流動率':>10} {'修正流動台数':>12} {'判定台数':>8}",
        "-" * 56,
    ]
    for s in exceeded:
        lines.append(
            f"{s['product_code']:<16} {s['rate']:>9.1f}% {s['rework']:>11}台 {s['total']:>7}台"
        )
    lines.append("")
    lines.append("詳細は工程一体チェックシート推移確認画面をご確認ください。")

    body = "\n".join(lines)

    service = EmailService()
    result = service.send_plain_email(to_emails=to_emails, subject=subject, body=body)
    if result.get("success"):
        return f"メール{len(to_emails)}件送信 "
    else:
        logger.warning("修正流動率アラートメール送信失敗: %s", result.get("message", ""))
        return f"メール送信失敗({result.get('message', '')}) "
