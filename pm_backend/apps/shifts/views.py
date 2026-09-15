from collections import defaultdict
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from .models import ShiftLine, ShiftWorker, ShiftLineProcess, ShiftAssignment
from .serializers import (
    ShiftLineSerializer, ShiftWorkerSerializer,
    ShiftLineProcessSerializer, ShiftAssignmentSerializer,
    ShiftAssignmentBulkSerializer,
)
from production.models_line_gantt_plan import LineGanttPlan


class ShiftLineViewSet(viewsets.ModelViewSet):
    queryset = ShiftLine.objects.prefetch_related('workers', 'line_processes__process').all()
    serializer_class = ShiftLineSerializer
    pagination_class = None

    @action(detail=True, methods=['post'], url_path='reorder-workers')
    def reorder_workers(self, request, pk=None):
        """作業者の並び替え"""
        line = self.get_object()
        worker_ids = request.data.get('worker_ids', [])
        for i, wid in enumerate(worker_ids):
            ShiftWorker.objects.filter(id=wid, shift_line=line).update(sort_order=i)
        return Response({'status': 'ok'})

    @action(detail=True, methods=['get'], url_path='process-loads')
    def process_loads(self, request, pk=None):
        """シフトラインの工程別負荷時間を取得（工程ガントから集計）"""
        line = self.get_object()
        date = request.query_params.get('date')
        if not date:
            return Response(
                {'error': 'dateは必須です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        line_processes = ShiftLineProcess.objects.filter(
            shift_line=line
        ).select_related('process')

        # シフトラインの工程ID→生産ラインIDのマッピング
        process_to_production_line = {}
        production_line_ids = set()
        for lp in line_processes:
            if lp.process and lp.process.line_id:
                process_to_production_line[lp.process_id] = lp.process.line_id
                production_line_ids.add(lp.process.line_id)

        if not production_line_ids:
            return Response({'date': date, 'loads': {}})

        # 工程ガントから該当日・該当ラインのデータを取得
        gantt_plans = LineGanttPlan.objects.filter(
            line_id__in=production_line_ids,
            plan_date=date,
        )

        # 工程別にeffective_minutesを集計
        load_by_process = defaultdict(float)
        for plan in gantt_plans:
            processes_plan = plan.processes_plan or []
            for pp in processes_plan:
                proc_id = pp.get('process_id')
                if proc_id is not None and proc_id in process_to_production_line:
                    minutes = float(pp.get('effective_minutes') or pp.get('total_minutes_required') or 0)
                    load_by_process[proc_id] += minutes

        loads = {}
        for proc_id, minutes in load_by_process.items():
            loads[str(proc_id)] = {
                'load_min': round(minutes, 1),
                'load_hours': round(minutes / 60, 2),
            }

        return Response({'date': date, 'loads': loads})


class ShiftWorkerViewSet(viewsets.ModelViewSet):
    queryset = ShiftWorker.objects.all()
    serializer_class = ShiftWorkerSerializer
    pagination_class = None
    filterset_fields = ['shift_line']


class ShiftLineProcessViewSet(viewsets.ModelViewSet):
    queryset = ShiftLineProcess.objects.select_related('process').all()
    serializer_class = ShiftLineProcessSerializer
    pagination_class = None
    filterset_fields = ['shift_line']


class ShiftAssignmentViewSet(viewsets.ModelViewSet):
    queryset = ShiftAssignment.objects.select_related('worker', 'process').all()
    serializer_class = ShiftAssignmentSerializer
    pagination_class = None
    filterset_fields = ['shift_line', 'date', 'worker']

    @action(detail=False, methods=['get'], url_path='by-range')
    def by_range(self, request):
        """日付範囲でフィルタ"""
        line_id = request.query_params.get('shift_line')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        qs = self.get_queryset()
        if line_id:
            qs = qs.filter(shift_line_id=line_id)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=['post'], url_path='copy-day')
    def copy_day(self, request):
        """シフトコピー（日→日、または1週間一括）"""
        ser = ShiftAssignmentBulkSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        source_date = ser.validated_data['source_date']
        target_dates = ser.validated_data['target_dates']
        line_id = ser.validated_data['shift_line']

        source_assignments = ShiftAssignment.objects.filter(
            shift_line_id=line_id, date=source_date
        )
        if not source_assignments.exists():
            return Response(
                {'error': '元の日に配置がありません'},
                status=status.HTTP_400_BAD_REQUEST
            )

        created_count = 0
        with transaction.atomic():
            for target_date in target_dates:
                ShiftAssignment.objects.filter(
                    shift_line_id=line_id, date=target_date
                ).delete()
                for a in source_assignments:
                    ShiftAssignment.objects.create(
                        shift_line_id=line_id,
                        worker=a.worker,
                        process=a.process,
                        line_process=a.line_process,
                        date=target_date,
                        start_time=a.start_time,
                        work_hours=a.work_hours,
                        units=a.units,
                        comment=a.comment,
                    )
                    created_count += 1

        return Response({'created': created_count})

    @action(detail=False, methods=['post'], url_path='reset-day')
    def reset_day(self, request):
        """指定日・ラインの配置をすべて削除"""
        line_id = request.data.get('shift_line')
        date = request.data.get('date')
        if not line_id or not date:
            return Response(
                {'error': 'shift_lineとdateは必須です'},
                status=status.HTTP_400_BAD_REQUEST
            )
        deleted, _ = ShiftAssignment.objects.filter(
            shift_line_id=line_id, date=date
        ).delete()
        return Response({'deleted': deleted})
