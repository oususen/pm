import logging
from datetime import date

from django.db import transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from datetime import timedelta

from masters.models import BOM, BOMItem, Calendar, CalendarDay, Product
from orders.utils.calendar_utils import get_business_today
from production.models_line_backlog import LineBacklog
from production.inventory.inventory_calculator import recalculate_inventory_for_line
from production.services.recalc_start_date import resolve_inventory_effective_start_date

from .models import (
    DiscontinuationCase,
    DiscontinuationProduct,
    DiscontinuationPart,
)

logger = logging.getLogger(__name__)

SOURCING_LABELS = {'MAKE': '自社製造', 'BUY': '購買', 'SUBCON': '外注'}


def _next_case_code():
    last = DiscontinuationCase.objects.order_by('-id').first()
    next_id = (last.id + 1) if last else 1
    return f'DC-{next_id:06d}'


def _get_bom_children(product_id):
    """BOMから構成品を取得"""
    today = date.today()
    bom = (
        BOM.objects
        .filter(parent_product_id=product_id, is_active=True)
        .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=today))
        .filter(valid_from__lte=today)
        .order_by('-valid_from')
        .first()
    )
    if not bom:
        return []
    items = BOMItem.objects.filter(bom=bom).select_related(
        'child_product', 'child_product__line', 'supplier'
    )
    return [
        {
            'child_product_id': item.child_product_id,
            'child_product_code': item.child_product.product_code,
            'child_product_name': item.child_product.product_name,
            'quantity': float(item.quantity),
            'sourcing_type': item.sourcing_type,
            'supplier_name': item.supplier.supplier_name if item.supplier else '',
        }
        for item in items
    ]


def _get_backlog_data(part_ids, end_date):
    """構成品の在庫・進度データを取得"""
    if not part_ids or not end_date:
        return {}

    from orders.utils.calendar_utils import get_business_today
    today = get_business_today()

    result = {}
    for part_id in part_ids:
        current_row = (
            LineBacklog.objects
            .filter(product_id=part_id, plan_date__lte=today, sequence_no=0)
            .order_by('-plan_date')
            .first()
        )
        end_row = (
            LineBacklog.objects
            .filter(product_id=part_id, plan_date__lte=end_date, sequence_no=0)
            .order_by('-plan_date')
            .first()
        )

        result[part_id] = {
            'stock_qty': current_row.stock_qty if current_row else None,
            'progress_qty': current_row.progress_qty if current_row else None,
            'planned_progress_qty': current_row.planned_progress_qty if current_row else None,
            'planned_stock_at_end': end_row.planned_stock_qty if end_row else None,
            'progress_at_end': end_row.progress_qty if end_row else None,
            'planned_progress_at_end': end_row.planned_progress_qty if end_row else None,
            'line_code': current_row.line.line_code if current_row and current_row.line_id else None,
        }
    return result


def _shift_business_days_back(target_date, days):
    """営業日ベースで日付を戻す（カレンダー簡易版: 土日スキップ）"""
    if not days or days <= 0:
        return target_date
    calendar = Calendar.objects.first()
    cal_id = calendar.id if calendar else None

    remaining = int(days)
    current = target_date
    while remaining > 0:
        current = current - timedelta(days=1)
        if cal_id:
            cal_day = CalendarDay.objects.filter(
                calendar_id=cal_id, target_date=current
            ).first()
            is_work = cal_day.is_working_day if cal_day else current.weekday() < 5
        else:
            is_work = current.weekday() < 5
        if is_work:
            remaining -= 1
    return current


def _get_sourcing_map(parent_product_id, child_product_ids):
    """親製品のBOMから子製品の調達区分・調達先・LTを取得"""
    today = date.today()
    bom = (
        BOM.objects
        .filter(parent_product_id=parent_product_id, is_active=True)
        .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=today))
        .filter(valid_from__lte=today)
        .order_by('-valid_from')
        .first()
    )
    if not bom:
        return {}
    items = BOMItem.objects.filter(
        bom=bom, child_product_id__in=child_product_ids
    ).select_related('supplier')
    return {
        item.child_product_id: {
            'sourcing_type': item.sourcing_type,
            'supplier_name': item.supplier.supplier_name if item.supplier else '',
            'lead_time_days': item.lead_time_days or 0,
        }
        for item in items
    }


def _get_shared_parents(product_id, disc_product_ids):
    """構成品が打ち切り対象以外の親製品にも使われているか判定"""
    today = date.today()
    bom_items = BOMItem.objects.filter(
        child_product_id=product_id,
        bom__is_active=True,
    ).filter(
        Q(bom__valid_to__isnull=True) | Q(bom__valid_to__gte=today),
        bom__valid_from__lte=today,
    ).select_related('bom__parent_product')

    shared = []
    for item in bom_items:
        parent = item.bom.parent_product
        if parent.id not in disc_product_ids:
            shared.append({
                'product_id': parent.id,
                'product_code': parent.product_code,
                'product_name': parent.product_name,
            })
    return shared


class DiscontinuationCaseListCreateView(APIView):
    """打ち切り案件 一覧/登録"""

    def get(self, request):
        cases = DiscontinuationCase.objects.prefetch_related(
            'products__product',
            'products__parts__part',
        ).order_by('-created_at')

        all_disc_product_ids = set(
            DiscontinuationProduct.objects
            .values_list('product_id', flat=True)
        )

        all_part_ids = set()
        end_date_map = {}
        parent_child_map = {}
        for case in cases:
            for dp in case.products.all():
                child_ids = set()
                for part in dp.parts.all():
                    all_part_ids.add(part.part_id)
                    child_ids.add(part.part_id)
                    ed = dp.end_date or case.end_date
                    if ed:
                        end_date_map[part.part_id] = ed
                parent_child_map[dp.product_id] = child_ids

        backlog_map = _get_backlog_data(all_part_ids, max(end_date_map.values()) if end_date_map else None)

        sourcing_maps = {}
        for parent_id, child_ids in parent_child_map.items():
            sourcing_maps[parent_id] = _get_sourcing_map(parent_id, child_ids)

        result = []
        for case in cases:
            products_data = []
            for dp in case.products.all():
                s_map = sourcing_maps.get(dp.product_id, {})
                dp_end = dp.end_date or case.end_date

                part_lt_dates = {}
                for part in dp.parts.all():
                    info = s_map.get(part.part_id, {})
                    lt_days = info.get('lead_time_days', 0) if info else 0
                    if dp_end and lt_days > 0:
                        part_lt_dates[part.part_id] = _shift_business_days_back(dp_end, lt_days)
                    else:
                        part_lt_dates[part.part_id] = dp_end

                dp_part_ids = [part.part_id for part in dp.parts.all()]
                dp_backlog = {}
                if dp_end and dp_part_ids:
                    dp_backlog = _get_backlog_data(dp_part_ids, dp_end)

                parts_data = []
                for part in dp.parts.all():
                    shared_parents = _get_shared_parents(
                        part.part_id, all_disc_product_ids
                    )
                    bl = dp_backlog.get(part.part_id, backlog_map.get(part.part_id, {}))
                    info = s_map.get(part.part_id, {})
                    sourcing = info.get('sourcing_type', '') if info else ''
                    supplier_name = info.get('supplier_name', '') if info else ''
                    lt_days = info.get('lead_time_days', 0) if info else 0
                    part_end = part_lt_dates.get(part.part_id)
                    planned_stock = bl.get('planned_stock_at_end')
                    planned_progress = bl.get('planned_progress_at_end')
                    is_shared = len(shared_parents) > 0

                    def _judge(val):
                        if val is None:
                            return 'no_data'
                        if val > 0 and not is_shared:
                            return 'excess'
                        if val > 0 and is_shared:
                            return 'shared_check'
                        return 'ok'

                    judgment_stock = _judge(planned_stock)
                    judgment_progress = _judge(planned_progress)

                    parts_data.append({
                        'id': part.id,
                        'part_id': part.part_id,
                        'part_code': part.part.product_code,
                        'part_name': part.part.product_name,
                        'note': part.note,
                        'sourcing_type': sourcing,
                        'sourcing_label': SOURCING_LABELS.get(sourcing, ''),
                        'supplier_name': supplier_name,
                        'lead_time_days': lt_days,
                        'part_end_date': part_end.isoformat() if part_end else None,
                        'stock_qty': bl.get('stock_qty'),
                        'progress_qty': bl.get('progress_qty'),
                        'planned_progress_qty': bl.get('planned_progress_qty'),
                        'planned_stock_at_end': planned_stock,
                        'progress_at_end': bl.get('progress_at_end'),
                        'planned_progress_at_end': bl.get('planned_progress_at_end'),
                        'line_code': bl.get('line_code'),
                        'shared_parents': shared_parents,
                        'judgment_stock': judgment_stock,
                        'judgment_progress': judgment_progress,
                    })

                products_data.append({
                    'id': dp.id,
                    'product_id': dp.product_id,
                    'product_code': dp.product.product_code,
                    'product_name': dp.product.product_name,
                    'end_date': dp.end_date.isoformat() if dp.end_date else None,
                    'note': dp.note,
                    'parts': parts_data,
                })

            result.append({
                'id': case.id,
                'case_code': case.case_code,
                'title': case.title,
                'end_date': case.end_date.isoformat() if case.end_date else None,
                'note': case.note,
                'products': products_data,
                'created_at': case.created_at.isoformat(),
            })

        return Response(result)

    @transaction.atomic
    def post(self, request):
        data = request.data
        title = data.get('title', '').strip()
        if not title:
            return Response({'detail': '案件名は必須です'}, status=status.HTTP_400_BAD_REQUEST)

        end_date = data.get('end_date')
        case = DiscontinuationCase.objects.create(
            case_code=_next_case_code(),
            title=title,
            end_date=end_date,
            note=data.get('note', ''),
        )

        products = data.get('products', [])
        for p in products:
            product_id = p.get('product_id')
            if not product_id:
                continue
            dp = DiscontinuationProduct.objects.create(
                case=case,
                product_id=product_id,
                end_date=p.get('end_date') or end_date,
                note=p.get('note', ''),
            )
            bom_children = _get_bom_children(product_id)
            for child in bom_children:
                DiscontinuationPart.objects.create(
                    disc_product=dp,
                    part_id=child['child_product_id'],
                )

        return Response({'id': case.id, 'case_code': case.case_code}, status=status.HTTP_201_CREATED)


class DiscontinuationCaseDetailView(APIView):
    """打ち切り案件 更新/削除"""

    def put(self, request, pk):
        case = DiscontinuationCase.objects.filter(pk=pk).first()
        if not case:
            return Response({'detail': 'not found'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        if 'title' in data:
            case.title = data['title']
        if 'end_date' in data:
            case.end_date = data['end_date']
        if 'note' in data:
            case.note = data['note']
        case.save()
        return Response({'detail': '保存しました'})

    def delete(self, request, pk):
        case = DiscontinuationCase.objects.filter(pk=pk).first()
        if not case:
            return Response({'detail': 'not found'}, status=status.HTTP_404_NOT_FOUND)
        case.delete()
        return Response({'detail': '削除しました'})


class DiscontinuationProductAddView(APIView):
    """打ち切り完成品 追加"""

    @transaction.atomic
    def post(self, request, case_id):
        case = DiscontinuationCase.objects.filter(pk=case_id).first()
        if not case:
            return Response({'detail': 'not found'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        product_id = data.get('product_id')
        if not product_id:
            return Response({'detail': '完成品は必須です'}, status=status.HTTP_400_BAD_REQUEST)

        dp = DiscontinuationProduct.objects.create(
            case=case,
            product_id=product_id,
            end_date=data.get('end_date') or case.end_date,
            note=data.get('note', ''),
        )
        bom_children = _get_bom_children(product_id)
        for child in bom_children:
            DiscontinuationPart.objects.create(
                disc_product=dp,
                part_id=child['child_product_id'],
            )
        return Response({'id': dp.id}, status=status.HTTP_201_CREATED)


class DiscontinuationProductDetailView(APIView):
    """打ち切り完成品 更新/削除"""

    def put(self, request, pk):
        dp = DiscontinuationProduct.objects.filter(pk=pk).first()
        if not dp:
            return Response({'detail': 'not found'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        if 'end_date' in data:
            dp.end_date = data['end_date']
        if 'note' in data:
            dp.note = data['note']
        dp.save()
        return Response({'detail': '保存しました'})

    def delete(self, request, pk):
        dp = DiscontinuationProduct.objects.filter(pk=pk).first()
        if not dp:
            return Response({'detail': 'not found'}, status=status.HTTP_404_NOT_FOUND)
        dp.delete()
        return Response({'detail': '削除しました'})


class DiscontinuationPartAddView(APIView):
    """打ち切り構成品 手動追加"""

    def post(self, request, disc_product_id):
        dp = DiscontinuationProduct.objects.filter(pk=disc_product_id).first()
        if not dp:
            return Response({'detail': 'not found'}, status=status.HTTP_404_NOT_FOUND)

        part_id = request.data.get('part_id')
        if not part_id:
            return Response({'detail': '構成品は必須です'}, status=status.HTTP_400_BAD_REQUEST)

        part = DiscontinuationPart.objects.create(
            disc_product=dp,
            part_id=part_id,
            note=request.data.get('note', ''),
        )
        return Response({'id': part.id}, status=status.HTTP_201_CREATED)


class DiscontinuationPartDetailView(APIView):
    """打ち切り構成品 削除"""

    def delete(self, request, pk):
        part = DiscontinuationPart.objects.filter(pk=pk).first()
        if not part:
            return Response({'detail': 'not found'}, status=status.HTTP_404_NOT_FOUND)
        part.delete()
        return Response({'detail': '削除しました'})


def _collect_all_descendants(product_id, visited=None):
    """BOMを再帰的に展開して子・孫すべてのproduct_idを収集"""
    if visited is None:
        visited = set()
    if product_id in visited:
        return visited
    visited.add(product_id)

    today = date.today()
    bom = (
        BOM.objects
        .filter(parent_product_id=product_id, is_active=True)
        .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=today))
        .filter(valid_from__lte=today)
        .order_by('-valid_from')
        .first()
    )
    if not bom:
        return visited

    child_ids = list(
        BOMItem.objects
        .filter(bom=bom)
        .values_list('child_product_id', flat=True)
    )
    for cid in child_ids:
        _collect_all_descendants(cid, visited)
    return visited


class DiscontinuationProductRecalculateView(APIView):
    """打ち切り完成品の構成品（子・孫）を再計算"""

    def post(self, request, pk):
        dp = (
            DiscontinuationProduct.objects
            .select_related('case', 'product')
            .filter(pk=pk)
            .first()
        )
        if not dp:
            return Response({'detail': 'not found'}, status=status.HTTP_404_NOT_FOUND)

        end_date = dp.end_date or dp.case.end_date
        today = get_business_today()
        if not end_date:
            return Response({'detail': '打ち切り日が設定されていません'}, status=status.HTTP_400_BAD_REQUEST)
        if end_date < today:
            end_date = today

        all_ids = _collect_all_descendants(dp.product_id)
        all_ids.discard(dp.product_id)
        if not all_ids:
            return Response({'detail': '構成品が見つかりません'}, status=status.HTTP_404_NOT_FOUND)

        line_products_map = {}
        for pid in all_ids:
            line_ids = set()
            prod = Product.objects.filter(pk=pid).select_related('line').first()
            if prod and prod.line_id:
                line_ids.add(prod.line_id)
            backlog_line_ids = (
                LineBacklog.objects
                .filter(product_id=pid, plan_date__gte=today, plan_date__lte=end_date)
                .values_list('line_id', flat=True)
                .distinct()
            )
            line_ids.update([lid for lid in backlog_line_ids if lid])
            for lid in line_ids:
                line_products_map.setdefault(lid, set()).add(pid)

        if not line_products_map:
            return Response({'detail': '対象ラインが見つかりません'}, status=status.HTTP_404_NOT_FOUND)

        recalculated_lines = 0
        recalculated_pairs = 0
        for line_id in sorted(line_products_map.keys()):
            pids = sorted(line_products_map[line_id])
            effective_start = resolve_inventory_effective_start_date(
                line_id, today, end_date, product_ids=pids,
            )
            recalculate_inventory_for_line(
                line_id, effective_start, end_date,
                include_progress=True,
                line_final_only=False,
                product_ids=pids,
            )
            recalculated_pairs += len(pids)
            recalculated_lines += 1

        return Response({
            'detail': f'{dp.product.product_code} の構成品を再計算しました',
            'line_count': recalculated_lines,
            'part_count': len(all_ids),
            'target_pairs': recalculated_pairs,
            'end_date': str(end_date),
        })


class DiscontinuationBomLookupView(APIView):
    """完成品のBOM構成品を検索"""

    def get(self, request):
        product_id = request.query_params.get('product_id')
        if not product_id:
            return Response({'detail': 'product_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        children = _get_bom_children(int(product_id))
        return Response(children)
