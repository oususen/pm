"""LineBacklogViewSet の再計算系サービス"""
from datetime import datetime

from rest_framework import status
from rest_framework.response import Response

from masters.models import Line
from production.models_line_backlog import LineBacklog
from production.services.recalc_start_date import (
    resolve_inventory_effective_start_date,
    resolve_product_recalc_start_date,
)


def recalculate_inventory(viewset, request, **deps):
    self = viewset
    _parse_product_ids = deps.get('parse_product_ids')
    """
    在庫・計画在庫を再計算するAPI

    期待payload: {
        line_id: int (required),
        start_date: str (YYYY-MM-DD, required),
        end_date: str (YYYY-MM-DD, required),
        include_progress: bool (optional, default: True),
        line_final_only: bool (optional, default: False) - Trueの場合はライン最終品のみ計算
        final_only: bool (deprecated, line_final_only を使用) - 後方互換のため残存
        progress_only: bool (optional, default: False) - Trueの場合は進度のみ再計算し在庫をスキップ
        force_from_start: bool (optional, default: False) - Trueの場合は指定開始日を計算起点として尊重
    }
    """
    from production.inventory.inventory_calculator import recalculate_inventory_for_line
    from production.inventory.progress_calculator import ProgressDemandResolutionError

    line_id = request.data.get('line_id')
    start_date = request.data.get('start_date')
    end_date = request.data.get('end_date')
    include_progress_raw = request.data.get('include_progress', True)
    try:
        requested_product_ids = _parse_product_ids(request.data.get('product_ids'))
    except ValueError as e:
        return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    if isinstance(include_progress_raw, str):
        include_progress = include_progress_raw.lower() not in ['false', '0', 'no']
    else:
        include_progress = bool(include_progress_raw)

    line_final_only_raw = request.data.get('line_final_only')
    if line_final_only_raw is None:
        line_final_only_raw = request.data.get('final_only', False)
    if isinstance(line_final_only_raw, str):
        line_final_only = line_final_only_raw.lower() in ['true', '1', 'yes']
    else:
        line_final_only = bool(line_final_only_raw)

    progress_only_raw = request.data.get('progress_only', False)
    if isinstance(progress_only_raw, str):
        progress_only = progress_only_raw.lower() in ['true', '1', 'yes']
    else:
        progress_only = bool(progress_only_raw)

    force_from_start_raw = request.data.get('force_from_start', False)
    if isinstance(force_from_start_raw, str):
        force_from_start = force_from_start_raw.lower() in ['true', '1', 'yes']
    else:
        force_from_start = bool(force_from_start_raw)

    if not line_id:
        return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not start_date or not end_date:
        return Response({'detail': 'start_date and end_date are required'}, status=status.HTTP_400_BAD_REQUEST)

    line_obj = Line.objects.filter(id=line_id).only('calendar_id', 'line_type').first()
    if line_obj and line_obj.line_type == 'PROD' and not line_obj.calendar_id:
        return Response(
            {
                'detail': 'ラインカレンダが設定されていません。ラインマスタからカレンダを設定してください。',
                'code': 'LINE_CALENDAR_MISSING',
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError as e:
        return Response({'detail': f'Invalid date format: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    if force_from_start:
        effective_start_dt = start_dt
        progress_calc_start_date = start_dt if (include_progress or progress_only) else None
    else:
        effective_start_dt = resolve_inventory_effective_start_date(
            line_id,
            start_dt,
            end_dt,
            product_ids=requested_product_ids or None,
            line_final_only=line_final_only,
            include_progress=include_progress or progress_only,
        )
        progress_calc_start_date = None

    try:
        result = recalculate_inventory_for_line(
            line_id,
            effective_start_dt,
            end_dt,
            include_progress=include_progress,
            line_final_only=line_final_only,
            product_ids=requested_product_ids or None,
            progress_only=progress_only,
            progress_calc_start_date=progress_calc_start_date,
            force_from_start=force_from_start,
        )
        record_count = LineBacklog.objects.filter(
            line_id=line_id,
            plan_date__range=[effective_start_dt, end_dt],
        ).count()
        return Response({
            'detail': 'Inventory recalculated successfully',
            'product_count': result.get('product_count', 0),
            'record_count': record_count,
        })
    except ProgressDemandResolutionError as e:
        return Response(
            {
                'detail': str(e),
                'code': 'PROGRESS_STEP_DEMAND_MISSING',
                'errors': e.details,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def recalculate_inventory_for_products(viewset, request, **deps):
    _parse_product_ids = deps.get('parse_product_ids')
    """表示中品番限定の在庫再計算。画面の表示開始日は使わない。"""
    mutable_data = request.data.copy()
    line_id = mutable_data.get('line_id')
    end_date = mutable_data.get('end_date')
    try:
        requested_product_ids = _parse_product_ids(mutable_data.get('product_ids'))
    except ValueError as e:
        return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    progress_only_raw = mutable_data.get('progress_only', False)
    if isinstance(progress_only_raw, str):
        is_progress_only = progress_only_raw.lower() in ('true', '1', 'yes')
    else:
        is_progress_only = bool(progress_only_raw)

    if line_id and end_date:
        try:
            end_dt = datetime.strptime(str(end_date), '%Y-%m-%d').date()
            effective_start_dt = resolve_product_recalc_start_date(
                int(line_id),
                end_dt,
                product_ids=requested_product_ids or None,
                progress_only=is_progress_only,
            )
            mutable_data['start_date'] = effective_start_dt.isoformat()
        except (TypeError, ValueError):
            pass
    request._full_data = mutable_data
    return recalculate_inventory(viewset, request, **deps)


def recalculate_inventory_deep(viewset, request, **deps):
    """
    過去から在庫・進度を深掘り再計算するAPI。
    _resolve_effective_start_date によるLT展開を行わず、指定した start_date をそのまま使う。
    棚卸初期化なしで古い実績データから在庫・進度を巻き直す場合に使用する。

    期待payload: {
        line_id: int (required),
        start_date: str (YYYY-MM-DD, required) - 画面の表示開始日をそのまま渡す
        end_date: str (YYYY-MM-DD, required),
    }
    """
    from production.inventory.inventory_calculator import recalculate_inventory_for_line
    from production.inventory.progress_calculator import ProgressDemandResolutionError

    line_id = request.data.get('line_id')
    start_date = request.data.get('start_date')
    end_date = request.data.get('end_date')
    product_ids = request.data.get('product_ids') or None

    if not line_id:
        return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not start_date or not end_date:
        return Response({'detail': 'start_date and end_date are required'}, status=status.HTTP_400_BAD_REQUEST)

    line_obj = Line.objects.filter(id=line_id).only('calendar_id', 'line_type').first()
    if line_obj and line_obj.line_type == 'PROD' and not line_obj.calendar_id:
        return Response(
            {
                'detail': 'ラインカレンダが設定されていません。ラインマスタからカレンダを設定してください。',
                'code': 'LINE_CALENDAR_MISSING',
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError as e:
        return Response({'detail': f'Invalid date format: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    progress_only_raw = request.data.get('progress_only', False)
    if isinstance(progress_only_raw, str):
        progress_only = progress_only_raw.lower() in ['true', '1', 'yes']
    else:
        progress_only = bool(progress_only_raw)

    try:
        result = recalculate_inventory_for_line(
            line_id,
            start_dt,
            end_dt,
            include_progress=True,
            product_ids=product_ids,
            progress_calc_start_date=start_dt,
            progress_only=progress_only,
            force_from_start=True,
        )
        return Response({
            'detail': '過去からの在庫・進度再計算が完了しました',
            'product_count': result.get('product_count', 0),
            'progress_only': progress_only,
        })
    except ProgressDemandResolutionError as e:
        return Response(
            {
                'detail': str(e),
                'code': 'PROGRESS_STEP_DEMAND_MISSING',
                'errors': e.details,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def recalculate_scrap(viewset, request, **deps):
    _parse_product_ids = deps.get('parse_product_ids')
    """
    仕損数（scrap_qty）を再集計するAPI

    期待payload: {
        line_id: int (required),
        start_date: str (YYYY-MM-DD, required),
        end_date: str (YYYY-MM-DD, required)
    }
    """
    from production.inventory.inventory_calculator import aggregate_scrap_to_backlog

    line_id = request.data.get('line_id')
    start_date = request.data.get('start_date')
    end_date = request.data.get('end_date')
    try:
        requested_product_ids = _parse_product_ids(request.data.get('product_ids'))
    except ValueError as e:
        return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    if not line_id:
        return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not start_date or not end_date:
        return Response({'detail': 'start_date and end_date are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError as e:
        return Response({'detail': f'Invalid date format: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        aggregate_scrap_to_backlog(
            line_id,
            start_dt,
            end_dt,
            product_ids=requested_product_ids or None,
        )
        return Response({'detail': 'Scrap recalculated successfully'})
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def recalculate_scrap_for_products(viewset, request, **deps):
    _parse_product_ids = deps.get('parse_product_ids')
    """表示中品番限定の仕損再計算。画面の表示開始日は使わない。"""
    mutable_data = request.data.copy()
    line_id = mutable_data.get('line_id')
    end_date = mutable_data.get('end_date')
    try:
        requested_product_ids = _parse_product_ids(mutable_data.get('product_ids'))
    except ValueError as e:
        return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    if line_id and end_date:
        try:
            end_dt = datetime.strptime(str(end_date), '%Y-%m-%d').date()
            effective_start_dt = resolve_product_recalc_start_date(
                int(line_id),
                end_dt,
                product_ids=requested_product_ids or None,
            )
            mutable_data['start_date'] = effective_start_dt.isoformat()
        except (TypeError, ValueError):
            pass
    request._full_data = mutable_data
    return recalculate_scrap(viewset, request, **deps)
