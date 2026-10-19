from collections import defaultdict
from datetime import date, timedelta

from accounts.models import Department, UnitLineMapping
from django.db.models import Q
from masters.models import Product
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models_line_backlog import LineBacklog
from .models import LineDemand
from .models_progress_monitor import ProgressMonitorTarget
from .serializers_progress_monitor import ProgressMonitorTargetSerializer


def _allowed_units(user):
    """ログイン者が選べるグループを返す。superuser は全グループ。"""
    queryset = Department.objects.filter(level='unit')
    if user.is_superuser:
        return queryset.order_by('display_id', 'name', 'id')

    try:
        profile = user.profile
    except Exception:
        return queryset.none()

    unit_ids = set(profile.leader_units.values_list('id', flat=True))
    if profile.unit_id:
        unit_ids.add(profile.unit_id)
    if profile.role == 'supervisor':
        # 班長は自分が統括する班（supervisor_teams、本人所属のteamを含む）の配下グループを担当する。
        # manager/chief等のdivision/group配下まで遡ると担当外グループまで見えてしまうため、
        # supervisorロールのteam配下（unitの親は必ずteam）に限定する。
        team_ids = set(profile.supervisor_teams.values_list('id', flat=True))
        if profile.team_id:
            team_ids.add(profile.team_id)
        if team_ids:
            unit_ids.update(
                Department.objects.filter(level='unit', parent_id__in=team_ids).values_list('id', flat=True)
            )
    return queryset.filter(id__in=unit_ids).order_by('display_id', 'name', 'id')


def _allowed_line_ids(user):
    unit_ids = _allowed_units(user).values_list('id', flat=True)
    return UnitLineMapping.objects.filter(unit_id__in=unit_ids).values_list('line_id', flat=True)


class ProgressMonitorTargetViewSet(viewsets.ModelViewSet):
    serializer_class = ProgressMonitorTargetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = ProgressMonitorTarget.objects.select_related(
            'product', 'line', 'registered_by'
        ).filter(line_id__in=_allowed_line_ids(self.request.user))
        line_id = self.request.query_params.get('line')
        if line_id:
            queryset = queryset.filter(line_id=line_id)
        active = self.request.query_params.get('is_active')
        if active in ('true', '1'):
            queryset = queryset.filter(is_active=True)
        elif active in ('false', '0'):
            queryset = queryset.filter(is_active=False)
        return queryset.order_by('display_order', 'line__line_code', 'product__product_code', 'id')

    def _line_is_allowed(self, line_id):
        return UnitLineMapping.objects.filter(
            unit_id__in=_allowed_units(self.request.user).values_list('id', flat=True),
            line_id=line_id,
        ).exists()

    def create(self, request, *args, **kwargs):
        if not self._line_is_allowed(request.data.get('line')):
            return Response({'detail': '選択したラインは担当グループの対象外です。'}, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        line_id = request.data.get('line', self.get_object().line_id)
        if not self._line_is_allowed(line_id):
            return Response({'detail': '選択したラインは担当グループの対象外です。'}, status=status.HTTP_400_BAD_REQUEST)
        return super().update(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(registered_by=self.request.user)

    @action(detail=False, methods=['get'], url_path='options')
    def options(self, request):
        units = list(_allowed_units(request.user).values('id', 'name', 'display_id'))
        mappings = UnitLineMapping.objects.select_related('line').filter(
            unit_id__in=[unit['id'] for unit in units],
        ).order_by('unit_id', '-is_default', 'sort_order', 'line__line_code', 'id')
        lines_by_unit = {}
        for mapping in mappings:
            lines_by_unit.setdefault(str(mapping.unit_id), []).append({
                'id': mapping.line_id,
                'line_code': mapping.line.line_code,
                'line_name': mapping.line.line_name,
            })
        return Response({'units': units, 'lines_by_unit': lines_by_unit})

    @action(detail=False, methods=['get'], url_path='product-candidates')
    def product_candidates(self, request):
        keyword = str(request.query_params.get('search', '')).strip()
        queryset = Product.objects.filter(is_active=True)
        if keyword:
            queryset = queryset.filter(
                Q(product_code__icontains=keyword)
                | Q(product_name__icontains=keyword)
                | Q(product_name_halfwidth__icontains=keyword)
            )
        return Response(list(queryset.order_by('product_code').values('id', 'product_code', 'product_name')))

    @action(detail=False, methods=['get'], url_path='snapshot')
    def snapshot(self, request):
        raw_unit_ids = [
            part.strip()
            for value in request.query_params.getlist('unit_id')
            for part in str(value).split(',')
            if part.strip()
        ]
        try:
            unit_ids = [int(value) for value in raw_unit_ids]
        except (TypeError, ValueError):
            return Response({'detail': 'unit_id は数値で指定してください。'}, status=status.HTTP_400_BAD_REQUEST)
        if not unit_ids:
            return Response({'detail': 'unit_id は必須です。'}, status=status.HTTP_400_BAD_REQUEST)
        unit_ids = sorted(set(unit_ids))
        allowed_units = _allowed_units(request.user).filter(id__in=unit_ids)
        if allowed_units.count() != len(unit_ids):
            return Response({'detail': '選択したグループは対象外です。'}, status=status.HTTP_400_BAD_REQUEST)

        raw_start_date = request.query_params.get('start_date')
        try:
            start_date = date.fromisoformat(raw_start_date or '')
        except ValueError:
            return Response({'detail': 'start_date は YYYY-MM-DD 形式で指定してください。'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            horizon = int(request.query_params.get('horizon', '30'))
        except (TypeError, ValueError):
            return Response({'detail': 'horizon は 30、60、90、120 のいずれかを指定してください。'}, status=status.HTTP_400_BAD_REQUEST)
        if horizon not in (30, 60, 90, 120):
            return Response({'detail': 'horizon は 30、60、90、120 のいずれかを指定してください。'}, status=status.HTTP_400_BAD_REQUEST)
        end_date = start_date + timedelta(days=horizon - 1)

        mappings = list(UnitLineMapping.objects.select_related('line').filter(
            unit_id__in=unit_ids,
        ).order_by('unit_id', '-is_default', 'sort_order', 'line__line_code', 'id'))
        line_ids = [mapping.line_id for mapping in mappings]
        all_targets = list(ProgressMonitorTarget.objects.select_related('product', 'line').filter(
            line_id__in=line_ids,
        ).order_by('display_order', 'line__line_code', 'product__product_code', 'id'))
        targets = [target for target in all_targets if target.is_active]

        target_keys = {(target.line_id, target.product_id) for target in targets}
        base_map = defaultdict(lambda: {
            'actual': 0,
            'adjust': 0,
            'planned_progress': 0,
            'progress': 0,
            'scrap': 0,
            'stock': 0,
            'planned_stock': 0,
            'order_qty': 0,
            'order_qty_actual': 0,
        })
        plan_map = defaultdict(int)
        demand_map = defaultdict(lambda: {'forecast': 0, 'firm': 0})
        process_meta = {}
        processes_by_target = defaultdict(set)
        if target_keys:
            backlogs = LineBacklog.objects.select_related('process').filter(
                plan_date__range=(start_date, end_date),
                line_id__in=line_ids,
                product_id__in={product_id for _, product_id in target_keys},
            ).order_by('line_id', 'product_id', 'process__process_code', 'id')
            for backlog in backlogs:
                target_key = (backlog.line_id, backlog.product_id)
                if target_key not in target_keys:
                    continue
                process_key = (backlog.line_id, backlog.product_id, backlog.process_id)
                process_meta[process_key] = backlog.process
                processes_by_target[target_key].add(backlog.process_id)
                data_key = (*process_key, backlog.plan_date)
                if backlog.sequence_no > 0:
                    plan_map[data_key] += backlog.plan_qty or 0
                elif backlog.sequence_no == 0:
                    cell = base_map[data_key]
                    cell['actual'] += backlog.actual_qty or 0
                    cell['adjust'] += backlog.adjust_qty or 0
                    cell['planned_progress'] += backlog.planned_progress_qty or 0
                    cell['progress'] += backlog.progress_qty or 0
                    cell['scrap'] += backlog.scrap_qty or 0
                    cell['stock'] += backlog.stock_qty or 0
                    cell['planned_stock'] += backlog.planned_stock_qty or 0
                    cell['order_qty'] += backlog.order_qty or 0
                    cell['order_qty_actual'] += backlog.order_qty_actual or 0

            demands = LineDemand.objects.select_related('process').filter(
                plan_date__range=(start_date, end_date),
                line_id__in=line_ids,
                product_id__in={product_id for _, product_id in target_keys},
            ).order_by('line_id', 'product_id', 'process__process_code', 'id')
            for demand in demands:
                target_key = (demand.line_id, demand.product_id)
                if target_key not in target_keys:
                    continue
                if demand.process_id is not None:
                    process_key = (demand.line_id, demand.product_id, demand.process_id)
                    process_meta[process_key] = demand.process
                    processes_by_target[target_key].add(demand.process_id)
                data_key = (demand.line_id, demand.product_id, demand.process_id, demand.plan_date)
                demand_cell = demand_map[data_key]
                demand_cell['forecast'] += demand.forecast_qty or 0
                demand_cell['firm'] += demand.firm_qty or 0

        rows = []
        for target in targets:
            target_key = (target.line_id, target.product_id)
            process_ids = sorted(
                processes_by_target.get(target_key, set()),
                key=lambda process_id: (
                    process_meta[(target.line_id, target.product_id, process_id)].process_code,
                    process_id,
                ),
            )
            if not process_ids:
                process_ids = [None]
            for process_id in process_ids:
                process = process_meta.get((target.line_id, target.product_id, process_id))
                cells = {}
                for day_offset in range(horizon):
                    current_date = start_date + timedelta(days=day_offset)
                    data_key = (target.line_id, target.product_id, process_id, current_date)
                    base = base_map.get(data_key)
                    plan = plan_map.get(data_key)
                    # 工程一致の需要を優先し、なければ工程なし需要を使用する。
                    demand = demand_map.get(data_key)
                    if demand is None:
                        demand = demand_map.get((target.line_id, target.product_id, None, current_date))
                    if base is None and plan is None and demand is None:
                        continue
                    if target.monitor_type == ProgressMonitorTarget.MONITOR_TYPE_INVENTORY:
                        # 在庫監視の計需・実需は後工程の計画・実績を集計したorder_qty/order_qty_actualを使う
                        forecast_value = base['order_qty'] if base is not None else 0
                        firm_value = base['order_qty_actual'] if base is not None else 0
                    else:
                        forecast_value = demand['forecast'] if demand is not None else 0
                        firm_value = demand['firm'] if demand is not None else 0
                    cells[current_date.isoformat()] = {
                        'forecast': forecast_value,
                        'firm': firm_value,
                        'plan': plan or 0,
                        'actual': base['actual'] if base is not None else 0,
                        'adjust': base['adjust'] if base is not None else 0,
                        'planned_progress': base['planned_progress'] if base is not None else 0,
                        'progress': base['progress'] if base is not None else 0,
                        'scrap': base['scrap'] if base is not None else 0,
                        'stock': base['stock'] if base is not None else 0,
                        'planned_stock': base['planned_stock'] if base is not None else 0,
                    }
                rows.append({
                    'target_id': target.id,
                    'monitor_type': target.monitor_type,
                    'display_order': target.display_order,
                    'memo': target.memo,
                    'is_active': target.is_active,
                    'line_id': target.line_id,
                    'line_code': target.line.line_code,
                    'line_name': target.line.line_name,
                    'product_id': target.product_id,
                    'product_code': target.product.product_code,
                    'product_name': target.product.product_name,
                    'process_id': process_id,
                    'process_code': process.process_code if process else None,
                    'process_name': process.process_name if process else None,
                    'cells': cells,
                })

        units_by_id = {unit.id: unit for unit in allowed_units}
        return Response({
            'units': [
                {'id': unit_id, 'name': units_by_id[unit_id].name}
                for unit_id in unit_ids
            ],
            'start_date': start_date,
            'end_date': end_date,
            'horizon': horizon,
            'dates': [
                (start_date + timedelta(days=day_offset)).isoformat()
                for day_offset in range(horizon)
            ],
            'lines': [
                {
                    'id': mapping.line_id,
                    'line_code': mapping.line.line_code,
                    'line_name': mapping.line.line_name,
                    'unit_id': mapping.unit_id,
                }
                for mapping in mappings
            ],
            'targets': [
                {
                    'target_id': target.id,
                    'monitor_type': target.monitor_type,
                    'display_order': target.display_order,
                    'memo': target.memo,
                    'is_active': target.is_active,
                    'line_id': target.line_id,
                    'line_code': target.line.line_code,
                    'line_name': target.line.line_name,
                    'product_id': target.product_id,
                    'product_code': target.product.product_code,
                    'product_name': target.product.product_name,
                }
                for target in all_targets
            ],
            'rows': rows,
        })
