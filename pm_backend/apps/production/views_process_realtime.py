"""
工程実時間記録API
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import models, transaction
from django.db.models import Sum
from django.utils.dateparse import parse_date, parse_datetime
from django.utils import timezone
from django.conf import settings
from decimal import Decimal, InvalidOperation
from datetime import datetime, time, timedelta

from .models_process_realtime import ProcessRealtimeRecord
from .models_process_work_session import ProcessWorkSession
from .models_process_work_session_change_history import ProcessWorkSessionChangeHistory
from .serializers_process_realtime import (
    ProcessRealtimeRecordSerializer,
    ProcessRealtimeCreateSerializer,
    ProcessWorkSessionSerializer,
    ProcessWorkSessionChangeHistorySerializer,
    resolve_workday_date_for_process,
    _next_session_no,
    check_plan_overrun,
)
from .services.process_realtime_backlog_service import (
    adjust_backlog_actual_for_session,
    adjust_backlog_scrap_for_session,
    adjust_coproduct_children_backlog,
    apply_delta_to_inventory_and_progress,
    recalculate_child_stock_after_record_edit,
    recalculate_inventory_for_product_impact,
    recalculate_inventory_after_session_change,
    rebuild_session_production_records,
    update_coproduct_children_records,
)
from .services.gantt_planning import LineWorkCalendar
from .services.process_realtime_history_service import (
    create_session_change_history,
    serialize_session_snapshot,
)
from .services.process_realtime_common import (
    build_business_boundary_datetime,
    calculate_effective_work_seconds,
    is_countable_session_for_actual,
    normalize_input_datetime,
    to_local_naive,
)
from .services.process_realtime_query_service import get_gantt_plan_qty
from .services.process_realtime_scrap_service import (
    ScrapServiceError,
    get_scrap_breakdown,
    mark_scrap_detail_replenished,
    mark_scrap_replenished,
    process_scrap_disposition,
)
from .models_line_backlog import LineBacklog
from masters.models import Product, Process, BOM, RoutingStep
from masters.services.routing_service import build_effective_routing_q
from orders.utils.calendar_utils import get_business_today, DAY_BOUNDARY_HOUR


class ProcessRealtimeRecordViewSet(viewsets.ModelViewSet):
    """工程実時間記録ViewSet"""

    queryset = ProcessRealtimeRecord.objects.all()
    serializer_class = ProcessRealtimeRecordSerializer

    @staticmethod
    def _get_session_output_routing_steps(session):
        """セッション製品を当日に出力する、同一ライン上の有効工程を取得する。"""
        if not session.product_id or not session.process_id or not session.plan_date:
            return []
        line_id = getattr(session.process, 'line_id', None)
        if not line_id:
            return []

        return list(
            RoutingStep.objects.filter(
                output_product_id=session.product_id,
                process_id__isnull=False,
            ).filter(
                build_effective_routing_q(session.plan_date, prefix='routing__')
            ).filter(
                models.Q(line_id=line_id)
                | models.Q(line__isnull=True, process__line_id=line_id)
            ).select_related('process', 'process__line', 'line')
        )

    @staticmethod
    def _recalculate_product_on_output_routes(session, routing_steps):
        """誤工程削除後、製品の正規出力ラインから在庫・進度を再計算する。"""
        line_ids = {
            step.line_id or getattr(step.process, 'line_id', None)
            for step in routing_steps
        }
        for line_id in sorted(line_id for line_id in line_ids if line_id):
            recalculate_inventory_for_product_impact(
                line_id=line_id,
                product_id=session.product_id,
                plan_date=session.plan_date,
            )

    def get_queryset(self):
        queryset = ProcessRealtimeRecord.objects.select_related('process', 'product', 'scrap_detail')

        process_id = self.request.query_params.get('process_id')
        if process_id:
            queryset = queryset.filter(process_id=process_id)

        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            d = parse_date(start_date)
            if d:
                start_dt = datetime.combine(d, time.min)
                if settings.USE_TZ:
                    start_dt = timezone.make_aware(start_dt)
                queryset = queryset.filter(timestamp__gte=start_dt)
            else:
                queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            d = parse_date(end_date)
            if d:
                end_dt = datetime.combine(d, time.max)
                if settings.USE_TZ:
                    end_dt = timezone.make_aware(end_dt)
                queryset = queryset.filter(timestamp__lte=end_dt)
            else:
                queryset = queryset.filter(timestamp__lte=end_date)

        record_type = self.request.query_params.get('record_type')
        if record_type:
            queryset = queryset.filter(record_type=record_type)

        product_id = self.request.query_params.get('product_id')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        product_code = self.request.query_params.get('product_code')
        if product_code:
            queryset = queryset.filter(product_code=product_code)

        return queryset.order_by('-timestamp')

    def create(self, request, *args, **kwargs):
        serializer = ProcessRealtimeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = serializer.save()
        response_data = ProcessRealtimeRecordSerializer(record).data

        # 生産実績・作業者アクション(END/PAUSE)の場合、計画超過チェック
        record_type = request.data.get('record_type', '')
        event_data = request.data.get('event_data') or {}
        action_upper = str(event_data.get('action', '')).upper()
        is_production = record_type == 'PRODUCTION'
        is_end_or_pause = record_type == 'OPERATOR_ACTION' and action_upper in ('END', 'PAUSE')

        if is_production or is_end_or_pause:
            process = getattr(record, 'process', None)
            product = getattr(record, 'product', None)
            plan_date = getattr(record, 'plan_date', None)
            if not plan_date and hasattr(record, 'timestamp') and record.timestamp:
                plan_date = resolve_workday_date_for_process(process, record.timestamp)
            if process and product and plan_date:
                overrun = check_plan_overrun(process, product, plan_date)
                if overrun:
                    response_data['plan_overrun_warning'] = overrun

        return Response(response_data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get', 'post'], url_path='sessions')
    def sessions(self, request):
        """
        開始〜終了セッションの一覧を返す（GET）、または後入力セッションを新規作成する（POST）。
        """
        if request.method.lower() == 'post':
            return self._create_manual_session(request)

        """
        稼働時間分析と不整合検知の確認用。
        """
        queryset = ProcessWorkSession.objects.select_related(
            'process',
            'product',
            'start_record',
            'end_record',
        ).prefetch_related('session_equipments__equipment')

        session_id = request.query_params.get('session_id')
        if session_id:
            queryset = queryset.filter(id=session_id)

        process_id = request.query_params.get('process_id')
        if process_id:
            queryset = queryset.filter(process_id=process_id)

        line_id = request.query_params.get('line_id')
        if line_id:
            queryset = queryset.filter(process__line_id=line_id)

        product_id = request.query_params.get('product_id')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        # 連産子への表示展開後にも適用できるよう、品番フィルタは後段で評価する。
        product_code = (request.query_params.get('product_code') or '').strip()

        status_param = (request.query_params.get('status') or '').strip().upper()
        if status_param:
            queryset = queryset.filter(status=status_param)

        session_type = (request.query_params.get('session_type') or '').strip().upper()
        if session_type:
            queryset = queryset.filter(session_type=session_type)

        start_date = request.query_params.get('start_date')
        if start_date:
            d = parse_date(start_date)
            if d:
                queryset = queryset.filter(
                    started_at__gte=build_business_boundary_datetime(d)
                )

        end_date = request.query_params.get('end_date')
        if end_date:
            d = parse_date(end_date)
            if d:
                queryset = queryset.filter(
                    started_at__lt=build_business_boundary_datetime(d, day_offset=1)
                )

        # 計画日（plan_date）での絞り込み
        plan_date_start = request.query_params.get('plan_date_start')
        if plan_date_start:
            d = parse_date(plan_date_start)
            if d:
                queryset = queryset.filter(plan_date__gte=d)

        plan_date_end = request.query_params.get('plan_date_end')
        if plan_date_end:
            d = parse_date(plan_date_end)
            if d:
                queryset = queryset.filter(plan_date__lte=d)

        unclosed = request.query_params.get('unclosed')
        if unclosed is not None:
            normalized_uc = str(unclosed).strip().lower()
            if normalized_uc in ('1', 'true', 'yes'):
                queryset = queryset.filter(status='OPEN')

        has_issue = request.query_params.get('has_issue')
        if has_issue is not None:
            normalized = str(has_issue).strip().lower()
            if normalized in ('1', 'true', 'yes'):
                queryset = queryset.filter(issue_count__gt=0)
            elif normalized in ('0', 'false', 'no'):
                queryset = queryset.filter(issue_count=0)

        limit = request.query_params.get('limit')
        try:
            limit_value = int(limit) if limit is not None else 200
        except ValueError:
            limit_value = 200
        limit_value = max(1, min(limit_value, 2000))

        sessions = list(queryset.order_by('-started_at', '-id')[:limit_value])
        serializer = ProcessWorkSessionSerializer(sessions, many=True)
        base_rows = list(serializer.data or [])
        if not base_rows:
            return Response([])

        line_calendar_cache = {}
        effective_seconds_map = {}

        for session_obj in sessions:
            session_id = getattr(session_obj, 'id', None)
            if not session_id:
                continue
            process = getattr(session_obj, 'process', None)
            line = getattr(process, 'line', None) if process else None
            line_id = getattr(line, 'id', None) if line else None

            calendar = None
            if line_id is not None:
                if line_id not in line_calendar_cache:
                    try:
                        line_calendar_cache[line_id] = LineWorkCalendar(line)
                    except Exception:
                        line_calendar_cache[line_id] = None
                calendar = line_calendar_cache.get(line_id)

            ended_at = session_obj.ended_at or timezone.now()
            effective_seconds_map[session_id] = calculate_effective_work_seconds(
                calendar=calendar,
                started_at=session_obj.started_at,
                ended_at=ended_at,
            )

        def enrich_row_metrics(target_row):
            session_id = target_row.get('id')
            effective_seconds = int(effective_seconds_map.get(session_id) or 0)
            target_row['effective_work_seconds'] = effective_seconds

            qty_raw = target_row.get('production_qty')
            try:
                qty = Decimal(str(qty_raw or 0))
            except (InvalidOperation, TypeError, ValueError):
                qty = Decimal('0')

            if effective_seconds > 0 and qty > 0:
                productivity = (qty * Decimal('3600')) / Decimal(str(effective_seconds))
                target_row['productivity_per_hour'] = float(productivity.quantize(Decimal('0.001')))
            else:
                target_row['productivity_per_hour'] = None

        session_ids = [row.get('id') for row in base_rows if row.get('id')]
        session_id_set = set(session_ids)
        child_rows_by_session = {}
        if session_ids:
            production_rows = list(ProcessRealtimeRecord.objects.filter(
                record_type='PRODUCTION',
                event_data__work_session_id__in=session_ids,
            ).values(
                'id',
                'product_id',
                'product_code',
                'product_name',
                'qty',
                'event_data',
            ))

            # 既存データ互換:
            # OPERATOR_ACTION=PAUSE の数量が中断セッションに紐付いている場合、
            # 直前で閉じた作業セッション（end_action=PAUSE 側）へ寄せて表示する。
            pause_action_record_ids = set()
            for rec in production_rows:
                event_data = rec.get('event_data') or {}
                operator_action = str(event_data.get('operator_action') or '').upper()
                if operator_action != 'PAUSE':
                    continue
                action_record_raw = event_data.get('operator_action_record_id')
                try:
                    action_record_id = int(action_record_raw)
                except (TypeError, ValueError):
                    continue
                pause_action_record_ids.add(action_record_id)

            pause_to_work_session = {}
            if pause_action_record_ids:
                work_rows = ProcessWorkSession.objects.filter(
                    end_record_id__in=list(pause_action_record_ids),
                    session_type='WORK',
                ).values('end_record_id', 'id')
                for work_row in work_rows:
                    end_record_id = work_row.get('end_record_id')
                    work_session_id = work_row.get('id')
                    if not end_record_id or not work_session_id:
                        continue
                    prev_id = pause_to_work_session.get(end_record_id)
                    if prev_id is None or work_session_id > prev_id:
                        pause_to_work_session[end_record_id] = work_session_id

            for rec in production_rows:
                event_data = rec.get('event_data') or {}
                session_id_raw = event_data.get('work_session_id')
                parent_record_id = event_data.get('coproduct_parent_record_id')
                if not session_id_raw or not parent_record_id:
                    # 連産子展開レコードのみ対象（親実績は表示置換に使わない）
                    continue
                try:
                    session_id = int(session_id_raw)
                except (TypeError, ValueError):
                    continue

                operator_action = str(event_data.get('operator_action') or '').upper()
                if operator_action == 'PAUSE':
                    action_record_raw = event_data.get('operator_action_record_id')
                    try:
                        action_record_id = int(action_record_raw)
                    except (TypeError, ValueError):
                        action_record_id = None
                    mapped_session_id = pause_to_work_session.get(action_record_id)
                    if mapped_session_id and mapped_session_id in session_id_set:
                        session_id = mapped_session_id

                child_rows_by_session.setdefault(session_id, []).append({
                    'source_record_id': rec.get('id'),
                    'product_id': rec.get('product_id'),
                    'product_code': (rec.get('product_code') or '').strip() or None,
                    'product_name': (rec.get('product_name') or '').strip() or None,
                    'production_qty': rec.get('qty') or 0,
                    'coproduct_parent_product_code': (
                        (event_data.get('coproduct_parent_product_code') or '').strip() or None
                    ),
                })

            for key, values in child_rows_by_session.items():
                values.sort(key=lambda x: (
                    x.get('product_code') or '',
                    x.get('product_id') or 0,
                    x.get('source_record_id') or 0,
                ))

        result_rows = []
        coproduct_mode = (request.query_params.get('coproduct_mode') or 'child_only').strip().lower()
        if coproduct_mode not in ('child_only', 'parent_only', 'both'):
            coproduct_mode = 'child_only'
        for row in base_rows:
            session_id = row.get('id')
            child_rows = child_rows_by_session.get(session_id) or []
            if child_rows:
                if coproduct_mode in ('parent_only', 'both'):
                    parent_row = dict(row)
                    parent_row['is_coproduct_child'] = False
                    parent_row['coproduct_parent_product_code'] = None
                    enrich_row_metrics(parent_row)
                    result_rows.append(parent_row)
                if coproduct_mode in ('child_only', 'both'):
                    for child in child_rows:
                        expanded = dict(row)
                        expanded['product'] = child.get('product_id')
                        expanded['product_code'] = child.get('product_code')
                        expanded['product_name'] = child.get('product_name')
                        expanded['production_qty'] = child.get('production_qty') or 0
                        expanded['coproduct_source_record_id'] = child.get('source_record_id')
                        expanded['is_coproduct_child'] = True
                        expanded['coproduct_parent_product_code'] = child.get('coproduct_parent_product_code')
                        enrich_row_metrics(expanded)
                        result_rows.append(expanded)
                continue

            expanded = dict(row)
            expanded['coproduct_source_record_id'] = None
            expanded['is_coproduct_child'] = False
            expanded['coproduct_parent_product_code'] = None
            enrich_row_metrics(expanded)
            result_rows.append(expanded)

        if product_code:
            keyword = product_code.lower()
            filtered_rows = []
            for row in result_rows:
                code = str(row.get('product_code') or '').lower()
                parent_code = str(row.get('coproduct_parent_product_code') or '').lower()
                if keyword in code or (parent_code and keyword in parent_code):
                    filtered_rows.append(row)
            result_rows = filtered_rows

        return Response(result_rows)

    def _create_manual_session(self, request):
        """
        後入力セッションを新規作成する。
        入力: process_id, product_code, started_at, ended_at, production_qty
        """
        payload = request.data or {}

        process_id = payload.get('process_id')
        product_code = str(payload.get('product_code') or '').strip()
        change_reason = str(payload.get('change_reason') or '').strip()
        started_at_raw = payload.get('started_at')
        ended_at_raw = payload.get('ended_at')
        production_qty_raw = payload.get('production_qty')
        operator_name = str(payload.get('operator_name') or '').strip()

        if not process_id:
            return Response({'detail': 'process_id は必須です。'}, status=status.HTTP_400_BAD_REQUEST)
        if not product_code:
            return Response({'detail': 'product_code は必須です。'}, status=status.HTTP_400_BAD_REQUEST)
        if not change_reason:
            return Response({'detail': 'change_reason は必須です。'}, status=status.HTTP_400_BAD_REQUEST)
        if not started_at_raw:
            return Response({'detail': 'started_at は必須です。'}, status=status.HTTP_400_BAD_REQUEST)
        if not ended_at_raw:
            return Response({'detail': 'ended_at は必須です。'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            production_qty = Decimal(str(production_qty_raw or 0))
        except (InvalidOperation, TypeError, ValueError):
            return Response({'detail': 'production_qty の形式が不正です。'}, status=status.HTTP_400_BAD_REQUEST)
        if production_qty < 0:
            return Response({'detail': 'production_qty は0以上で入力してください。'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            process = Process.objects.get(id=process_id)
        except Process.DoesNotExist:
            return Response({'detail': '指定された工程が存在しません。'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(product_code=product_code)
        except Product.DoesNotExist:
            return Response({'detail': f'品番 {product_code} が存在しません。'}, status=status.HTTP_400_BAD_REQUEST)

        parsed_start = parse_datetime(started_at_raw) if isinstance(started_at_raw, str) else None
        if not parsed_start:
            return Response({'detail': 'started_at の形式が不正です。'}, status=status.HTTP_400_BAD_REQUEST)
        parsed_end = parse_datetime(ended_at_raw) if isinstance(ended_at_raw, str) else None
        if not parsed_end:
            return Response({'detail': 'ended_at の形式が不正です。'}, status=status.HTTP_400_BAD_REQUEST)

        started_at = normalize_input_datetime(parsed_start)
        ended_at = normalize_input_datetime(parsed_end)

        if ended_at < started_at:
            return Response({'detail': '終了時刻は開始時刻以降にしてください。'}, status=status.HTTP_400_BAD_REQUEST)

        # 日替わり時刻（8時）を考慮して計画日を算出
        local_start = to_local_naive(started_at)
        plan_date = resolve_workday_date_for_process(process, local_start)

        duration_seconds = int((ended_at - started_at).total_seconds())

        with transaction.atomic():
            session = ProcessWorkSession.objects.create(
                process=process,
                product=product,
                product_code=product.product_code,
                product_name=product.product_name,
                plan_date=plan_date,
                session_no=_next_session_no(process, product, plan_date),
                session_type='WORK',
                start_action='MANUAL',
                end_action='END',
                started_at=started_at,
                ended_at=ended_at,
                status='CLOSED',
                duration_seconds=duration_seconds,
                production_qty=production_qty,
                operator_name=operator_name,
            )
            changed_by = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
            create_session_change_history(
                session_obj=session,
                operation_type='ADD',
                reason=change_reason,
                changed_by=changed_by,
                before_data={},
                after_data=serialize_session_snapshot(session),
            )
            rebuild_session_production_records(session)
            if production_qty:
                adjust_backlog_actual_for_session(session, int(production_qty))
                adjust_coproduct_children_backlog(session, int(production_qty))
                apply_delta_to_inventory_and_progress(session, int(production_qty))
            recalculate_inventory_after_session_change(session)

        serializer = ProcessWorkSessionSerializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['patch', 'delete'], url_path=r'sessions/(?P<session_id>[^/.]+)')
    def session_detail(self, request, session_id=None):
        session = ProcessWorkSession.objects.select_related('process', 'product').prefetch_related('session_equipments__equipment').filter(id=session_id).first()
        if not session:
            return Response({'detail': 'セッションが見つかりません。'}, status=status.HTTP_404_NOT_FOUND)

        if request.method.lower() == 'delete':
            payload = request.data or {}
            change_reason = str(payload.get('change_reason') or '').strip()
            if not change_reason:
                return Response({'detail': 'change_reason は必須です。'}, status=status.HTTP_400_BAD_REQUEST)

            before_snapshot = serialize_session_snapshot(session)
            changed_by = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
            output_routing_steps = self._get_session_output_routing_steps(session)
            is_valid_process = any(step.process_id == session.process_id for step in output_routing_steps)
            with transaction.atomic():
                create_session_change_history(
                    session_obj=session,
                    operation_type='DELETE',
                    reason=change_reason,
                    changed_by=changed_by,
                    before_data=before_snapshot,
                    after_data={},
                )
                if is_valid_process:
                    old_qty = int(session.production_qty or 0) if is_countable_session_for_actual(
                        session.session_type, session.end_action
                    ) else 0
                    if old_qty:
                        adjust_backlog_actual_for_session(session, -old_qty)
                        adjust_coproduct_children_backlog(session, -old_qty)
                        apply_delta_to_inventory_and_progress(session, -old_qty)
                else:
                    # 誤工程で作られた基礎行・計画行は実績として扱わず全て除去する。
                    LineBacklog.objects.filter(
                        line_id=session.process.line_id,
                        process_id=session.process_id,
                        product_id=session.product_id,
                        plan_date=session.plan_date,
                    ).delete()

                ProcessRealtimeRecord.objects.filter(
                    record_type='PRODUCTION',
                    event_data__work_session_id=session.id,
                ).delete()
                if is_valid_process:
                    recalculate_inventory_after_session_change(session)
                else:
                    self._recalculate_product_on_output_routes(session, output_routing_steps)
                session.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        payload = request.data or {}
        change_reason = str(payload.get('change_reason') or '').strip()
        started_at = session.started_at
        ended_at = session.ended_at
        production_qty = session.production_qty
        defect_qty = session.defect_qty
        new_product = None
        product_changed = False
        before_snapshot = serialize_session_snapshot(session)

        if not change_reason:
            return Response({'detail': 'change_reason は必須です。'}, status=status.HTTP_400_BAD_REQUEST)

        if 'product_code' in payload:
            new_code = str(payload.get('product_code') or '').strip()
            if not new_code:
                return Response({'detail': '品番は必須です。'}, status=status.HTTP_400_BAD_REQUEST)
            new_product = Product.objects.filter(product_code=new_code).first()
            if not new_product:
                return Response({'detail': f'品番 {new_code} が見つかりません。'}, status=status.HTTP_400_BAD_REQUEST)
            if session.product_id != new_product.id:
                product_changed = True

        if 'started_at' in payload:
            next_started = payload.get('started_at')
            parsed = parse_datetime(next_started) if isinstance(next_started, str) and next_started else None
            if next_started and parsed is None:
                return Response({'detail': 'started_at の形式が不正です。'}, status=status.HTTP_400_BAD_REQUEST)
            started_at = normalize_input_datetime(parsed)

        if 'ended_at' in payload:
            next_ended = payload.get('ended_at')
            parsed = parse_datetime(next_ended) if isinstance(next_ended, str) and next_ended else None
            if next_ended and parsed is None:
                return Response({'detail': 'ended_at の形式が不正です。'}, status=status.HTTP_400_BAD_REQUEST)
            ended_at = normalize_input_datetime(parsed)

        if 'production_qty' in payload:
            try:
                production_qty = Decimal(str(payload.get('production_qty') or 0))
            except (InvalidOperation, TypeError, ValueError):
                return Response({'detail': 'production_qty の形式が不正です。'}, status=status.HTTP_400_BAD_REQUEST)
            if production_qty < 0:
                return Response({'detail': 'production_qty は0以上で入力してください。'}, status=status.HTTP_400_BAD_REQUEST)

        if 'defect_qty' in payload:
            try:
                defect_qty = int(payload.get('defect_qty') or 0)
            except (TypeError, ValueError):
                return Response({'detail': 'defect_qty の形式が不正です。'}, status=status.HTTP_400_BAD_REQUEST)
            if defect_qty < 0:
                return Response({'detail': 'defect_qty は0以上で入力してください。'}, status=status.HTTP_400_BAD_REQUEST)

        if started_at and ended_at and ended_at < started_at:
            return Response({'detail': '終了時刻は開始時刻以降にしてください。'}, status=status.HTTP_400_BAD_REQUEST)

        is_countable = is_countable_session_for_actual(session.session_type, session.end_action)
        old_qty = int(session.production_qty or 0) if is_countable else 0
        new_qty = int(production_qty or 0) if is_countable else 0

        old_defect = int(session.defect_qty or 0)
        defect_delta = defect_qty - old_defect

        if 'operator_name' in payload:
            operator_name = str(payload.get('operator_name') or '').strip()
        else:
            operator_name = None

        update_fields = [
            'started_at', 'ended_at', 'production_qty', 'defect_qty',
            'status', 'duration_seconds', 'updated_at',
        ]

        with transaction.atomic():
            if product_changed and old_qty:
                adjust_backlog_actual_for_session(session, -old_qty)
                adjust_coproduct_children_backlog(session, -old_qty)
                apply_delta_to_inventory_and_progress(session, -old_qty)

            session.started_at = started_at
            session.ended_at = ended_at
            session.production_qty = production_qty
            session.defect_qty = defect_qty

            if operator_name is not None:
                session.operator_name = operator_name
                update_fields.append('operator_name')
                if session.start_record_id:
                    ProcessRealtimeRecord.objects.filter(id=session.start_record_id).update(operator_name=operator_name)
                if session.end_record_id:
                    ProcessRealtimeRecord.objects.filter(id=session.end_record_id).update(operator_name=operator_name)
            session.status = 'CLOSED' if ended_at else 'OPEN'
            if started_at and ended_at and ended_at >= started_at:
                session.duration_seconds = int((ended_at - started_at).total_seconds())
            else:
                session.duration_seconds = 0

            if product_changed:
                session.product = new_product
                session.product_code = new_product.product_code
                session.product_name = new_product.product_name or ''
                update_fields += ['product_id', 'product_code', 'product_name']

            session.save(update_fields=update_fields)
            rebuild_session_production_records(session)

            if product_changed:
                if new_qty:
                    adjust_backlog_actual_for_session(session, new_qty)
                    adjust_coproduct_children_backlog(session, new_qty)
                    update_coproduct_children_records(session, production_qty)
                    apply_delta_to_inventory_and_progress(session, new_qty)
            else:
                delta = new_qty - old_qty
                if delta:
                    adjust_backlog_actual_for_session(session, delta)
                    adjust_coproduct_children_backlog(session, delta)
                    update_coproduct_children_records(session, production_qty)
                    apply_delta_to_inventory_and_progress(session, delta)

            if defect_delta:
                adjust_backlog_scrap_for_session(session, defect_delta)
            after_snapshot = serialize_session_snapshot(session)
            if before_snapshot != after_snapshot:
                changed_by = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
                create_session_change_history(
                    session_obj=session,
                    operation_type='UPDATE',
                    reason=change_reason,
                    changed_by=changed_by,
                    before_data=before_snapshot,
                    after_data=after_snapshot,
                )
            recalculate_inventory_after_session_change(session)

        serializer = ProcessWorkSessionSerializer(session)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='session-history')
    def session_history(self, request):
        queryset = ProcessWorkSessionChangeHistory.objects.select_related(
            'session', 'process', 'product', 'changed_by',
        )

        session_id = request.query_params.get('session_id')
        if session_id:
            queryset = queryset.filter(session_record_id=session_id)

        operation_type = str(request.query_params.get('operation_type') or '').strip().upper()
        if operation_type:
            queryset = queryset.filter(operation_type=operation_type)

        start_date = request.query_params.get('start_date')
        if start_date:
            d = parse_date(start_date)
            if d:
                queryset = queryset.filter(changed_at__gte=build_business_boundary_datetime(d))

        end_date = request.query_params.get('end_date')
        if end_date:
            d = parse_date(end_date)
            if d:
                queryset = queryset.filter(changed_at__lt=build_business_boundary_datetime(d, day_offset=1))

        limit = request.query_params.get('limit')
        try:
            limit_value = int(limit) if limit is not None else 300
        except ValueError:
            limit_value = 300
        limit_value = max(1, min(limit_value, 1000))

        serializer = ProcessWorkSessionChangeHistorySerializer(
            queryset.order_by('-changed_at', '-id')[:limit_value],
            many=True,
        )
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='status')
    def status(self, request):
        line_id = request.query_params.get('line_id')
        if not line_id:
            return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        processes = Process.objects.filter(line_id=line_id, is_active=True).order_by('process_code')
        process_ids = list(processes.values_list('id', flat=True))
        if not process_ids:
            return Response([])

        business_today = get_business_today()
        start_dt = datetime.combine(business_today, time(DAY_BOUNDARY_HOUR, 0))
        end_dt = start_dt + timedelta(days=1) - timedelta(microseconds=1)
        if settings.USE_TZ:
            start_dt = timezone.make_aware(start_dt)
            end_dt = timezone.make_aware(end_dt)

        copro_child_ids = set()
        copro_boms = BOM.objects.filter(is_coproduct=True, is_active=True).prefetch_related('items')
        for bom in copro_boms:
            for item in bom.items.all():
                if item.child_product_id:
                    copro_child_ids.add(item.child_product_id)

        plan_qs = LineBacklog.objects.filter(
            line_id=line_id,
            plan_date=business_today,
            process_id__in=process_ids,
        )
        if copro_child_ids:
            plan_qs = plan_qs.exclude(product_id__in=copro_child_ids)
        plan_qs = plan_qs.values('process_id').annotate(total=Sum('plan_qty'))
        plan_map = {row['process_id']: row['total'] or 0 for row in plan_qs}

        output_qs = ProcessRealtimeRecord.objects.filter(
            process_id__in=process_ids,
            record_type='PRODUCTION',
            timestamp__gte=start_dt,
            timestamp__lte=end_dt,
        ).values('process_id').annotate(total=Sum('qty'))
        output_map = {row['process_id']: row['total'] or 0 for row in output_qs}

        state_map = {}
        latest_state_qs = ProcessRealtimeRecord.objects.filter(
            process_id__in=process_ids,
            equipment_state__isnull=False,
        ).order_by('-timestamp')
        for rec in latest_state_qs:
            if rec.process_id in state_map:
                continue
            state_map[rec.process_id] = {
                'state': rec.equipment_state,
                'timestamp': rec.timestamp,
            }

        product_map = {}
        latest_product_qs = ProcessRealtimeRecord.objects.filter(
            process_id__in=process_ids,
            record_type='PRODUCTION',
        ).order_by('-timestamp')
        for rec in latest_product_qs:
            if rec.process_id in product_map:
                continue
            code = (rec.product_code or '').strip() or None
            name = (rec.product_name or '').strip() or None
            if not code and not name:
                continue
            product_map[rec.process_id] = {
                'code': code,
                'name': name,
            }

        state_labels = dict(ProcessRealtimeRecord.EQUIPMENT_STATE_CHOICES)
        result = []
        for process in processes:
            today_plan = plan_map.get(process.id, 0) or 0
            today_output = output_map.get(process.id, 0) or 0
            if today_plan:
                achievement_rate = round((float(today_output) / float(today_plan)) * 100, 1)
            else:
                achievement_rate = 0
            progress = achievement_rate if today_plan else 0
            state_info = state_map.get(process.id, {})
            state = state_info.get('state') or 'STOPPED'
            product_info = product_map.get(process.id, {})

            result.append({
                'id': process.id,
                'process': process.id,
                'process_code': process.process_code,
                'process_name': process.process_name,
                'current_state': state,
                'state_display': state_labels.get(state, state),
                'state_started_at': state_info.get('timestamp'),
                'today_output': float(today_output),
                'today_plan': float(today_plan),
                'achievement_rate': achievement_rate,
                'current_product_code': product_info.get('code'),
                'current_product_name': product_info.get('name'),
                'last_update': state_info.get('timestamp'),
                'progress': progress,
            })

        return Response(result)

    @action(detail=True, methods=['get'], url_path='scrap-breakdown')
    def scrap_breakdown(self, request, pk=None):
        """仕損のBOM展開明細を返す"""
        record = self.get_object()
        return Response(get_scrap_breakdown(record))

    @action(detail=True, methods=['post'], url_path='mark-replenished')
    def mark_replenished(self, request, pk=None):
        """仕損補充完了フラグを立てる（全明細まとめて）"""
        record = self.get_object()
        try:
            result = mark_scrap_replenished(record, user=getattr(request, 'user', None))
        except ScrapServiceError as exc:
            return Response({'detail': exc.detail}, status=exc.status_code)
        return Response(result)

    @action(detail=True, methods=['post'], url_path='mark-detail-replenished')
    def mark_detail_replenished(self, request, pk=None):
        """仕損明細単位で補充完了を立てる"""
        record = self.get_object()
        try:
            result = mark_scrap_detail_replenished(
                record,
                detail_id=request.data.get('detail_id'),
                user=getattr(request, 'user', None),
            )
        except ScrapServiceError as exc:
            return Response({'detail': exc.detail}, status=exc.status_code)
        return Response(result)

    @action(detail=True, methods=['post'], url_path='scrap-disposition')
    def scrap_disposition(self, request, pk=None):
        """仕損の判定（戻し/仕損確定）"""
        record = self.get_object()
        user = getattr(request, 'user', None)
        decided_by = None
        if user and getattr(user, 'is_authenticated', False):
            decided_by = getattr(user, 'username', None)
        try:
            result = process_scrap_disposition(
                record,
                action=request.data.get('action'),
                qty_input=request.data.get('qty'),
                decided_by=decided_by,
            )
        except ScrapServiceError as exc:
            return Response({'detail': exc.detail}, status=exc.status_code)

        return Response(result)

    @action(detail=False, methods=['get'], url_path='gantt-plan-qty')
    def gantt_plan_qty(self, request):
        return Response(
            get_gantt_plan_qty(
                line_id=request.query_params.get('line_id'),
                process_id=request.query_params.get('process_id'),
                dates_str=request.query_params.get('dates', ''),
            )
        )
