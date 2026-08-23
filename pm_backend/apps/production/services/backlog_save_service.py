"""LineBacklogViewSet の保存系サービス"""
from datetime import datetime
from decimal import Decimal

from rest_framework import status
from rest_framework.response import Response

from masters.models import Product
from production.models_line_backlog import LineBacklog
from production.models_production import ProductionOrder


def save(viewset, request, **deps):
    resolve_effective_routing = deps.get('resolve_effective_routing')
    """
    ユーザーが入力した計画データをLineBacklogに保存する
    期待payload: { line_id, items: [{product_id, process_id, plan_date, plan_qty?, actual_qty?, stock_qty?, planned_stock_qty?, adjust_qty?, sequence_no?}] }

    plan_id ロジック:
    - plan_id = 製品コード_日付_数量_順番
    - 数量が変更されるとplan_idが変わるため、古いplan_idのレコードを削除
    - plan_qty=0の場合もplan_idに紐づくレコードを削除
    """
    line_id = request.data.get('line_id')
    items = request.data.get('items', [])
    if not line_id:
        return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not isinstance(items, list) or not items:
        return Response({'detail': 'items is required'}, status=status.HTTP_400_BAD_REQUEST)

    created = 0
    updated = 0
    deleted = 0
    skipped = []
    change_reason = request.data.get('change_reason')
    if isinstance(change_reason, str):
        change_reason = change_reason.strip()
    if not change_reason:
        change_reason = None

    product_cache = {}
    plan_date_cache = {}
    change_user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None

    def parse_plan_date(raw_date):
        if raw_date in plan_date_cache:
            return plan_date_cache[raw_date]
        if isinstance(raw_date, str):
            parsed = datetime.strptime(raw_date, '%Y-%m-%d').date()
        else:
            parsed = raw_date
        plan_date_cache[raw_date] = parsed
        return parsed

    def record_change(plan_date_value, product_id, process_id, line_id_value, before_qty, after_qty, plan_id_value, sequence_no_value):
        if not change_reason:
            return
        if before_qty == after_qty:
            return
        from purchase.models import PurchasePlanChangeLog

        PurchasePlanChangeLog.objects.create(
            plan_date=plan_date_value,
            product_id=product_id,
            process_id=process_id,
            line_id=line_id_value,
            sequence_no=sequence_no_value,
            plan_id=plan_id_value,
            before_qty=before_qty,
            after_qty=after_qty,
            reason=change_reason,
            changed_by=change_user,
        )

    for it in items:
        try:
            product_id = it.get('product_id')
            process_id = it.get('process_id')
            plan_date = it.get('plan_date')
            if not product_id or not process_id or not plan_date:
                skipped.append({'item': it, 'reason': 'product_id/process_id/plan_date required'})
                continue

            if product_id not in product_cache:
                try:
                    product = Product.objects.get(id=product_id)
                    product_cache[product_id] = product
                except Product.DoesNotExist:
                    skipped.append({'item': it, 'reason': 'product not found'})
                    continue
            product = product_cache[product_id]
            product_code = product.product_code

            plan_qty_provided = 'plan_qty' in it
            plan_qty_value = None
            existing_plan_qty = 0
            existing_plan_id = None
            existing_sequence_no = None
            if plan_qty_provided:
                plan_qty_value = Decimal(str(it['plan_qty'] or 0))
                if plan_qty_value == 0:
                    seq_for_zero = it.get('sequence_no') if it.get('sequence_no') is not None else 0
                    existing = LineBacklog.objects.filter(
                        plan_date=plan_date,
                        process_id=process_id,
                        product_id=product_id,
                        line_id=line_id,
                        sequence_no=seq_for_zero,
                    ).first()

                    if existing and existing.plan_id:
                        existing_plan_qty = int(existing.plan_qty or 0)
                        existing_plan_id = existing.plan_id
                        existing_sequence_no = existing.sequence_no
                        ProductionOrder.objects.filter(order_no=existing.plan_id).delete()
                        deleted_count = LineBacklog.objects.filter(plan_id=existing.plan_id).delete()[0]
                        deleted += deleted_count
                        record_change(
                            parse_plan_date(plan_date),
                            product_id,
                            process_id,
                            line_id,
                            existing_plan_qty,
                            0,
                            existing_plan_id,
                            existing_sequence_no,
                        )
                        continue
                    elif existing:
                        existing_plan_qty = int(existing.plan_qty or 0)
                        existing_plan_id = existing.plan_id
                        existing_sequence_no = existing.sequence_no

                        def resolve_qty(field_name):
                            if field_name in it:
                                return Decimal(str(it[field_name] or 0))
                            return Decimal(str(getattr(existing, field_name, 0) or 0))

                        actual_qty = resolve_qty('actual_qty')
                        stock_qty = resolve_qty('stock_qty')
                        planned_stock_qty = resolve_qty('planned_stock_qty')
                        adjust_qty = resolve_qty('adjust_qty')
                        order_qty = Decimal(str(existing.order_qty or 0))
                        demand_qty_plan = Decimal(str(existing.demand_qty_plan or 0))
                        seq_in = it.get('sequence_no', existing.sequence_no)
                        seq_val = 0 if seq_in is None else seq_in

                        if (
                            actual_qty == 0
                            and stock_qty == 0
                            and planned_stock_qty == 0
                            and adjust_qty == 0
                            and order_qty == 0
                            and demand_qty_plan == 0
                            and seq_val in (0, None, '')
                        ):
                            existing.delete()
                            deleted += 1
                            record_change(
                                parse_plan_date(plan_date),
                                product_id,
                                process_id,
                                line_id,
                                existing_plan_qty,
                                0,
                                existing_plan_id,
                                existing_sequence_no,
                            )
                            continue

            sequence_no = it.get('sequence_no')
            if sequence_no is None:
                sequence_no = 0

            existing = LineBacklog.objects.filter(
                plan_date=plan_date,
                process_id=process_id,
                product_id=product_id,
                line_id=line_id,
                sequence_no=sequence_no,
            ).first()
            if existing:
                existing_plan_qty = int(existing.plan_qty or 0)
                existing_plan_id = existing.plan_id
                existing_sequence_no = existing.sequence_no

            new_plan_id = None
            plan_date_obj = None
            if plan_qty_provided:
                plan_date_obj = parse_plan_date(plan_date)
                qty_label = str(plan_qty_value).rstrip('0').rstrip('.')
                if '.' in qty_label:
                    qty_label = qty_label.replace('.', 'p')

                new_plan_id = f"{product_code}_{plan_date_obj.strftime('%Y%m%d')}_{qty_label}_{sequence_no}"

                if existing and existing.plan_id and existing.plan_id != new_plan_id:
                    old_plan_id = existing.plan_id
                    LineBacklog.objects.filter(plan_id=old_plan_id).delete()
                    ProductionOrder.objects.filter(order_no=old_plan_id).delete()
                    existing = None

            defaults = {}
            if plan_qty_provided:
                defaults['plan_id'] = new_plan_id
                defaults['plan_qty'] = plan_qty_value
            if 'actual_qty' in it:
                defaults['actual_qty'] = Decimal(str(it['actual_qty']))
            if 'stock_qty' in it:
                defaults['stock_qty'] = Decimal(str(it['stock_qty']))
            if 'planned_stock_qty' in it:
                defaults['planned_stock_qty'] = Decimal(str(it['planned_stock_qty']))
            if 'adjust_qty' in it:
                defaults['adjust_qty'] = Decimal(str(it['adjust_qty']))
            if 'sequence_no' in it:
                defaults['sequence_no'] = sequence_no

            defaults.pop('sequence_no', None)
            obj, is_created = LineBacklog.objects.update_or_create(
                plan_date=plan_date,
                process_id=process_id,
                product_id=product_id,
                line_id=line_id,
                sequence_no=sequence_no,
                defaults=defaults,
            )
            if is_created:
                created += 1
            else:
                updated += 1

            if plan_qty_provided and plan_qty_value is not None:
                after_qty = int(plan_qty_value)
                record_change(
                    plan_date_obj or parse_plan_date(plan_date),
                    product_id,
                    process_id,
                    line_id,
                    existing_plan_qty,
                    after_qty,
                    new_plan_id or existing_plan_id,
                    sequence_no if 'sequence_no' in it or sequence_no is not None else existing_sequence_no,
                )

            if plan_qty_provided and plan_qty_value is not None and plan_qty_value > 0 and new_plan_id:
                routing = resolve_effective_routing(product_id, plan_date_obj)
                ProductionOrder.objects.update_or_create(
                    order_no=new_plan_id,
                    defaults={
                        'product_id': product_id,
                        'routing_id': routing.id if routing else None,
                        'line_id': line_id,
                        'order_qty': plan_qty_value,
                        'scheduled_start_date': plan_date_obj,
                        'scheduled_end_date': plan_date_obj,
                        'priority': sequence_no or 0,
                    },
                )
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({'created': created, 'updated': updated, 'deleted': deleted, 'skipped': skipped})
