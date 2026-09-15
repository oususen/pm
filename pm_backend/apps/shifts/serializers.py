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
    process_name = serializers.CharField(source='process.process_name', read_only=True)
    process_code = serializers.CharField(source='process.process_code', read_only=True)

    class Meta:
        model = ShiftLineProcess
        fields = '__all__'


class ShiftLineSerializer(serializers.ModelSerializer):
    workers = ShiftWorkerSerializer(many=True, read_only=True)
    line_processes = ShiftLineProcessSerializer(many=True, read_only=True)

    class Meta:
        model = ShiftLine
        fields = '__all__'


class ShiftAssignmentSerializer(serializers.ModelSerializer):
    worker_name = serializers.CharField(source='worker.name', read_only=True)
    process_name = serializers.CharField(source='process.process_name', read_only=True)

    class Meta:
        model = ShiftAssignment
        fields = '__all__'


class ShiftAssignmentBulkSerializer(serializers.Serializer):
    """週間コピー用"""
    source_date = serializers.DateField()
    target_dates = serializers.ListField(child=serializers.DateField())
    shift_line = serializers.IntegerField()
