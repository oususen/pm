"""定時タスク設定系サービス"""
import re

from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response

from masters.models import Line, Process
from production.models_schedule_config import ScheduleConfig
from production.serializers import ScheduleConfigSerializer


def get_configs(request=None, logger=None):
    _ensure_defaults()
    configs = ScheduleConfig.objects.select_related('line', 'process').order_by(
        'task_name',
        'execution_order',
        'line__line_code',
    )
    serializer = ScheduleConfigSerializer(configs, many=True)
    return Response(serializer.data)


def save_config(request, logger=None):
    payload = _normalize_config_payload(request.data)
    if isinstance(payload, Response):
        return payload

    target_result = _resolve_target_objects(payload)
    if isinstance(target_result, Response):
        return target_result

    line_obj, process_obj = target_result
    config = _resolve_or_create_config(payload, line_obj, process_obj)
    if isinstance(config, Response):
        return config

    if payload['task_name'] == 'AUTO_PLAN' and getattr(config, 'auto_plan_sequence_locked', False) and not payload['from_sequence_ui']:
        return Response(
            {'detail': '自動計画は順序運用モードです。順序設定画面から編集してください。'},
            status=status.HTTP_409_CONFLICT,
        )

    _apply_config_values(
        config=config,
        payload=payload,
        line_obj=line_obj,
        process_obj=process_obj,
        user=request.user if getattr(request, 'user', None) and request.user.is_authenticated else None,
    )
    _save_notify_users(config=config, payload=payload)

    serializer = ScheduleConfigSerializer(config)
    return Response(serializer.data)


def _ensure_defaults():
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
        start=1,
    ):
        ScheduleConfig.objects.get_or_create(
            task_name='AUTO_PLAN',
            line=line,
            defaults={**template, 'execution_order': idx},
        )


def _to_bool(value, default=False):
    if value in (None, ''):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on')
    return bool(value)


def _normalize_config_payload(request_data):
    payload = {
        'config_id': request_data.get('id') or request_data.get('config_id'),
        'task_name': str(request_data.get('task_name', 'INVENTORY_RECALC')).upper(),
        'line_id': request_data.get('line'),
        'process_id': request_data.get('process'),
        'scheduled_hour': request_data.get('scheduled_hour'),
        'scheduled_minute': request_data.get('scheduled_minute', 0),
        'scheduled_dom': request_data.get('scheduled_dom'),
        'execution_order': request_data.get('execution_order'),
        'range_base_day': (request_data.get('range_base_day') or 'TODAY').upper(),
        'range_days_after': request_data.get('range_days_after', 45),
        'kubota_due_auto_link_enabled': _to_bool(request_data.get('kubota_due_auto_link_enabled', True), True),
        'average_days_window': request_data.get('average_days_window', 60),
        'safety_days': request_data.get('safety_days', 1),
        'is_enabled': request_data.get('is_enabled', True),
        'include_current_month': _to_bool(request_data.get('include_current_month', False), False),
        'include_next_month': _to_bool(request_data.get('include_next_month', True), True),
        'include_second_month': _to_bool(request_data.get('include_second_month', False), False),
        'include_third_month': _to_bool(request_data.get('include_third_month', False), False),
        'from_sequence_ui': _to_bool(request_data.get('from_sequence_ui', False), False),
        'notify_user_ids': request_data.get('notify_users', None),
        'notify_user_codes': request_data.get('notify_user_codes', None),
    }
    validation_error = _validate_config_payload(payload)
    if validation_error is not None:
        return validation_error
    return payload


def _validate_config_payload(payload):
    try:
        payload['scheduled_hour'] = int(payload['scheduled_hour'])
        payload['scheduled_minute'] = int(payload['scheduled_minute'])
    except (TypeError, ValueError):
        return Response({'detail': '時刻は整数で指定してください'}, status=status.HTTP_400_BAD_REQUEST)
    if not (0 <= payload['scheduled_hour'] <= 23) or not (0 <= payload['scheduled_minute'] <= 59):
        return Response({'detail': '時刻の範囲が不正です'}, status=status.HTTP_400_BAD_REQUEST)

    if payload['scheduled_dom'] not in (None, ''):
        try:
            payload['scheduled_dom'] = int(payload['scheduled_dom'])
        except (TypeError, ValueError):
            return Response({'detail': '実行日は1-31の整数で指定してください'}, status=status.HTTP_400_BAD_REQUEST)
        if not (1 <= payload['scheduled_dom'] <= 31):
            return Response({'detail': '実行日は1-31の範囲で指定してください'}, status=status.HTTP_400_BAD_REQUEST)
    else:
        payload['scheduled_dom'] = None

    if payload['execution_order'] in (None, ''):
        payload['execution_order'] = None
    else:
        try:
            payload['execution_order'] = int(payload['execution_order'])
        except (TypeError, ValueError):
            return Response({'detail': '実行順は整数で指定してください'}, status=status.HTTP_400_BAD_REQUEST)
        if payload['execution_order'] < 1:
            return Response({'detail': '実行順は1以上で指定してください'}, status=status.HTTP_400_BAD_REQUEST)

    if isinstance(payload['is_enabled'], str):
        payload['is_enabled'] = payload['is_enabled'].lower() in ('true', '1', 'yes')

    allowed_base_days = {'TODAY', 'YESTERDAY', 'TWO_DAYS_AGO'}
    if payload['range_base_day'] not in allowed_base_days:
        return Response({'detail': '開始基準日は 今日 / 昨日 / 一昨日 から選択してください'}, status=status.HTTP_400_BAD_REQUEST)

    for key, label, min_value, max_value in (
        ('range_days_after', '何日後', 0, 365),
        ('average_days_window', '実行日からの平均日数', 1, 365),
        ('safety_days', '安全在庫日数', 1, 365),
    ):
        try:
            payload[key] = int(payload[key])
        except (TypeError, ValueError):
            return Response({'detail': f'{label}は整数で指定してください'}, status=status.HTTP_400_BAD_REQUEST)
        if not (min_value <= payload[key] <= max_value):
            return Response({'detail': f'{label}は{min_value}〜{max_value}で指定してください'}, status=status.HTTP_400_BAD_REQUEST)

    return None


def _resolve_target_objects(payload):
    task_name = payload['task_name']
    line_obj = None
    process_obj = None
    safety_task_names = {'AUTO_SAFETY_STOCK_INTERNAL', 'AUTO_SAFETY_STOCK_PURCHASE'}

    if task_name == 'AUTO_PLAN':
        if not payload['line_id']:
            return Response({'detail': 'ラインを指定してください'}, status=status.HTTP_400_BAD_REQUEST)
        line_obj = Line.objects.filter(id=payload['line_id'], line_type__in=['PROD', 'OUTSOURCE', 'PURCHASE']).first()
        if not line_obj:
            return Response({'detail': '指定されたラインが見つかりません（社内/外作/購買ラインのみ設定可能）'}, status=status.HTTP_400_BAD_REQUEST)
        if not (
            payload['include_current_month']
            or payload['include_next_month']
            or payload['include_second_month']
            or payload['include_third_month']
        ):
            return Response({'detail': '実行期間を1つ以上選択してください'}, status=status.HTTP_400_BAD_REQUEST)

    if task_name in safety_task_names and payload['scheduled_dom'] is None:
        return Response({'detail': '安全在庫タスクは実行日（1-31）を指定してください'}, status=status.HTTP_400_BAD_REQUEST)

    if task_name == 'PLAN_TO_ACTUAL_COPY':
        if not payload['line_id']:
            return Response({'detail': 'ラインを指定してください'}, status=status.HTTP_400_BAD_REQUEST)
        if not payload['process_id']:
            return Response({'detail': '工程を指定してください'}, status=status.HTTP_400_BAD_REQUEST)
        line_obj = Line.objects.filter(id=payload['line_id'], is_active=True).first()
        if not line_obj:
            return Response({'detail': '指定されたラインが見つかりません'}, status=status.HTTP_400_BAD_REQUEST)
        process_obj = Process.objects.filter(id=payload['process_id'], line_id=payload['line_id']).first()
        if not process_obj:
            return Response({'detail': '指定された工程が見つかりません（ライン不一致を含む）'}, status=status.HTTP_400_BAD_REQUEST)

    return line_obj, process_obj


def _resolve_or_create_config(payload, line_obj, process_obj):
    if payload['config_id']:
        config = ScheduleConfig.objects.filter(id=payload['config_id']).first()
        if not config:
            return Response({'detail': '設定が見つかりません'}, status=status.HTTP_404_NOT_FOUND)
        return config

    config, _ = ScheduleConfig.objects.get_or_create(
        task_name=payload['task_name'],
        line=line_obj,
        process=process_obj,
        defaults={
            'scheduled_hour': payload['scheduled_hour'],
            'scheduled_minute': payload['scheduled_minute'],
            'scheduled_dom': payload['scheduled_dom'],
            'range_base_day': payload['range_base_day'],
            'range_days_after': payload['range_days_after'],
            'kubota_due_auto_link_enabled': payload['kubota_due_auto_link_enabled'],
            'average_days_window': payload['average_days_window'],
            'safety_days': payload['safety_days'],
            'is_enabled': payload['is_enabled'],
            'include_current_month': payload['include_current_month'],
            'include_next_month': payload['include_next_month'],
            'include_second_month': payload['include_second_month'],
            'include_third_month': payload['include_third_month'],
        },
    )
    return config


def _apply_config_values(*, config, payload, line_obj, process_obj, user):
    config.scheduled_hour = payload['scheduled_hour']
    config.scheduled_minute = payload['scheduled_minute']
    config.scheduled_dom = payload['scheduled_dom']
    config.range_base_day = payload['range_base_day']
    config.range_days_after = payload['range_days_after']
    config.kubota_due_auto_link_enabled = payload['kubota_due_auto_link_enabled']
    config.average_days_window = payload['average_days_window']
    config.safety_days = payload['safety_days']
    config.is_enabled = payload['is_enabled']
    config.include_current_month = payload['include_current_month']
    config.include_next_month = payload['include_next_month']
    config.include_second_month = payload['include_second_month']
    config.include_third_month = payload['include_third_month']
    if payload['execution_order'] is not None:
        config.execution_order = payload['execution_order']
    if payload['task_name'] == 'AUTO_PLAN':
        config.auto_plan_sequence_locked = payload['from_sequence_ui']
    if line_obj:
        config.line = line_obj
    if payload['task_name'] == 'PLAN_TO_ACTUAL_COPY':
        config.process = process_obj
    config.updated_by = user

    update_fields = [
        'scheduled_hour', 'scheduled_minute', 'scheduled_dom',
        'range_base_day', 'range_days_after', 'kubota_due_auto_link_enabled', 'average_days_window', 'safety_days',
        'is_enabled', 'include_current_month', 'include_next_month', 'include_second_month', 'include_third_month',
        'line', 'updated_at', 'updated_by',
    ]
    if payload['task_name'] == 'PLAN_TO_ACTUAL_COPY':
        update_fields.append('process')
    if payload['execution_order'] is not None:
        update_fields.append('execution_order')
    if payload['task_name'] == 'AUTO_PLAN':
        update_fields.append('auto_plan_sequence_locked')
    config.save(update_fields=update_fields)


def _save_notify_users(*, config, payload):
    if payload['notify_user_ids'] is not None:
        config.notify_users.set(payload['notify_user_ids'])
        return

    if payload['notify_user_codes'] is None:
        return

    codes = payload['notify_user_codes']
    if isinstance(codes, str):
        codes = [code for code in re.split(r'[,\s]+', codes) if code]
    try:
        iter(codes)
    except TypeError:
        codes = []

    User = get_user_model()
    users = User.objects.filter(
        Q(profile__employee_code__in=codes) | Q(username__in=codes) | Q(email__in=codes)
    ).distinct()
    config.notify_users.set(users)
