from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from rest_framework import serializers, status
from masters.models import Line
from production.models_line_plan import LinePlan
from production.models_line_backlog import LineBacklog
from rest_framework.response import Response
from rest_framework.views import APIView

from production.models_production_lock import ProductionLock


class LockKeySerializer(serializers.Serializer):
    lock_type = serializers.ChoiceField(choices=['auto_plan'])
    line_id = serializers.IntegerField(min_value=1)
    plan_date = serializers.DateField()
    product_id = serializers.IntegerField(min_value=1)


class LockCreateSerializer(LockKeySerializer):
    locked_qty = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0'))


class ProductionLockView(APIView):
    """汎用ロック API（追加/解除/一覧取得）"""

    def get(self, request):
        lock_type = request.query_params.get('lock_type')
        line_id = request.query_params.get('line_id')
        start = request.query_params.get('start')
        end = request.query_params.get('end')

        if not lock_type or not line_id:
            return Response(
                {'detail': 'lock_type and line_id are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = ProductionLock.objects.filter(lock_type=lock_type, line_id=line_id)
        if start and end:
            qs = qs.filter(plan_date__range=[start, end])

        locks = list(qs.values('id', 'lock_type', 'line_id', 'plan_date', 'product_id', 'locked_qty', 'locked_at'))
        return Response(locks)

    def post(self, request):
        serializer = LockCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        requested_qty = data.pop('locked_qty')
        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        with transaction.atomic():
            line = Line.objects.filter(id=data['line_id']).first()
            if not line:
                return Response({'detail': 'ラインが見つかりません。'}, status=400)
            # 数量は保存済み計画から確定する。画面の未保存値はロックしない。
            source = (LineBacklog.objects.filter(sequence_no=1)
                      if line.line_type == 'PURCHASE' else LinePlan.objects.all())
            saved_qty = source.filter(
                line_id=line.id, plan_date=data['plan_date'], product_id=data['product_id'],
            ).aggregate(qty=Sum('plan_qty'))['qty'] or Decimal('0')
            if requested_qty != saved_qty:
                return Response({'detail': '計画を保存してからロックしてください。保存済み数量と一致しません。'}, status=409)
            obj, created = ProductionLock.objects.get_or_create(
                **data, defaults={'locked_by': user, 'locked_qty': saved_qty},
            )
            if not created and obj.locked_qty != requested_qty:
                return Response({'detail': '数量の変更には先にロック解除が必要です。'}, status=409)
        return Response(
            {'id': obj.id, 'created': created, 'locked_qty': float(obj.locked_qty)},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request):
        serializer = LockKeySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        deleted, _ = ProductionLock.objects.filter(**serializer.validated_data).delete()
        return Response({'deleted': deleted})
