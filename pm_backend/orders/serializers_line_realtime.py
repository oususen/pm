"""
ライン実時間記録用のSerializer
"""
from rest_framework import serializers
from .models_line_realtime import LineRealtimeRecord, LineStatus
from masters.models import Line


class LineRealtimeRecordSerializer(serializers.ModelSerializer):
    """ライン実時間記録Serializer"""

    line_code = serializers.CharField(source='line.line_code', read_only=True)
    line_name = serializers.CharField(source='line.line_name', read_only=True)
    record_type_display = serializers.CharField(source='get_record_type_display', read_only=True)
    equipment_state_display = serializers.CharField(source='get_equipment_state_display', read_only=True)

    class Meta:
        model = LineRealtimeRecord
        fields = [
            'id',
            'line',
            'line_code',
            'line_name',
            'timestamp',
            'record_type',
            'record_type_display',
            'qty',
            'equipment_state',
            'equipment_state_display',
            'event_data',
            'batch_no',
            'operator_name',
            'remarks',
        ]
        read_only_fields = ['id', 'timestamp']


class LineStatusSerializer(serializers.ModelSerializer):
    """ライン状態Serializer"""

    line_code = serializers.CharField(source='line.line_code', read_only=True)
    line_name = serializers.CharField(source='line.line_name', read_only=True)
    state_display = serializers.CharField(source='get_current_state_display', read_only=True)

    # 達成率計算
    achievement_rate = serializers.SerializerMethodField()

    class Meta:
        model = LineStatus
        fields = [
            'line',
            'line_code',
            'line_name',
            'current_state',
            'state_display',
            'today_output',
            'today_plan',
            'achievement_rate',
            'current_product_code',
            'current_product_name',
            'last_update',
        ]

    def get_achievement_rate(self, obj):
        """達成率を計算"""
        if obj.today_plan and obj.today_plan > 0:
            return round((float(obj.today_output) / float(obj.today_plan)) * 100, 1)
        return 0.0


class LineRealtimeCreateSerializer(serializers.Serializer):
    """ライン実時間記録作成用Serializer（簡易入力）"""

    line_id = serializers.IntegerField()
    record_type = serializers.ChoiceField(choices=LineRealtimeRecord.RECORD_TYPE_CHOICES)
    qty = serializers.DecimalField(max_digits=10, decimal_places=3, default=0)
    equipment_state = serializers.ChoiceField(
        choices=LineRealtimeRecord.EQUIPMENT_STATE_CHOICES,
        required=False,
        allow_null=True
    )
    batch_no = serializers.CharField(max_length=100, required=False, allow_blank=True)
    operator_name = serializers.CharField(max_length=50, required=False, allow_blank=True)
    remarks = serializers.CharField(required=False, allow_blank=True)
    event_data = serializers.JSONField(required=False, allow_null=True)

    def create(self, validated_data):
        """記録を作成"""
        line_id = validated_data.pop('line_id')
        line = Line.objects.get(id=line_id)

        record = LineRealtimeRecord.objects.create(
            line=line,
            **validated_data
        )

        # ライン状態も更新
        self._update_line_status(line, validated_data)

        return record

    def _update_line_status(self, line, data):
        """ライン状態を更新"""
        line_status, created = LineStatus.objects.get_or_create(line=line)

        # 設備状態が変更された場合
        if 'equipment_state' in data and data['equipment_state']:
            line_status.current_state = data['equipment_state']

        # 生産記録の場合、本日生産数を加算
        if data.get('record_type') == 'PRODUCTION':
            line_status.today_output += data.get('qty', 0)

        line_status.save()
