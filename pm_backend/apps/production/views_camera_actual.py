from datetime import datetime

from django.db import IntegrityError, transaction
from django.db.models import F
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models_camera_actual import CameraCountEvent, ProductionResultDaily
from .serializers_camera_actual import (
    CameraEventCreateSerializer,
    resolve_business_date,
)


class CameraEventCreateView(APIView):
    """カメラ検知イベントを冪等で保存し、日次実績へ反映する。"""

    def post(self, request):
        serializer = CameraEventCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        camera_event_id = validated["camera_event_id"]
        line = validated["line"]
        process = validated["process"]
        product = validated["product"]
        count = validated["count"]
        business_date = validated["business_date"]

        try:
            with transaction.atomic():
                event = CameraCountEvent.objects.create(
                    camera_event_id=camera_event_id,
                    line=line,
                    process=process,
                    product=product,
                    count=count,
                    event_at_client=validated["event_at"],
                    business_date=business_date,
                    device_id=validated.get("device_id", ""),
                    confidence=validated.get("confidence"),
                    status=CameraCountEvent.STATUS_ACCEPTED,
                )
                daily, _ = ProductionResultDaily.objects.select_for_update().get_or_create(
                    business_date=business_date,
                    line=line,
                    process=process,
                    product=product,
                    defaults={"actual_count": 0},
                )
                daily.actual_count = F("actual_count") + count
                daily.save(update_fields=["actual_count", "updated_at"])
        except IntegrityError:
            # 同一 camera_event_id の再送は成功扱いで非加算
            event = CameraCountEvent.objects.filter(camera_event_id=camera_event_id).first()
            if event and event.status != CameraCountEvent.STATUS_REPLAYED:
                event.status = CameraCountEvent.STATUS_REPLAYED
                event.save(update_fields=["status"])
            total = ProductionResultDaily.objects.filter(
                business_date=business_date,
                line=line,
                process=process,
                product=product,
            ).values_list("actual_count", flat=True).first() or 0
            return Response(
                {
                    "accepted": True,
                    "idempotent_replay": True,
                    "total_count": int(total),
                },
                status=status.HTTP_200_OK,
            )

        refreshed = ProductionResultDaily.objects.get(
            business_date=business_date,
            line=line,
            process=process,
            product=product,
        )
        return Response(
            {
                "accepted": True,
                "idempotent_replay": False,
                "total_count": int(refreshed.actual_count),
                "business_date": str(business_date),
            },
            status=status.HTTP_200_OK,
        )


class CameraResultDailyView(APIView):
    """ライン×工程×製品の日次実績を返す。"""

    def get(self, request):
        line_id = request.query_params.get("line_id")
        process_id = request.query_params.get("process_id")
        product_id = request.query_params.get("product_id")
        business_date_str = request.query_params.get("business_date")

        if not line_id or not process_id or not product_id:
            return Response(
                {"detail": "line_id, process_id, product_id は必須です。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if business_date_str:
            try:
                business_date = datetime.strptime(business_date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"detail": "business_date は YYYY-MM-DD 形式で指定してください。"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            business_date = resolve_business_date(datetime.now())

        row = ProductionResultDaily.objects.filter(
            business_date=business_date,
            line_id=line_id,
            process_id=process_id,
            product_id=product_id,
        ).first()
        return Response(
            {
                "business_date": str(business_date),
                "line_id": int(line_id),
                "process_id": int(process_id),
                "product_id": int(product_id),
                "actual_count": int(row.actual_count) if row else 0,
            },
            status=status.HTTP_200_OK,
        )
