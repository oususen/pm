"""定時タスク参照系サービス"""
from rest_framework import status
from rest_framework.response import Response

from production.models_schedule_config import ScheduleRunLog
from production.serializers import ScheduleRunLogSerializer


def get_run_logs(request, logger=None):
    config_id = request.query_params.get('config_id')
    if not config_id:
        return Response({'detail': 'config_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    logs = ScheduleRunLog.objects.filter(config_id=config_id).order_by('-started_at')[:30]
    serializer = ScheduleRunLogSerializer(logs, many=True)
    return Response(serializer.data)
