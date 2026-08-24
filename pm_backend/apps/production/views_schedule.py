import logging

from django.db.models import Q
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from masters.models import Line, Process
from production.models_purchase_actual_reconcile import (
    PurchaseActualReconcileReport,
    PurchaseActualReconcileReportDetail,
)
from production.models_production_actual_reconcile import (
    ProductionActualReconcileReport,
    ProductionActualReconcileReportDetail,
)
from production.models_schedule_config import ScheduleConfig, ScheduleRunLog
from production.serializers import (
    ScheduleConfigSerializer,
    ScheduleRunLogSerializer,
    PurchaseActualReconcileReportSerializer,
    PurchaseActualReconcileReportDetailSerializer,
    ProductionActualReconcileReportSerializer,
    ProductionActualReconcileReportDetailSerializer,
)

logger = logging.getLogger(__name__)


def _is_stale_cancel_requested_run(config):
    if not config or getattr(config, 'last_run_status', None) != 'RUNNING':
        return False
    message = str(getattr(config, 'last_run_message', '') or '')
    last_run_at = getattr(config, 'last_run_at', None)
    if '[CANCEL_REQUESTED]' not in message or not last_run_at:
        return False
    return last_run_at.date() < datetime.now().date()


from datetime import datetime


class ScheduleConfigView(APIView):
    """定時タスクスケジュール設定API"""

    def _ensure_defaults(self):
        """既定設定を補完（自動計画は社内/外作/購買ライン分を作成）"""
        inventory_defaults = [
            ('INVENTORY_RECALC', 7, 0, True),
            ('PICKUP_ONLY', 7, 30, False),
            ('INVENTORY_ONLY', 8, 0, False),
            ('PROGRESS_ONLY', 8, 30, False),
            ('KUBOTA_SAKAI_DUE_SYNC', 7, 45, False),
            ('AUTO_PURCHASE_ORDER_CHECK', 6, 30, False),
            ('PURCHASE_ACTUAL_RECONCILE_CHECK', 2, 0, False),
            ('PRODUCTION_ACTUAL_RECONCILE_CHECK', 2, 30, False),
            ('CONTAINER_IMPORT_TMP_CLEANUP', 3, 0, False),
        ]
        for task_name, hour, minute, is_enabled in inventory_defaults:
            ScheduleConfig.objects.get_or_create(
                task_name=task_name,
                line=None,
                defaults={
                    'scheduled_hour': hour,
                    'scheduled_minute': minute,
                    'is_enabled': is_enabled,
                    'range_base_day': 'TODAY',
                    'range_days_after': 45,
                },
            )
        ScheduleConfig.objects.get_or_create(
            task_name='ORDER_EXPANSION',
            line=None,
            defaults={
                'scheduled_hour': 6,
                'scheduled_minute': 0,
                'is_enabled': False,
                'range_base_day': 'TODAY',
                'range_days_after': 45,
            },
        )
        safety_defaults = [
            ('AUTO_SAFETY_STOCK_INTERNAL', 1, 3, 0, 60, 1, False),
            ('AUTO_SAFETY_STOCK_PURCHASE', 1, 3, 30, 60, 1, False),
        ]
        for task_name, dom, hour, minute, average_days_window, safety_days, is_enabled in safety_defaults:
            ScheduleConfig.objects.get_or_create(
                task_name=task_name,
                line=None,
                defaults={
                    'scheduled_dom': dom,
                    'scheduled_hour': hour,
                    'scheduled_minute': minute,
                    'is_enabled': is_enabled,
                    'range_base_day': 'TODAY',
                    'range_days_after': 45,
                    'average_days_window': average_days_window,
                    'safety_days': safety_days,
                },
            )
        base_plan = ScheduleConfig.objects.filter(task_name='AUTO_PLAN', line__isnull=False).first()
        if not base_plan:
            base_plan = ScheduleConfig.objects.filter(task_name='AUTO_PLAN', line__isnull=True).first()
        template = {
            'scheduled_hour': getattr(base_plan, 'scheduled_hour', 3) or 3,
            'scheduled_minute': getattr(base_plan, 'scheduled_minute', 0) or 0,
            'scheduled_dom': getattr(base_plan, 'scheduled_dom', 1),
            'is_enabled': getattr(base_plan, 'is_enabled', True),
            'include_next_month': getattr(base_plan, 'include_next_month', True),
            'include_second_month': getattr(base_plan, 'include_second_month', False),
            'include_third_month': getattr(base_plan, 'include_third_month', False),
        }
        target_types = ['PROD', 'OUTSOURCE', 'PURCHASE']
        for idx, line in enumerate(
            Line.objects.filter(is_active=True, line_type__in=target_types).order_by('line_type', 'line_code', 'id'),
            start=1
        ):
            ScheduleConfig.objects.get_or_create(
                task_name='AUTO_PLAN',
                line=line,
                defaults={**template, 'execution_order': idx},
            )

    def get(self, request):
        self._ensure_defaults()
        configs = ScheduleConfig.objects.select_related('line', 'process').order_by('task_name', 'execution_order', 'line__line_code')
        serializer = ScheduleConfigSerializer(configs, many=True)
        return Response(serializer.data)

    def post(self, request):
        config_id = request.data.get('id') or request.data.get('config_id')
        task_name = str(request.data.get('task_name', 'INVENTORY_RECALC')).upper()
        line_id = request.data.get('line')
        process_id = request.data.get('process')

        def to_bool(val, default=False):
            if val in (None, ''):
                return default
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                return val.lower() in ('true', '1', 'yes', 'on')
            return bool(val)

        scheduled_hour = request.data.get('scheduled_hour')
        scheduled_minute = request.data.get('scheduled_minute', 0)
        scheduled_dom = request.data.get('scheduled_dom')
        execution_order = request.data.get('execution_order')
        range_base_day = (request.data.get('range_base_day') or 'TODAY').upper()
        range_days_after = request.data.get('range_days_after', 45)
        average_days_window = request.data.get('average_days_window', 60)
        safety_days = request.data.get('safety_days', 1)
        is_enabled = request.data.get('is_enabled', True)
        include_current_month = to_bool(request.data.get('include_current_month', False), False)
        include_next_month = to_bool(request.data.get('include_next_month', True), True)
        include_second_month = to_bool(request.data.get('include_second_month', False), False)
        include_third_month = to_bool(request.data.get('include_third_month', False), False)
        from_sequence_ui = to_bool(request.data.get('from_sequence_ui', False), False)

        try:
            scheduled_hour = int(scheduled_hour)
            scheduled_minute = int(scheduled_minute)
        except (TypeError, ValueError):
            return Response(
                {'detail': '時刻は整数で指定してください'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not (0 <= scheduled_hour <= 23) or not (0 <= scheduled_minute <= 59):
            return Response(
                {'detail': '時刻の範囲が不正です'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if scheduled_dom not in (None, '',):
            try:
                scheduled_dom = int(scheduled_dom)
            except (TypeError, ValueError):
                return Response({'detail': '実行日は1-31の整数で指定してください'}, status=status.HTTP_400_BAD_REQUEST)
            if not (1 <= scheduled_dom <= 31):
                return Response({'detail': '実行日は1-31の範囲で指定してください'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            scheduled_dom = None
        if execution_order in (None, ''):
            execution_order = None
        else:
            try:
                execution_order = int(execution_order)
            except (TypeError, ValueError):
                return Response({'detail': '実行順は整数で指定してください'}, status=status.HTTP_400_BAD_REQUEST)
            if execution_order < 1:
                return Response({'detail': '実行順は1以上で指定してください'}, status=status.HTTP_400_BAD_REQUEST)

        if isinstance(is_enabled, str):
            is_enabled = is_enabled.lower() in ('true', '1', 'yes')

        allowed_base_days = {'TODAY', 'YESTERDAY', 'TWO_DAYS_AGO'}
        if range_base_day not in allowed_base_days:
            return Response(
                {'detail': '開始基準日は 今日 / 昨日 / 一昨日 から選択してください'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            range_days_after = int(range_days_after)
        except (TypeError, ValueError):
            return Response(
                {'detail': '何日後は整数で指定してください'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not (0 <= range_days_after <= 365):
            return Response(
                {'detail': '何日後は0〜365で指定してください'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            average_days_window = int(average_days_window)
        except (TypeError, ValueError):
            return Response(
                {'detail': '実行日からの平均日数は整数で指定してください'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not (1 <= average_days_window <= 365):
            return Response(
                {'detail': '実行日からの平均日数は1〜365で指定してください'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            safety_days = int(safety_days)
        except (TypeError, ValueError):
            return Response(
                {'detail': '安全在庫日数は整数で指定してください'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not (1 <= safety_days <= 365):
            return Response(
                {'detail': '安全在庫日数は1〜365で指定してください'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        line_obj = None
        process_obj = None
        safety_task_names = {'AUTO_SAFETY_STOCK_INTERNAL', 'AUTO_SAFETY_STOCK_PURCHASE'}
        if task_name == 'AUTO_PLAN':
            if not line_id:
                return Response({'detail': 'ラインを指定してください'}, status=status.HTTP_400_BAD_REQUEST)
            line_obj = Line.objects.filter(id=line_id, line_type__in=['PROD', 'OUTSOURCE', 'PURCHASE']).first()
            if not line_obj:
                return Response({'detail': '指定されたラインが見つかりません（社内/外作/購買ラインのみ設定可能）'}, status=status.HTTP_400_BAD_REQUEST)
            if not (include_current_month or include_next_month or include_second_month or include_third_month):
                return Response({'detail': '実行期間を1つ以上選択してください'}, status=status.HTTP_400_BAD_REQUEST)
        if task_name in safety_task_names and scheduled_dom is None:
            return Response({'detail': '安全在庫タスクは実行日（1-31）を指定してください'}, status=status.HTTP_400_BAD_REQUEST)
        if task_name == 'PLAN_TO_ACTUAL_COPY':
            if not line_id:
                return Response({'detail': 'ラインを指定してください'}, status=status.HTTP_400_BAD_REQUEST)
            if not process_id:
                return Response({'detail': '工程を指定してください'}, status=status.HTTP_400_BAD_REQUEST)
            line_obj = Line.objects.filter(id=line_id, is_active=True).first()
            if not line_obj:
                return Response({'detail': '指定されたラインが見つかりません'}, status=status.HTTP_400_BAD_REQUEST)
            process_obj = Process.objects.filter(id=process_id, line_id=line_id).first()
            if not process_obj:
                return Response({'detail': '指定された工程が見つかりません（ライン不一致を含む）'}, status=status.HTTP_400_BAD_REQUEST)

        if config_id:
            config = ScheduleConfig.objects.filter(id=config_id).first()
            if not config:
                return Response({'detail': '設定が見つかりません'}, status=status.HTTP_404_NOT_FOUND)
        else:
            config, _ = ScheduleConfig.objects.get_or_create(
                task_name=task_name,
                line=line_obj,
                process=process_obj,
                defaults={
                    'scheduled_hour': scheduled_hour,
                    'scheduled_minute': scheduled_minute,
                    'scheduled_dom': scheduled_dom,
                    'range_base_day': range_base_day,
                    'range_days_after': range_days_after,
                    'average_days_window': average_days_window,
                    'safety_days': safety_days,
                    'is_enabled': is_enabled,
                    'include_current_month': include_current_month,
                    'include_next_month': include_next_month,
                    'include_second_month': include_second_month,
                    'include_third_month': include_third_month,
                },
            )

        if task_name == 'AUTO_PLAN' and getattr(config, 'auto_plan_sequence_locked', False) and not from_sequence_ui:
            return Response(
                {'detail': '自動計画は順序運用モードです。順序設定画面から編集してください。'},
                status=status.HTTP_409_CONFLICT,
            )

        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        config.scheduled_hour = scheduled_hour
        config.scheduled_minute = scheduled_minute
        config.scheduled_dom = scheduled_dom
        config.range_base_day = range_base_day
        config.range_days_after = range_days_after
        config.average_days_window = average_days_window
        config.safety_days = safety_days
        config.is_enabled = is_enabled
        config.include_current_month = include_current_month
        config.include_next_month = include_next_month
        config.include_second_month = include_second_month
        config.include_third_month = include_third_month
        if execution_order is not None:
            config.execution_order = execution_order
        if task_name == 'AUTO_PLAN':
            config.auto_plan_sequence_locked = from_sequence_ui
        if line_obj:
            config.line = line_obj
        if task_name == 'PLAN_TO_ACTUAL_COPY':
            config.process = process_obj
        config.updated_by = user
        update_fields = [
            'scheduled_hour', 'scheduled_minute', 'scheduled_dom',
            'range_base_day', 'range_days_after', 'average_days_window', 'safety_days',
            'is_enabled', 'include_current_month', 'include_next_month', 'include_second_month', 'include_third_month',
            'line', 'updated_at', 'updated_by',
        ]
        if task_name == 'PLAN_TO_ACTUAL_COPY':
            update_fields.append('process')
        if execution_order is not None:
            update_fields.append('execution_order')
        if task_name == 'AUTO_PLAN':
            update_fields.append('auto_plan_sequence_locked')
        config.save(update_fields=update_fields)

        notify_user_ids = request.data.get('notify_users', None)
        notify_user_codes = request.data.get('notify_user_codes', None)

        if notify_user_ids is not None:
            config.notify_users.set(notify_user_ids)
        elif notify_user_codes is not None:
            codes = notify_user_codes
            if isinstance(codes, str):
                import re
                codes = [c for c in re.split(r'[,\s]+', codes) if c]
            try:
                iter(codes)
            except TypeError:
                codes = []
            User = get_user_model()
            users = User.objects.filter(
                Q(profile__employee_code__in=codes) | Q(username__in=codes) | Q(email__in=codes)
            ).distinct()
            config.notify_users.set(users)

        serializer = ScheduleConfigSerializer(config)
        return Response(serializer.data)


class ScheduleRunLogView(APIView):
    """定時タスク実行履歴（直近分）"""

    def get(self, request):
        config_id = request.query_params.get('config_id')
        if not config_id:
            return Response({'detail': 'config_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        logs = ScheduleRunLog.objects.filter(config_id=config_id).order_by('-started_at')[:30]
        serializer = ScheduleRunLogSerializer(logs, many=True)
        return Response(serializer.data)


class ScheduleRunNowView(APIView):
    """定時タスクを手動実行（非同期）"""

    def post(self, request):
        import threading
        from .scheduler.tasks import run_inventory_recalculation
        from .scheduler.tasks_safety_stock import run_auto_safety_stock
        from .scheduler.tasks_auto_plan import run_auto_plan
        from .scheduler.tasks_order_expansion import run_order_expansion
        from .scheduler.tasks_purchase_actual_reconcile import run_purchase_actual_reconcile_check
        from .scheduler.tasks_production_actual_reconcile import run_production_actual_reconcile_check
        from .scheduler.tasks_plan_to_actual import run_plan_to_actual_copy
        from shipping.scheduler_tasks_kubota_sakai_due import run_kubota_sakai_due_sync
        from purchase.order_proposal_views import run_auto_purchase_order_check
        from masters.scheduler.tasks_container_import_cleanup import run_container_import_tmp_cleanup
        task = (request.data.get('task_name') or 'INVENTORY_RECALC').upper()
        task_labels = {
            'INVENTORY_RECALC': '取り込み＋在庫再計算',
            'PICKUP_ONLY': '取り込みのみ',
            'INVENTORY_ONLY': '在庫計算のみ',
            'PROGRESS_ONLY': '進度計算のみ',
            'KUBOTA_SAKAI_DUE_SYNC': 'クボタ堺納期調整 取込+再配分',
            'AUTO_SAFETY_STOCK_INTERNAL': '自動安全在庫（社内）',
            'AUTO_SAFETY_STOCK_PURCHASE': '自動安全在庫（購入品）',
            'AUTO_PURCHASE_ORDER_CHECK': '発注タイミング日次チェック',
            'PURCHASE_ACTUAL_RECONCILE_CHECK': '納入実績整合チェック',
            'PRODUCTION_ACTUAL_RECONCILE_CHECK': '生産実績整合チェック',
            'PLAN_TO_ACTUAL_COPY': '計画実績自動セット',
            'ORDER_EXPANSION': '自動受注展開',
            'CONTAINER_IMPORT_TMP_CLEANUP': '荷姿設定Excel取込 一時ファイル削除',
        }
        config_id = request.data.get('config_id') or request.data.get('id')
        line_id = request.data.get('line')
        try:
            if task == 'AUTO_PLAN':
                if config_id:
                    config = ScheduleConfig.objects.filter(id=config_id).first()
                    if not config:
                        return Response({'detail': '対象設定が見つかりません'}, status=status.HTTP_404_NOT_FOUND)
                    result = run_auto_plan(force=True, config_id=config.id)
                elif line_id:
                    config = ScheduleConfig.objects.filter(task_name='AUTO_PLAN', line_id=line_id).first()
                    if not config:
                        return Response({'detail': '対象設定が見つかりません'}, status=status.HTTP_404_NOT_FOUND)
                    result = run_auto_plan(force=True, config_id=config.id)
                else:
                    result = run_auto_plan(force=True)
                return Response({'detail': '生産計画自動生成を実行しました', **(result or {})})
            elif task in task_labels:
                running_cfg = ScheduleConfig.objects.filter(
                    task_name=task,
                    last_run_status='RUNNING',
                ).first()
                if running_cfg:
                    if _is_stale_cancel_requested_run(running_cfg):
                        stale_message = (running_cfg.last_run_message or '').strip()
                        stale_message = (stale_message + '\n' if stale_message else '') + '前日以前のキャンセル要求済み実行を残留扱いで解放しました。'
                        running_cfg.last_run_status = 'FAILED'
                        running_cfg.last_run_message = stale_message
                        running_cfg.save(update_fields=['last_run_status', 'last_run_message'])
                    else:
                        running_msg = running_cfg.last_run_message or ''
                        if '[CANCEL_REQUESTED]' in running_msg:
                            detail = '既にキャンセル要求済みの実行が停止待ちです。完了までお待ちください。'
                        else:
                            detail = '既に実行中です。完了までお待ちください。必要なら「キャンセル要求」を実行してください。'
                        return Response({'detail': detail}, status=status.HTTP_409_CONFLICT)

                def _run():
                    import django
                    django.db.connections.close_all()
                    try:
                        if task in {'AUTO_SAFETY_STOCK_INTERNAL', 'AUTO_SAFETY_STOCK_PURCHASE'}:
                            run_auto_safety_stock(task_name=task)
                        elif task == 'AUTO_PURCHASE_ORDER_CHECK':
                            run_auto_purchase_order_check()
                        elif task == 'PURCHASE_ACTUAL_RECONCILE_CHECK':
                            run_purchase_actual_reconcile_check(apply_fix=False)
                        elif task == 'PRODUCTION_ACTUAL_RECONCILE_CHECK':
                            run_production_actual_reconcile_check(apply_fix=False)
                        elif task == 'PLAN_TO_ACTUAL_COPY':
                            if not config_id:
                                raise ValueError('PLAN_TO_ACTUAL_COPY は config_id が必要です')
                            run_plan_to_actual_copy(config_id=int(config_id))
                        elif task == 'ORDER_EXPANSION':
                            run_order_expansion()
                        elif task == 'CONTAINER_IMPORT_TMP_CLEANUP':
                            run_container_import_tmp_cleanup()
                        elif task == 'KUBOTA_SAKAI_DUE_SYNC':
                            run_kubota_sakai_due_sync()
                        else:
                            run_inventory_recalculation(task_name=task)
                    except Exception:
                        logger.exception('バックグラウンドタスク実行に失敗')
                        ScheduleConfig.objects.filter(
                            task_name=task,
                            last_run_status='RUNNING',
                        ).update(last_run_status='FAILED', last_run_message='実行中にエラーが発生しました')

                thread = threading.Thread(target=_run, daemon=True)
                thread.start()
                return Response({
                    'detail': f'{task_labels[task]}をバックグラウンドで開始しました。',
                    'async': True,
                })
            else:
                return Response(
                    {'detail': f'未対応のタスクです: {task}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            logger.exception('手動実行に失敗')
            return Response(
                {'detail': f'実行に失敗しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PurchaseActualReconcileReportView(APIView):
    """納入実績整合チェックのレポート取得API"""

    def get(self, request):
        limit = request.query_params.get('limit', 10)
        detail_limit = request.query_params.get('detail_limit', 200)
        report_id = request.query_params.get('report_id')

        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 10
        limit = max(1, min(limit, 50))

        try:
            detail_limit = int(detail_limit)
        except (TypeError, ValueError):
            detail_limit = 200
        detail_limit = max(1, min(detail_limit, 1000))

        report_qs = (
            PurchaseActualReconcileReport.objects
            .select_related('task_config', 'created_by')
            .order_by('-id')
        )
        if report_id:
            report_qs = report_qs.filter(id=report_id)

        reports = list(report_qs[:limit])
        latest = reports[0] if reports else None
        detail_rows = []
        if latest:
            detail_rows = list(
                PurchaseActualReconcileReportDetail.objects
                .filter(report_id=latest.id)
                .select_related('line', 'process', 'product')
                .order_by('plan_date', 'line__line_code', 'product__product_code')[:detail_limit]
            )

        return Response({
            'reports': PurchaseActualReconcileReportSerializer(reports, many=True).data,
            'details': PurchaseActualReconcileReportDetailSerializer(detail_rows, many=True).data,
            'latest_report_id': latest.id if latest else None,
        })


class PurchaseActualReconcileFixView(APIView):
    """納入実績整合チェックの手動修正実行API"""

    def post(self, request):
        from .scheduler.tasks_purchase_actual_reconcile import run_purchase_actual_reconcile_check

        task_name = 'PURCHASE_ACTUAL_RECONCILE_CHECK'
        running = ScheduleConfig.objects.filter(task_name=task_name, last_run_status='RUNNING').exists()
        if running:
            return Response(
                {'detail': '現在整合チェックが実行中です。完了後に再実行してください。'},
                status=status.HTTP_409_CONFLICT,
            )

        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        try:
            result = run_purchase_actual_reconcile_check(apply_fix=True, created_by=user)
            return Response({
                'detail': '修正を実行しました。',
                **result,
            })
        except Exception as e:
            logger.exception('納入実績整合修正に失敗')
            return Response(
                {'detail': f'修正に失敗しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ProductionActualReconcileReportView(APIView):
    """生産実績整合チェックのレポート取得API"""

    def get(self, request):
        limit = request.query_params.get('limit', 10)
        detail_limit = request.query_params.get('detail_limit', 200)
        report_id = request.query_params.get('report_id')

        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 10
        limit = max(1, min(limit, 50))

        try:
            detail_limit = int(detail_limit)
        except (TypeError, ValueError):
            detail_limit = 200
        detail_limit = max(1, min(detail_limit, 1000))

        report_qs = (
            ProductionActualReconcileReport.objects
            .select_related('task_config', 'created_by')
            .order_by('-id')
        )
        if report_id:
            report_qs = report_qs.filter(id=report_id)

        reports = list(report_qs[:limit])
        latest = reports[0] if reports else None
        detail_rows = []
        if latest:
            detail_rows = list(
                ProductionActualReconcileReportDetail.objects
                .filter(report_id=latest.id)
                .select_related('line', 'process', 'product')
                .order_by('plan_date', 'line__line_code', 'product__product_code')[:detail_limit]
            )

        return Response({
            'reports': ProductionActualReconcileReportSerializer(reports, many=True).data,
            'details': ProductionActualReconcileReportDetailSerializer(detail_rows, many=True).data,
            'latest_report_id': latest.id if latest else None,
        })


class ProductionActualReconcileFixView(APIView):
    """生産実績整合チェックの手動修正実行API"""

    def post(self, request):
        from .scheduler.tasks_production_actual_reconcile import run_production_actual_reconcile_check

        task_name = 'PRODUCTION_ACTUAL_RECONCILE_CHECK'
        running = ScheduleConfig.objects.filter(task_name=task_name, last_run_status='RUNNING').exists()
        if running:
            return Response(
                {'detail': '現在整合チェックが実行中です。完了後に再実行してください。'},
                status=status.HTTP_409_CONFLICT,
            )

        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        try:
            result = run_production_actual_reconcile_check(apply_fix=True, created_by=user)
            return Response({
                'detail': '修正を実行しました。',
                **result,
            })
        except Exception as e:
            logger.exception('生産実績整合修正に失敗')
            return Response(
                {'detail': f'修正に失敗しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ScheduleCancelView(APIView):
    """定時タスクのキャンセル要求API（実行中タスク向け）"""

    def post(self, request):
        from .scheduler.tasks import request_task_cancel

        task = (request.data.get('task_name') or 'INVENTORY_RECALC').upper()
        config_id = request.data.get('config_id') or request.data.get('id')
        supported_tasks = {'INVENTORY_RECALC', 'PICKUP_ONLY', 'INVENTORY_ONLY', 'PROGRESS_ONLY'}

        if task not in supported_tasks:
            return Response(
                {'detail': f'このタスクはキャンセル未対応です: {task}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if config_id:
            exists = ScheduleConfig.objects.filter(id=config_id, task_name=task).exists()
            if not exists:
                return Response({'detail': '対象設定が見つかりません'}, status=status.HTTP_404_NOT_FOUND)

        result = request_task_cancel(task)
        if not result.get('ok'):
            if result.get('reason') == 'not_found':
                return Response({'detail': '対象設定が見つかりません'}, status=status.HTTP_404_NOT_FOUND)
            if result.get('reason') == 'not_running':
                return Response({'detail': '現在このタスクは実行中ではありません。'}, status=status.HTTP_409_CONFLICT)
            return Response({'detail': 'キャンセル要求に失敗しました。'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if result.get('already_requested'):
            return Response({'detail': '既にキャンセル要求済みです。停止完了までお待ちください。'})
        return Response({'detail': 'キャンセル要求を受け付けました。安全な区切りで停止します。'})
