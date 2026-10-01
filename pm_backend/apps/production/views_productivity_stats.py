"""
加工費集計（/overtime/productivity-stats）用の集計API

レーザー・ブレーキ・工程実績の3系統から「作業者×日付」単位の
加工数・加工金額・セッション秒数を集計して返す。
件数の上限は設けない。

GET /production/productivity-stats/?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD
"""
from collections import defaultdict
from datetime import date, datetime

from django.utils.dateparse import parse_date
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from masters.models import Line, Product
from production.models_brake_line_record import BrakeLineRecord
from production.models_laser_actual import LaserActual
from production.models_process_realtime import ProcessRealtimeRecord
from production.models_process_work_session import ProcessWorkSession
from production.services.gantt_planning import LineWorkCalendar
from production.services.process_realtime_common import calculate_effective_work_seconds
from production.views_brake_line import build_brake_sessions

COUNTABLE_END_ACTIONS = ('END', 'PAUSE')


def _normalize_person_name(value):
    return ''.join(str(value or '').split()).lower()


def _iso_second(dt):
    """重複判定キー用に秒単位へ丸めたISO文字列を返す"""
    if not dt:
        return ''
    if isinstance(dt, str):
        return dt[:19]
    return dt.replace(microsecond=0).isoformat()


def _display_user_name(user):
    if not user:
        return ''
    full_name = (getattr(user, 'get_full_name', lambda: '')() or '').strip()
    if full_name:
        return full_name
    return getattr(user, 'username', '') or ''


def _collect_laser_items(date_from, date_to):
    """レーザー実績 → 集計対象行。画面旧ロジックと同じく、設備ごとに START/RESUME → 次の記録で作業秒を算出する。"""
    records = list(
        LaserActual.objects
        .filter(work_date__gte=date_from, work_date__lte=date_to)
        .select_related('created_by', 'updated_by')
        .prefetch_related('details')
        .order_by('-work_date', '-created_at', '-id')
    )

    by_equipment = defaultdict(list)
    for rec in records:
        by_equipment[rec.equipment_code or '__unknown__'].append(rec)

    duration_by_id = {}
    for rows in by_equipment.values():
        pending_start = None
        for rec in sorted(rows, key=lambda r: r.created_at):
            action = str(rec.operator_action or '').upper()
            if action in ('START', 'RESUME'):
                pending_start = rec
            elif pending_start:
                diff = (rec.created_at - pending_start.created_at).total_seconds()
                duration_by_id[rec.id] = max(0, int(round(diff)))
                pending_start = None

    items = []
    for rec in records:
        action = str(rec.operator_action or '').upper()
        if action not in COUNTABLE_END_ACTIONS:
            continue
        duration = duration_by_id.get(rec.id, 0)
        operator = _display_user_name(rec.created_by) or _display_user_name(rec.updated_by) or '—'
        work_date = rec.work_date
        details = [d for d in rec.details.all() if str(d.detail_type or '').upper() == 'COMPONENT']
        details.sort(key=lambda d: (d.display_order, d.id))

        def build(detail):
            return {
                'operator_name': operator,
                'date': str(work_date)[:10],
                'process_code': '',
                'product_code': (detail.product_code if detail else '') or '',
                'qty': float(detail.total_qty or 0) if detail else 0.0,
                'seconds': duration,
                'end_action': action,
                'started_at': '',
                'ended_at': '',
            }

        if details:
            items.extend(build(d) for d in details)
        else:
            items.append(build(None))
    return items


def _collect_brake_items(date_from, date_to):
    records = list(
        BrakeLineRecord.objects
        .filter(plan_date__gte=date_from, plan_date__lte=date_to)
        .select_related('process', 'product', 'line', 'equipment')
        .order_by('line_id', 'process_id', 'product_id', 'equipment_id', 'recorded_at')
    )
    sessions = build_brake_sessions(records)
    sessions.sort(key=lambda s: s.get('started_at') or '', reverse=True)

    items = []
    for s in sessions:
        if s.get('session_type') != 'WORK':
            continue
        items.append({
            'operator_name': s.get('operator_name') or '',
            'date': str(s.get('plan_date') or '')[:10],
            'process_code': s.get('process_code') or '',
            'product_code': s.get('product_code') or '',
            'qty': float(s.get('production_qty') or 0),
            'seconds': int(s.get('effective_work_seconds') or 0),
            'end_action': str(s.get('end_action') or '').upper(),
            'started_at': _iso_second(s.get('started_at')),
            'ended_at': _iso_second(s.get('ended_at')),
        })
    return items


def _collect_process_items(date_from, date_to):
    """工程実績セッション → 集計対象行（連産は子品番へ展開。既存の sessions API の child_only と同じ）"""
    rows = list(
        ProcessWorkSession.objects
        .filter(
            plan_date__gte=date_from,
            plan_date__lte=date_to,
            session_type='WORK',
            end_action__in=COUNTABLE_END_ACTIONS,
        )
        .values(
            'id', 'product_code', 'plan_date', 'started_at', 'ended_at',
            'production_qty', 'operator_name', 'end_action',
            'process__process_code', 'process__line_id',
            'start_record__operator_name', 'end_record__operator_name',
        )
        .order_by('-started_at', '-id')
    )
    if not rows:
        return []

    session_ids = [r['id'] for r in rows]
    session_id_set = set(session_ids)

    # 連産子レコード
    production_rows = list(
        ProcessRealtimeRecord.objects.filter(
            record_type='PRODUCTION',
            event_data__work_session_id__in=session_ids,
        ).values('id', 'product_code', 'qty', 'event_data')
    )
    pause_action_record_ids = set()
    for rec in production_rows:
        event_data = rec.get('event_data') or {}
        if str(event_data.get('operator_action') or '').upper() != 'PAUSE':
            continue
        try:
            pause_action_record_ids.add(int(event_data.get('operator_action_record_id')))
        except (TypeError, ValueError):
            continue

    pause_to_work_session = {}
    if pause_action_record_ids:
        for work_row in ProcessWorkSession.objects.filter(
            end_record_id__in=list(pause_action_record_ids),
            session_type='WORK',
        ).values('end_record_id', 'id'):
            end_record_id = work_row['end_record_id']
            work_session_id = work_row['id']
            prev_id = pause_to_work_session.get(end_record_id)
            if prev_id is None or work_session_id > prev_id:
                pause_to_work_session[end_record_id] = work_session_id

    children_by_session = defaultdict(list)
    for rec in production_rows:
        event_data = rec.get('event_data') or {}
        session_id_raw = event_data.get('work_session_id')
        if not session_id_raw or not event_data.get('coproduct_parent_record_id'):
            continue
        try:
            session_id = int(session_id_raw)
        except (TypeError, ValueError):
            continue
        if str(event_data.get('operator_action') or '').upper() == 'PAUSE':
            try:
                action_record_id = int(event_data.get('operator_action_record_id'))
            except (TypeError, ValueError):
                action_record_id = None
            mapped = pause_to_work_session.get(action_record_id)
            if mapped and mapped in session_id_set:
                session_id = mapped
        children_by_session[session_id].append({
            'source_record_id': rec['id'],
            'product_id': None,
            'product_code': (rec.get('product_code') or '').strip() or None,
            'qty': rec.get('qty') or 0,
        })
    for values in children_by_session.values():
        values.sort(key=lambda x: (x.get('product_code') or '', x.get('source_record_id') or 0))

    # ライン別の作業カレンダ（実働秒計算用）
    line_ids = {r['process__line_id'] for r in rows if r['process__line_id']}
    calendar_by_line = {}
    for line in Line.objects.filter(id__in=line_ids):
        try:
            calendar_by_line[line.id] = LineWorkCalendar(line)
        except Exception:
            calendar_by_line[line.id] = None

    now = datetime.now()
    items = []
    for r in rows:
        operator = (
            (r['end_record__operator_name'] or '').strip()
            or (r['start_record__operator_name'] or '').strip()
            or (r['operator_name'] or '').strip()
        )
        seconds = calculate_effective_work_seconds(
            calendar=calendar_by_line.get(r['process__line_id']),
            started_at=r['started_at'],
            ended_at=r['ended_at'] or now,
        )
        base = {
            'operator_name': operator,
            'date': str(r['plan_date'])[:10],
            'process_code': r['process__process_code'] or '',
            'seconds': int(seconds or 0),
            'end_action': str(r['end_action'] or '').upper(),
            'started_at': _iso_second(r['started_at']),
            'ended_at': _iso_second(r['ended_at']),
        }
        children = children_by_session.get(r['id']) or []
        if children:
            for child in children:
                items.append({**base, 'product_code': child['product_code'] or '', 'qty': float(child['qty'] or 0)})
        else:
            items.append({**base, 'product_code': r['product_code'] or '', 'qty': float(r['production_qty'] or 0)})
    return items


class ProductivityStatsView(APIView):
    """作業者×日付の加工数・加工金額・セッション秒数を返す"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        date_from = parse_date(request.query_params.get('date_from') or '')
        date_to = parse_date(request.query_params.get('date_to') or '')
        if not date_from or not date_to:
            return Response({'detail': 'date_from / date_to は YYYY-MM-DD 形式で必須です。'}, status=400)

        # 取り込み順（レーザー → ブレーキ → 工程実績）で重複判定し、先勝ちとする
        raw_items = (
            _collect_laser_items(date_from, date_to)
            + _collect_brake_items(date_from, date_to)
            + _collect_process_items(date_from, date_to)
        )

        seen = set()
        counted = []
        for it in raw_items:
            if it['qty'] == 0:
                continue
            key = (
                it['date'],
                _normalize_person_name(it['operator_name']),
                it['process_code'],
                it['product_code'].strip(),
                it['end_action'],
                it['qty'],
                it['started_at'],
                it['ended_at'],
            )
            if key in seen:
                continue
            seen.add(key)
            counted.append(it)

        codes = {it['product_code'].strip() for it in counted if it['product_code'].strip()}
        price_by_code = {}
        for code, price in Product.objects.filter(product_code__in=codes).values_list('product_code', 'unit_price'):
            price_by_code[(code or '').strip()] = float(price or 0)

        aggregate = {}
        for it in counted:
            name_raw = str(it['operator_name'] or '').strip()
            name_key = _normalize_person_name(name_raw)
            if not name_key or not it['date']:
                continue
            key = (name_key, it['date'])
            target = aggregate.get(key)
            if target is None:
                target = {'name': name_raw, 'date': it['date'], 'qty_total': 0.0, 'amount_total': 0.0, 'session_seconds': 0}
                aggregate[key] = target
            target['qty_total'] += it['qty']
            target['amount_total'] += it['qty'] * price_by_code.get(it['product_code'].strip(), 0.0)
            target['session_seconds'] += max(it['seconds'], 0)

        return Response({'rows': list(aggregate.values())})
