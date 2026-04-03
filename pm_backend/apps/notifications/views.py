from datetime import datetime, timedelta

from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification, NotificationRead
from .serializers import NotificationSerializer


def _get_business_today():
    """日替わり8:00を考慮した「今日」を返す"""
    now = datetime.now()
    if now.hour < 8:
        return (now - timedelta(days=1)).date()
    return now.date()


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all().order_by('display_order', 'id')
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == 'list':
            today = _get_business_today()
            cutoff_hide = datetime.now() - timedelta(days=5)
            cutoff_delete = datetime.now() - timedelta(days=10)
            expired_hide = Q(valid_to__isnull=False, valid_to__lt=today) | \
                           Q(valid_to__isnull=True, created_at__lt=cutoff_hide)
            expired_delete = Q(valid_to__isnull=False, valid_to__lt=today - timedelta(days=5)) | \
                             Q(valid_to__isnull=True, created_at__lt=cutoff_delete)
            # 10日以上経過した通知をDBから削除
            Notification.objects.filter(expired_delete).delete()
            # 5日以上経過した通知を一覧から除外
            qs = qs.exclude(expired_hide)
        return qs

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
