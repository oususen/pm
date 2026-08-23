from datetime import datetime, time, timedelta

from django.conf import settings
from django.utils import timezone

from orders.utils.calendar_utils import DAY_BOUNDARY_HOUR


def is_countable_session_for_actual(session_type, end_action):
    return str(session_type or '').upper() == 'WORK' and str(end_action or '').upper() in ('END', 'PAUSE')


def _to_local_naive(dt):
    if not dt:
        return None
    if timezone.is_aware(dt):
        return timezone.localtime(dt).replace(tzinfo=None)
    return dt


def build_business_boundary_datetime(target_date, day_offset=0):
    boundary_dt = datetime.combine(
        target_date + timedelta(days=day_offset),
        time(DAY_BOUNDARY_HOUR, 0),
    )
    if settings.USE_TZ:
        return timezone.make_aware(boundary_dt, timezone.get_current_timezone())
    return boundary_dt


def normalize_input_datetime(dt):
    if not dt:
        return None
    if settings.USE_TZ:
        return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
    return timezone.localtime(dt).replace(tzinfo=None) if timezone.is_aware(dt) else dt


def calculate_effective_work_seconds(calendar, started_at, ended_at):
    """
    ラインカレンダ（勤務パターン＋休憩）で区切った実作業秒数を返す。
    """
    start_dt = _to_local_naive(started_at)
    end_dt = _to_local_naive(ended_at)
    if not start_dt or not end_dt or end_dt <= start_dt:
        return 0

    if not calendar:
        return max(int((end_dt - start_dt).total_seconds()), 0)

    total_seconds = 0
    check_date = start_dt.date() - timedelta(days=1)
    last_date = end_dt.date() + timedelta(days=1)

    while check_date <= last_date:
        segments = calendar.get_segments(check_date) or []
        for seg_start, seg_end in segments:
            overlap_start = max(start_dt, seg_start)
            overlap_end = min(end_dt, seg_end)
            if overlap_end > overlap_start:
                total_seconds += int((overlap_end - overlap_start).total_seconds())
        check_date += timedelta(days=1)

    return max(total_seconds, 0)
