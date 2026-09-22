"""LinePlanViewSet の変更系サービス"""
from datetime import date, datetime
from decimal import Decimal

from django.db import transaction
from rest_framework import status
from rest_framework.response import Response

from masters.models import Line, Product
from production.models_line_backlog import LineBacklog
from production.models_line_gantt_plan import LineGanttPlan
from production.models_line_plan import LinePlan
from production.models_plan_change_log import ProductionPlanChangeLog


def bulk_delete(viewset, request, **deps):
    """
    選択ライン・期間のLinePlan/LineGanttPlan/LineBacklog計画行を一括削除する
    期待payload: { line_id, start_date, end_date }
    """
    line_id = request.data.get('line_id')
    start_date_raw = request.data.get('start_date')
    end_date_raw = request.data.get('end_date')

    if not line_id:
        return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not start_date_raw or not end_date_raw:
        return Response({'detail': 'start_date and end_date are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        start_date = datetime.strptime(str(start_date_raw), '%Y-%m-%d').date()
        end_date = datetime.strptime(str(end_date_raw), '%Y-%m-%d').date()
    except Exception:
        return Response({'detail': 'start_date/end_date must be YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

    if start_date > end_date:
        return Response({'detail': 'start_date must be <= end_date'}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        deleted_plan_result = LinePlan.objects.filter(
            line_id=line_id,
            plan_date__gte=start_date,
            plan_date__lte=end_date,
        ).delete()
        deleted_gantt_result = LineGanttPlan.objects.filter(
            line_id=line_id,
            plan_date__gte=start_date,
            plan_date__lte=end_date,
        ).exclude(plan_id__startswith='SINGLEPROC_').delete()
        deleted_backlog_result = LineBacklog.objects.filter(
            line_id=line_id,
            plan_date__gte=start_date,
            plan_date__lte=end_date,
        ).exclude(sequence_no=0).exclude(plan_id__startswith='SINGLEPROC_').delete()

    deleted_plan = deleted_plan_result[0] if deleted_plan_result else 0
    deleted_gantt = deleted_gantt_result[0] if deleted_gantt_result else 0
    deleted_backlog = deleted_backlog_result[0] if deleted_backlog_result else 0

    return Response({
        'deleted_plan': deleted_plan,
        'deleted_gantt': deleted_gantt,
        'deleted_backlog': deleted_backlog,
        'line_id': line_id,
        'start_date': str(start_date),
        'end_date': str(end_date),
    })


def save(viewset, request, **deps):
    is_floor_shipping_delivery_line = deps.get('is_floor_shipping_delivery_line')
    """
    ユーザーが入力した計画データをLinePlanに保存する
    期待payload: { line_id, items: [{product_id, process_id, plan_date, plan_qty?, sequence_no?}] }

    保存前に、該当ライン・日付・製品のすべてのLinePlanとLineGanttPlanを削除してから新規作成する
    """
    line_id = request.data.get('line_id')
    items = request.data.get('items', [])
    replace_dates = request.data.get('replace_dates', [])
    replace_product_ids = request.data.get('replace_product_ids', [])
    if not line_id:
        return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not isinstance(items, list):
        return Response({'detail': 'items must be a list'}, status=status.HTTP_400_BAD_REQUEST)
    if replace_dates and not isinstance(replace_dates, list):
        return Response({'detail': 'replace_dates must be a list'}, status=status.HTTP_400_BAD_REQUEST)
    if replace_product_ids and not isinstance(replace_product_ids, list):
        return Response({'detail': 'replace_product_ids must be a list'}, status=status.HTTP_400_BAD_REQUEST)
    if not items and not replace_dates:
        return Response({'detail': 'items or replace_dates is required'}, status=status.HTTP_400_BAD_REQUEST)

    line_obj = Line.objects.filter(id=line_id, is_active=True).only('id', 'line_code', 'line_name').first()
    if not line_obj:
        return Response({'detail': 'line not found'}, status=status.HTTP_400_BAD_REQUEST)

    raw_reason = request.data.get('change_reason')
    change_reason = None
    if raw_reason is not None:
        change_reason = str(raw_reason).strip()
        if not change_reason:
            return Response({'detail': 'change_reason is required'}, status=status.HTTP_400_BAD_REQUEST)

    def parse_plan_date(raw_date):
        if isinstance(raw_date, str):
            return datetime.strptime(raw_date, '%Y-%m-%d').date()
        return raw_date

    affected_dates = set()
    affected_products = set()
    floor_shipping_plan_counts = {}
    for raw_date in replace_dates:
        try:
            affected_dates.add(parse_plan_date(raw_date))
        except Exception:
            continue
    for raw_product_id in replace_product_ids:
        try:
            product_id = int(raw_product_id)
        except (TypeError, ValueError):
            continue
        if product_id > 0:
            affected_products.add(product_id)
    for it in items:
        plan_date = it.get('plan_date')
        product_id = it.get('product_id')
        if plan_date and product_id:
            plan_date_obj = parse_plan_date(plan_date)
            affected_dates.add(plan_date_obj)
            affected_products.add(product_id)
            if is_floor_shipping_delivery_line(line_obj):
                try:
                    plan_qty_value = Decimal(str(it.get('plan_qty') or 0))
                except Exception:
                    plan_qty_value = Decimal('0')
                if plan_qty_value > 0:
                    count_key = (product_id, plan_date_obj)
                    floor_shipping_plan_counts[count_key] = floor_shipping_plan_counts.get(count_key, 0) + 1

    if is_floor_shipping_delivery_line(line_obj):
        invalid_keys = [
            (product_id, plan_date_obj, count)
            for (product_id, plan_date_obj), count in floor_shipping_plan_counts.items()
            if count > 2
        ]
        if invalid_keys:
            product_ids = {product_id for product_id, _, _ in invalid_keys}
            product_code_map = {
                product.id: product.product_code
                for product in Product.objects.filter(id__in=product_ids).only('id', 'product_code')
            }
            first_product_id, first_plan_date, first_count = invalid_keys[0]
            product_label = product_code_map.get(first_product_id, str(first_product_id))
            return Response(
                {'detail': f'フロア配送は同一日・同一品番で2件までです: {product_label} {first_plan_date} ({first_count}件)'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    created = 0
    deleted_plan = 0
    deleted_gantt = 0
    deleted_backlog = 0
    skipped = []
    product_cache = {}
    next_seq_cache = {}
    existing_plan_map = {}
    change_user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None

    def get_next_sequence(plan_date_obj):
        """自動採番: 日付ごとに連番を生成"""
        cache_key = (line_id, plan_date_obj)
        if cache_key not in next_seq_cache:
            next_seq_cache[cache_key] = 1
        next_seq = next_seq_cache[cache_key]
        next_seq_cache[cache_key] = next_seq + 1
        return next_seq

    def record_change(before_qty, after_qty, plan_date_obj, product_id, process_id, line_id_value, sequence_no_value, plan_id_value):
        if not change_reason:
            return
        if before_qty == after_qty:
            return
        ProductionPlanChangeLog.objects.create(
            plan_date=plan_date_obj,
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

    indexed_items = list(enumerate(items))

    def to_int_or_none(value):
        if value is None or value == '':
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def item_sort_key(indexed_item):
        original_idx, item = indexed_item
        plan_date_raw = item.get('plan_date')
        try:
            plan_date_obj = parse_plan_date(plan_date_raw)
        except Exception:
            plan_date_obj = date.max
        display_order = to_int_or_none(item.get('display_order'))
        if display_order is None:
            display_order = 10 ** 9
        return (plan_date_obj, display_order, original_idx)

    sorted_items = sorted(indexed_items, key=item_sort_key)

    with transaction.atomic():
        # 保存対象の完成品計画を置換する前に、旧plan_idを控えておく。
        # 同一plan_idは工程展開後の構成部品行にも引き継がれるため、
        # 数量を0/空欄にした場合でも残骸を残さず削除するために使用する。
        replacement_plan_ids = set()
        if affected_dates and affected_products:
            replacement_plan_ids = set(
                LinePlan.objects.filter(
                    line_id=line_id,
                    plan_date__in=affected_dates,
                    product_id__in=affected_products,
                ).exclude(plan_id__isnull=True).exclude(plan_id='').values_list('plan_id', flat=True)
            )

            # 過去に完成品行だけが削除され、展開行だけが残っているケースも回収する。
            # plan_idは「完成品コード_日付_数量_順番」なので、画面表示製品のコードを
            # 先頭に持つ行を対象にすれば、構成部品側に残った旧計画も特定できる。
            from django.db.models import Q
            product_codes = list(
                Product.objects.filter(id__in=affected_products).values_list('product_code', flat=True)
            )
            plan_id_prefix_q = Q()
            for product_code in product_codes:
                normalized_code = str(product_code or '').strip()
                if normalized_code:
                    plan_id_prefix_q |= Q(plan_id__startswith=f'{normalized_code}_')
            if plan_id_prefix_q:
                replacement_plan_ids.update(
                    LineBacklog.objects.filter(
                        line_id=line_id,
                        plan_date__in=affected_dates,
                        sequence_no__gt=0,
                    ).filter(plan_id_prefix_q).exclude(plan_id__startswith='SINGLEPROC_').values_list('plan_id', flat=True)
                )

        if change_reason and affected_dates and affected_products:
            existing_plans = LinePlan.objects.filter(
                line_id=line_id,
                plan_date__in=affected_dates,
                product_id__in=affected_products,
            )
            for plan in existing_plans:
                key = (plan.product_id, plan.process_id, plan.plan_date, plan.sequence_no)
                existing_plan_map[key] = plan

        if affected_dates and affected_products:
            deleted_plan_result = LinePlan.objects.filter(
                line_id=line_id,
                plan_date__in=affected_dates,
                product_id__in=affected_products,
            ).delete()
            deleted_plan = deleted_plan_result[0] if deleted_plan_result else 0

            # 画面表示製品の旧計画から展開された構成部品・全工程行も削除する。
            # line_idで限定し、別ラインの同一plan_idを削除しない。
            if replacement_plan_ids:
                deleted_gantt_by_plan_id = LineGanttPlan.objects.filter(
                    line_id=line_id,
                    plan_id__in=replacement_plan_ids,
                ).exclude(plan_id__startswith='SINGLEPROC_').delete()
                deleted_gantt += deleted_gantt_by_plan_id[0] if deleted_gantt_by_plan_id else 0

                deleted_backlog_by_plan_id = LineBacklog.objects.filter(
                    line_id=line_id,
                    plan_id__in=replacement_plan_ids,
                ).exclude(plan_id__startswith='SINGLEPROC_').delete()
                deleted_backlog += deleted_backlog_by_plan_id[0] if deleted_backlog_by_plan_id else 0

            # plan_idを持たない旧行も従来どおり対象製品・期間で削除する。
            deleted_gantt_result = LineGanttPlan.objects.filter(
                line_id=line_id,
                plan_date__in=affected_dates,
                product_id__in=affected_products,
            ).exclude(plan_id__startswith='SINGLEPROC_').delete()
            deleted_gantt += deleted_gantt_result[0] if deleted_gantt_result else 0

            deleted_backlog_result = LineBacklog.objects.filter(
                line_id=line_id,
                plan_date__in=affected_dates,
                product_id__in=affected_products,
                sequence_no__gt=0,
            ).exclude(plan_id__startswith='SINGLEPROC_').delete()
            deleted_backlog += deleted_backlog_result[0] if deleted_backlog_result else 0

        for _original_idx, it in sorted_items:
            try:
                product_id = it.get('product_id')
                process_id = it.get('process_id')
                plan_date = it.get('plan_date')
                if not product_id or not process_id or not plan_date:
                    skipped.append({'item': it, 'reason': 'product_id/process_id/plan_date required'})
                    continue

                plan_qty_value = Decimal(str(it.get('plan_qty') or 0))
                plan_date_obj = parse_plan_date(plan_date)

                seq_in = it.get('sequence_no')
                if seq_in in (None, '', 0):
                    if plan_qty_value > 0:
                        sequence_no = get_next_sequence(plan_date_obj)
                    else:
                        skipped.append({'item': it, 'reason': 'sequence_no required for zero quantity'})
                        continue
                else:
                    try:
                        sequence_no = int(seq_in)
                    except (TypeError, ValueError):
                        skipped.append({'item': it, 'reason': 'invalid sequence_no'})
                        continue

                existing_key = (product_id, process_id, plan_date_obj, sequence_no)
                existing_plan = existing_plan_map.pop(existing_key, None)
                before_qty = int(existing_plan.plan_qty or 0) if existing_plan else 0
                before_plan_id = existing_plan.plan_id if existing_plan else None

                if plan_qty_value <= 0:
                    record_change(
                        before_qty,
                        0,
                        plan_date_obj,
                        product_id,
                        process_id,
                        line_id,
                        sequence_no,
                        before_plan_id,
                    )
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

                qty_label = str(plan_qty_value).rstrip('0').rstrip('.')
                if '.' in qty_label:
                    qty_label = qty_label.replace('.', 'p')

                plan_id = f"{product_code}_{plan_date_obj.strftime('%Y%m%d')}_{qty_label}_{sequence_no}"

                LinePlan.objects.create(
                    plan_date=plan_date_obj,
                    process_id=process_id,
                    product_id=product_id,
                    line_id=line_id,
                    plan_qty=int(plan_qty_value),
                    plan_id=plan_id,
                    sequence_no=sequence_no,
                )
                LineBacklog.objects.create(
                    plan_date=plan_date_obj,
                    process_id=process_id,
                    product_id=product_id,
                    line_id=line_id,
                    plan_qty=int(plan_qty_value),
                    plan_id=plan_id,
                    sequence_no=sequence_no,
                )
                created += 1
                record_change(
                    before_qty,
                    int(plan_qty_value),
                    plan_date_obj,
                    product_id,
                    process_id,
                    line_id,
                    sequence_no,
                    plan_id,
                )
            except Exception as e:
                return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if change_reason:
            for plan in existing_plan_map.values():
                record_change(
                    int(plan.plan_qty or 0),
                    0,
                    plan.plan_date,
                    plan.product_id,
                    plan.process_id,
                    line_id,
                    plan.sequence_no,
                    plan.plan_id,
                )

    return Response({
        'created': created,
        'deleted_plan': deleted_plan,
        'deleted_gantt': deleted_gantt,
        'deleted_backlog': deleted_backlog,
        'skipped': skipped,
    })
