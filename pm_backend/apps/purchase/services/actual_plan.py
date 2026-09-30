"""仕入計画から登録した実績の残数と、画面取得後の変更を管理する。"""
import hashlib
import json
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

from rest_framework.exceptions import ValidationError

from masters.models import Supplier
from production.models_line_backlog import LineBacklog
from production.models_process_realtime import ProcessRealtimeRecord


def lock_supplier(supplier_id):
    # 登録・訂正・削除で同じ順序のロックを取り、残数判定を直列化する。
    return Supplier.objects.select_for_update().get(pk=supplier_id)


def plan_key(supplier_id, product_id, plan_date):
    try:
        target = date.fromisoformat(str(plan_date).replace('/', '-'))
    except (ValueError, TypeError):
        raise ValidationError('元の計画日が不正です。計画を再読込してください。')
    return {'supplier_id': supplier_id, 'product_id': product_id, 'plan_date': target.isoformat()}


def plan_state(key, *, lock=False):
    plans = LineBacklog.objects.filter(
        line__line_code=Supplier.objects.get(pk=key['supplier_id']).supplier_code,
        product_id=key['product_id'], plan_date=key['plan_date'], sequence_no=1,
    ).order_by('id')
    if lock:
        plans = plans.select_for_update()
    plans = list(plans)
    records = list(ProcessRealtimeRecord.objects.filter(
        record_type='PURCHASE', product_id=key['product_id'], event_data__purchase_plan=key,
    ).order_by('id').values_list('id', 'qty'))
    return _build_state(key, plans, records)


def plan_states(supplier_id, plan_date, plans):
    """一覧は品番ごとの実績クエリを繰り返さず、一括取得する。"""
    plans_by_product = defaultdict(list)
    for plan in plans:
        plans_by_product[plan.product_id].append(plan)
    keys = {pid: plan_key(supplier_id, pid, plan_date) for pid in plans_by_product}
    records_by_product = defaultdict(list)
    records = ProcessRealtimeRecord.objects.filter(
        record_type='PURCHASE', product_id__in=keys,
        event_data__purchase_plan__supplier_id=supplier_id,
        event_data__purchase_plan__plan_date=str(plan_date),
    ).order_by('id').values_list('id', 'qty', 'product_id', 'event_data')
    for pk, qty, pid, event in records:
        if event.get('purchase_plan') == keys[pid]:
            records_by_product[pid].append((pk, qty))
    return {
        pid: _build_state(keys[pid], sorted(rows, key=lambda p: p.id), records_by_product[pid])
        for pid, rows in plans_by_product.items()
    }


def _build_state(key, plans, records):
    planned = sum((Decimal(p.plan_qty) for p in plans), Decimal(0))
    registered = sum((qty for _, qty in records), Decimal(0))
    snapshot = {
        'key': key,
        'plans': [(p.id, p.plan_qty, p.updated_at.isoformat()) for p in plans],
        'records': [(pk, str(qty)) for pk, qty in records],
    }
    token = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()
    return {
        'plan_date': key['plan_date'], 'plan_qty': planned,
        'registered_qty': registered, 'remaining_qty': max(planned - registered, Decimal(0)),
        'plan_token': token,
    }


def touch_plan(key):
    # 実績削除で数量が元に戻っても、過去の送信内容を再受理しない。
    LineBacklog.objects.filter(
        line__line_code=Supplier.objects.get(pk=key['supplier_id']).supplier_code,
        product_id=key['product_id'], plan_date=key['plan_date'], sequence_no=1,
    ).update(updated_at=datetime.now())


def validate_plan_registration(key, qty, token):
    state = plan_state(key, lock=True)
    if not token or token != state['plan_token']:
        raise ValidationError('計画または登録済み実績が変更されています。計画を再読込してください。')
    if state['remaining_qty'] <= 0:
        raise ValidationError('この計画は登録済みです。追加登録できません。')
    if qty > state['remaining_qty']:
        raise ValidationError(f"入荷数が未納残数（{state['remaining_qty']}）を超えています。")


def validate_plan_edit(record, supplier_id, line_id, qty):
    key = (record.event_data or {}).get('purchase_plan')
    if not key:
        return
    if supplier_id != key['supplier_id'] or line_id != (record.event_data or {}).get('line_id'):
        raise ValidationError('計画に紐付く実績の仕入先・ラインは変更できません。削除後に登録し直してください。')
    state = plan_state(key, lock=True)
    # 計画が後から減った場合も、数量を減らす訂正は可能にする。
    if qty > record.qty and state['registered_qty'] - record.qty + qty > state['plan_qty']:
        raise ValidationError('変更後の登録済み数量が計画数を超えます。')
