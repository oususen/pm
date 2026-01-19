from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification, NotificationRead
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all().order_by('display_order', 'id')
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """通知を既読にする"""
        notification = self.get_object()
        NotificationRead.objects.get_or_create(
            notification=notification,
            user=request.user
        )
        return Response({'status': 'ok'})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """複数の通知を既読にする"""
        notification_ids = request.data.get('notification_ids', [])
        for nid in notification_ids:
            try:
                notification = Notification.objects.get(id=nid)
                NotificationRead.objects.get_or_create(
                    notification=notification,
                    user=request.user
                )
            except Notification.DoesNotExist:
                pass
        return Response({'status': 'ok'})
