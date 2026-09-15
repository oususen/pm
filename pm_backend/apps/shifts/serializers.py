from rest_framework import serializers
from .models import ShiftLine, ShiftWorker, ShiftLineProcess, ShiftAssignment


class ShiftWorkerSerializer(serializers.ModelSerializer):
    user_display_name = serializers.SerializerMethodField()

    class Meta:
        model = ShiftWorker
        fields = '__all__'

    def get_user_display_name(self, obj):
        if obj.user:
            return f'{obj.user.last_name} {obj.user.first_name}'.strip() or obj.user.username
        return None


class ShiftLineProcessSerializer(serializers.ModelSerializer):
    process_name = serializers.SerializerMethodField()
    process_code = serializers.SerializerMethodField()
    is_activity = serializers.SerializerMethodField()

    class Meta:
        model = ShiftLineProcess
        fields = '__all__'

    def get_process_name(self, obj):
        """生産工程ならマスタ名、活動ならcustom_name"""
        if obj.process:
            return obj.process.process_name
        return obj.custom_name or ''

    def get_process_code(self, obj):
        if obj.process:
            return obj.process.process_code
        return ''

    def get_is_activity(self, obj):
        """活動（非生産工程）かどうか"""
        return obj.process is None


class ShiftLineSerializer(serializers.ModelSerializer):
    workers = ShiftWorkerSerializer(many=True, read_only=True)
    line_processes = ShiftLineProcessSerializer(many=True, read_only=True)

    class Meta:
        model = ShiftLine
        fields = '__all__'


class ShiftAssignmentSerializer(serializers.ModelSerializer):
    worker_name = serializers.CharField(source='worker.name', read_only=True)
    process_name = serializers.SerializerMethodField()

    class Meta:
        model = ShiftAssignment
        fields = '__all__'

    def get_process_name(self, obj):
        if obj.process:
            return obj.process.process_name
        if obj.line_process:
            return obj.line_process.display_name
        return ''


class ShiftAssignmentBulkSerializer(serializers.Serializer):
    """週間コピー用"""
    source_date = serializers.DateField()
    target_dates = serializers.ListField(child=serializers.DateField())
    shift_line = serializers.IntegerField()
