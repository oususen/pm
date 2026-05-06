from datetime import datetime, timedelta

from masters.models import Line, Process, Product
from rest_framework import serializers


def resolve_business_date(target_dt):
    """8:00締めで業務日を返す。"""
    if target_dt.time() < datetime.strptime("08:00:00", "%H:%M:%S").time():
        return (target_dt - timedelta(days=1)).date()
    return target_dt.date()


class CameraEventCreateSerializer(serializers.Serializer):
    camera_event_id = serializers.CharField(max_length=64)
    line_id = serializers.IntegerField(min_value=1)
    process_id = serializers.IntegerField(min_value=1)
    product_id = serializers.IntegerField(min_value=1)
    event_at = serializers.DateTimeField()
    count = serializers.IntegerField(min_value=1, default=1)
    device_id = serializers.CharField(max_length=128, allow_blank=True, required=False, default="")
    confidence = serializers.DecimalField(
        max_digits=6,
        decimal_places=4,
        required=False,
        allow_null=True,
    )

    def validate(self, attrs):
        line_id = attrs["line_id"]
        process_id = attrs["process_id"]
        product_id = attrs["product_id"]

        line = Line.objects.filter(id=line_id, is_active=True).first()
        if not line:
            raise serializers.ValidationError("指定ラインが見つかりません。")

        process = Process.objects.filter(id=process_id, is_active=True).first()
        if not process:
            raise serializers.ValidationError("指定工程が見つかりません。")

        product = Product.objects.filter(id=product_id, is_active=True).first()
        if not product:
            raise serializers.ValidationError("指定製品が見つかりません。")

        if process.line_id and process.line_id != line.id:
            raise serializers.ValidationError("工程とラインの組み合わせが不正です。")
        if product.line_id and product.line_id != line.id:
            raise serializers.ValidationError("製品とラインの組み合わせが不正です。")
        if product.process_id and product.process_id != process.id:
            raise serializers.ValidationError("製品と工程の組み合わせが不正です。")

        attrs["line"] = line
        attrs["process"] = process
        attrs["product"] = product
        attrs["business_date"] = resolve_business_date(attrs["event_at"])
        return attrs


class ProductionResultDailyResponseSerializer(serializers.Serializer):
    business_date = serializers.DateField()
    line_id = serializers.IntegerField()
    process_id = serializers.IntegerField()
    product_id = serializers.IntegerField()
    actual_count = serializers.IntegerField()


class CameraAutoDetectSerializer(serializers.Serializer):
    session_id = serializers.CharField(max_length=128)
    line_id = serializers.IntegerField(min_value=1)
    process_id = serializers.IntegerField(min_value=1)
    product_id = serializers.IntegerField(min_value=1)
    frame_data_url = serializers.CharField()
    frame_captured_at = serializers.DateTimeField(required=False, allow_null=True)
    device_id = serializers.CharField(max_length=128, allow_blank=True, required=False, default="")
    line_position_ratio = serializers.FloatField(required=False, min_value=0.1, max_value=0.9, default=0.5)
    side_margin_ratio = serializers.FloatField(required=False, min_value=0.01, max_value=0.3, default=0.03)
    person_bottom_ratio = serializers.FloatField(required=False, min_value=0.5, max_value=0.95, default=0.78)
    min_y_ratio = serializers.FloatField(required=False, min_value=0.1, max_value=0.95, default=0.45)
    yolo_confidence = serializers.FloatField(required=False, min_value=0.1, max_value=0.95, default=0.5)
    dedup_seconds = serializers.FloatField(required=False, min_value=0.2, max_value=5.0, default=1.2)
    motion_threshold_ratio = serializers.FloatField(required=False, min_value=0.002, max_value=0.08, default=0.01)
    frame_interval_ms = serializers.IntegerField(required=False, min_value=200, max_value=5000, default=1200)

    def validate(self, attrs):
        line = Line.objects.filter(id=attrs["line_id"], is_active=True).first()
        if not line:
            raise serializers.ValidationError("指定ラインが見つかりません。")
        process = Process.objects.filter(id=attrs["process_id"], is_active=True).first()
        if not process:
            raise serializers.ValidationError("指定工程が見つかりません。")
        product = Product.objects.filter(id=attrs["product_id"], is_active=True).first()
        if not product:
            raise serializers.ValidationError("指定製品が見つかりません。")
        if process.line_id and process.line_id != line.id:
            raise serializers.ValidationError("工程とラインの組み合わせが不正です。")
        if product.line_id and product.line_id != line.id:
            raise serializers.ValidationError("製品とラインの組み合わせが不正です。")
        if product.process_id and product.process_id != process.id:
            raise serializers.ValidationError("製品と工程の組み合わせが不正です。")
        attrs["line"] = line
        attrs["process"] = process
        attrs["product"] = product
        return attrs
