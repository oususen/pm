from datetime import datetime

from django.db import IntegrityError, transaction
from django.db.models import F
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models_camera_actual import CameraCountEvent, ProductionResultDaily
from .serializers_camera_actual import (
    CameraAutoDetectSerializer,
    CameraEventCreateSerializer,
    resolve_business_date,
)
from .services_camera_auto_detect import auto_detect_runtime


def apply_camera_event(
    *,
    camera_event_id,
    line,
    process,
    product,
    count,
    event_at,
    device_id="",
    confidence=None,
    shape_code="",
    shape_confidence=None,
):
    """カメライベントを冪等で反映し、集計結果を返す。"""
    business_date = resolve_business_date(event_at)
    try:
        with transaction.atomic():
            CameraCountEvent.objects.create(
                camera_event_id=camera_event_id,
                line=line,
                process=process,
                product=product,
                count=count,
                event_at_client=event_at,
                business_date=business_date,
                device_id=device_id or "",
                confidence=confidence,
                shape_code=shape_code or "",
                shape_confidence=shape_confidence,
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
            replayed = False
    except IntegrityError:
        event = CameraCountEvent.objects.filter(camera_event_id=camera_event_id).first()
        if event and event.status != CameraCountEvent.STATUS_REPLAYED:
            event.status = CameraCountEvent.STATUS_REPLAYED
            event.save(update_fields=["status"])
        replayed = True

    total = ProductionResultDaily.objects.filter(
        business_date=business_date,
        line=line,
        process=process,
        product=product,
    ).values_list("actual_count", flat=True).first() or 0
    return {
        "accepted": True,
        "idempotent_replay": replayed,
        "total_count": int(total),
        "business_date": str(business_date),
    }


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
        data = apply_camera_event(
            camera_event_id=camera_event_id,
            line=line,
            process=process,
            product=product,
            count=validated["count"],
            event_at=validated["event_at"],
            device_id=validated.get("device_id", ""),
            confidence=validated.get("confidence"),
            shape_code=validated["product"].product_code,
            shape_confidence=validated.get("confidence"),
        )
        return Response(data, status=status.HTTP_200_OK)


class CameraAutoDetectView(APIView):
    """フレームから自動検知し、通過時のみ実績を加算する。"""

    def post(self, request):
        serializer = CameraAutoDetectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        now_dt = datetime.now()
        captured_at = validated.get("frame_captured_at") or now_dt

        try:
            detect_result = auto_detect_runtime.process(
                session_id=validated["session_id"],
                frame_data_url=validated["frame_data_url"],
                now_dt=now_dt,
                config={
                    "line_position_ratio": validated.get("line_position_ratio", 0.5),
                    "side_margin_ratio": validated.get("side_margin_ratio", 0.03),
                    "person_bottom_ratio": validated.get("person_bottom_ratio", 0.78),
                    "min_y_ratio": validated.get("min_y_ratio", 0.45),
                    "yolo_confidence": validated.get("yolo_confidence", 0.5),
                    "dedup_seconds": validated.get("dedup_seconds", 1.2),
                    "motion_threshold_ratio": validated.get("motion_threshold_ratio", 0.01),
                },
            )
        except RuntimeError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as exc:
            return Response({"detail": f"自動検知に失敗しました: {exc}"}, status=status.HTTP_400_BAD_REQUEST)

        total_count = None
        business_date = resolve_business_date(captured_at)
        detected_shape_code = validated["product"].product_code
        detected_shape_confidence = 0.9 if detect_result.detected_count > 0 else None
        shape_match = bool(detect_result.detected_count > 0)

        for idx in range(detect_result.pass_count if shape_match else 0):
            camera_event_id = f"auto-{validated['session_id']}-{int(now_dt.timestamp() * 1000)}-{idx}"
            event_data = apply_camera_event(
                camera_event_id=camera_event_id,
                line=validated["line"],
                process=validated["process"],
                product=validated["product"],
                count=1,
                event_at=captured_at,
                device_id=validated.get("device_id", ""),
                confidence=0.9,
                shape_code=detected_shape_code,
                shape_confidence=detected_shape_confidence,
            )
            total_count = event_data["total_count"]
            business_date = event_data["business_date"]

        if total_count is None:
            total_count = ProductionResultDaily.objects.filter(
                business_date=business_date,
                line=validated["line"],
                process=validated["process"],
                product=validated["product"],
            ).values_list("actual_count", flat=True).first() or 0

        return Response(
            {
                "detected_count": detect_result.detected_count,
                "pass_count": detect_result.pass_count,
                "shape_code": detected_shape_code,
                "shape_confidence": detected_shape_confidence,
                "shape_match": shape_match,
                "total_count": int(total_count),
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
        try:
            line_id_int = int(line_id)
            process_id_int = int(process_id)
            product_id_int = int(product_id)
        except (TypeError, ValueError):
            return Response(
                {"detail": "line_id, process_id, product_id は整数で指定してください。"},
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
            line_id=line_id_int,
            process_id=process_id_int,
            product_id=product_id_int,
        ).first()
        return Response(
            {
                "business_date": str(business_date),
                "line_id": line_id_int,
                "process_id": process_id_int,
                "product_id": product_id_int,
                "actual_count": int(row.actual_count) if row else 0,
            },
            status=status.HTTP_200_OK,
        )
