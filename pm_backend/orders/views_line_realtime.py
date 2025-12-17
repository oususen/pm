"""
ライン実時間記録API
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Max
from django.utils import timezone
from datetime import timedelta, datetime
from .models_line_realtime import LineRealtimeRecord, LineStatus
from .serializers_line_realtime import (
    LineRealtimeRecordSerializer,
    LineStatusSerializer,
    LineRealtimeCreateSerializer,
)
from masters.models import Line


class LineRealtimeRecordViewSet(viewsets.ModelViewSet):
    """ライン実時間記録ViewSet"""

    queryset = LineRealtimeRecord.objects.all()
    serializer_class = LineRealtimeRecordSerializer

    def get_queryset(self):
        """クエリパラメータでフィルタリング"""
        queryset = LineRealtimeRecord.objects.select_related('line', 'product')

        # ラインでフィルタ
        line_id = self.request.query_params.get('line_id')
        if line_id:
            queryset = queryset.filter(line_id=line_id)

        # 期間でフィルタ
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)

        # 記録タイプでフィルタ
        record_type = self.request.query_params.get('record_type')
        if record_type:
            queryset = queryset.filter(record_type=record_type)

        # 製品でフィルタ
        product_id = self.request.query_params.get('product_id')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        product_code = self.request.query_params.get('product_code')
        if product_code:
            queryset = queryset.filter(product_code=product_code)

        return queryset.order_by('-timestamp')

    def create(self, request, *args, **kwargs):
        """簡易作成API"""
        serializer = LineRealtimeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = serializer.save()

        # 作成した記録を返す
        output_serializer = LineRealtimeRecordSerializer(record)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class LineStatusViewSet(viewsets.ReadOnlyModelViewSet):
    """ライン状態ViewSet（読み取り専用）"""

    queryset = LineStatus.objects.select_related('line').filter(line__is_active=True)
    serializer_class = LineStatusSerializer

    @action(detail=False, methods=['get'])
    def list_all(self, request):
        """全ライン状態を一括取得"""
        lines = Line.objects.filter(is_active=True)
        result = []

        for line in lines:
            # ライン状態取得（なければ作成）
            line_status, created = LineStatus.objects.get_or_create(
                line=line,
                defaults={
                    'current_state': 'STOPPED',
                    'today_output': 0,
                    'today_plan': 0,
                }
            )

            # 本日の計画数を取得（LineDemandから）
            today = timezone.now().date()
            from .models import LineDemand
            today_demand = LineDemand.objects.filter(
                line=line,
                plan_date=today
            ).aggregate(total=Sum('plan_qty'))['total'] or 0

            # 計画数を更新
            if line_status.today_plan != today_demand:
                line_status.today_plan = today_demand
                line_status.save()

            # 過去1時間の生産推移データを取得
            one_hour_ago = timezone.now() - timedelta(hours=1)
            recent_production = LineRealtimeRecord.objects.filter(
                line=line,
                record_type='PRODUCTION',
                timestamp__gte=one_hour_ago
            ).values('timestamp', 'qty').order_by('timestamp')

            # レスポンスデータ構築
            serializer = LineStatusSerializer(line_status)
            data = serializer.data
            data['recent_production'] = list(recent_production)

            # サイクルタイム計算（仮）
            data['cycle_time'] = 0

            # 進捗率
            if line_status.today_plan > 0:
                data['progress'] = round((float(line_status.today_output) / float(line_status.today_plan)) * 100, 1)
            else:
                data['progress'] = 0

            result.append(data)

        return Response(result)

    @action(detail=True, methods=['post'])
    def reset_daily(self, request, pk=None):
        """日次リセット（デバッグ用）"""
        line_status = self.get_object()
        line_status.today_output = 0
        line_status.today_plan = 0
        line_status.save()

        return Response({'message': '日次リセット完了'})

    @action(detail=False, methods=['post'])
    def reset_all_daily(self, request):
        """全ライン日次リセット"""
        LineStatus.objects.update(today_output=0, today_plan=0)
        return Response({'message': '全ライン日次リセット完了'})
