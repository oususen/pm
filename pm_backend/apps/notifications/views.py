from datetime import datetime, timedelta

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification, NotificationRead, CallSession, CallSignal
from .serializers import NotificationSerializer, CallSessionSerializer, CallSignalSerializer


def _get_business_today():
    """日替わり8:00を考慮した「今日」を返す"""
    now = datetime.now()
    if now.hour < 8:
        return (now - timedelta(days=1)).date()
    return now.date()


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all().order_by('display_order', '-id')
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

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


def _display_name(user):
    full_name = f"{user.last_name or ''}{user.first_name or ''}".strip()
    return full_name or user.username


class CallSessionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = CallSession.objects.select_related('caller', 'callee')
    serializer_class = CallSessionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        qs = self.queryset.filter(Q(caller=self.request.user) | Q(callee=self.request.user))
        status_param = (self.request.query_params.get('status') or '').strip()
        if status_param:
            statuses = [value.strip() for value in status_param.split(',') if value.strip()]
            if statuses:
                qs = qs.filter(status__in=statuses)
        return qs.order_by('-initiated_at', '-id')

    @action(detail=False, methods=['post'], url_path='start')
    def start(self, request):
        callee_id = request.data.get('callee_id')
        call_type = request.data.get('call_type')

        if call_type not in {'voice', 'video'}:
            return Response({'detail': 'call_type は voice または video を指定してください。'}, status=400)
        if not callee_id:
            return Response({'detail': 'callee_id は必須です。'}, status=400)
        if str(callee_id) == str(request.user.id):
            return Response({'detail': '自分自身には発信できません。'}, status=400)

        from django.contrib.auth import get_user_model
        User = get_user_model()
        callee = get_object_or_404(User, id=callee_id, is_active=True)
        session = CallSession.objects.create(
            caller=request.user,
            callee=callee,
            call_type=call_type,
            status='ringing',
        )

        title = f'{_display_name(request.user)}から{"ビデオ" if call_type == "video" else "音声"}着信'
        description = (
            f'通知の通話センターから応答してください。\n'
            f'対象セッションID: {session.id}'
        )
        notification = Notification.objects.create(
            title=title,
            category='incoming_call',
            domain='call',
            description=description,
            operator_name=_display_name(request.user),
            valid_from=_get_business_today(),
            valid_to=_get_business_today() + timedelta(days=1),
        )
        notification.target_users.set([callee])

        return Response(self.get_serializer(session).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        session = self.get_object()
        if session.callee_id != request.user.id:
            return Response({'detail': '着信者のみ応答できます。'}, status=403)
        if session.status not in {'ringing', 'missed'}:
            return Response({'detail': 'この通話は応答できません。'}, status=400)

        session.status = 'accepted'
        session.accepted_at = datetime.now()
        session.save(update_fields=['status', 'accepted_at', 'updated_at'])
        return Response(self.get_serializer(session).data)

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        session = self.get_object()
        if request.user.id not in {session.caller_id, session.callee_id}:
            return Response({'detail': '参加者のみ操作できます。'}, status=403)

        session.status = 'declined'
        session.ended_at = datetime.now()
        session.save(update_fields=['status', 'ended_at', 'updated_at'])

        target_user = session.caller if request.user.id == session.callee_id else session.callee
        CallSignal.objects.create(
            session=session,
            sender=request.user,
            target_user=target_user,
            signal_type='hangup',
            payload={'reason': 'declined'},
        )
        return Response(self.get_serializer(session).data)

    @action(detail=True, methods=['post'])
    def finish(self, request, pk=None):
        session = self.get_object()
        if request.user.id not in {session.caller_id, session.callee_id}:
            return Response({'detail': '参加者のみ操作できます。'}, status=403)

        if session.status == 'ringing':
            session.status = 'canceled' if request.user.id == session.caller_id else 'missed'
        elif session.status not in {'declined', 'ended', 'canceled', 'missed'}:
            session.status = 'ended'
        session.ended_at = datetime.now()
        session.save(update_fields=['status', 'ended_at', 'updated_at'])

        target_user = session.caller if request.user.id == session.callee_id else session.callee
        CallSignal.objects.create(
            session=session,
            sender=request.user,
            target_user=target_user,
            signal_type='hangup',
            payload={'reason': session.status},
        )
        return Response(self.get_serializer(session).data)

    @action(detail=True, methods=['get', 'post'])
    def signals(self, request, pk=None):
        session = self.get_object()
        if request.user.id not in {session.caller_id, session.callee_id}:
            return Response({'detail': '参加者のみアクセスできます。'}, status=403)

        if request.method == 'GET':
            after_id = request.query_params.get('after_id')
            qs = session.signals.filter(target_user=request.user).select_related('sender', 'target_user')
            if after_id not in (None, ''):
                try:
                    qs = qs.filter(id__gt=int(after_id))
                except (TypeError, ValueError):
                    return Response({'detail': 'after_id は数値で指定してください。'}, status=400)
            serializer = CallSignalSerializer(qs.order_by('id'), many=True)
            return Response(serializer.data)

        target_user_id = request.data.get('target_user')
        signal_type = request.data.get('signal_type')
        payload = request.data.get('payload') or {}

        if signal_type not in {'offer', 'answer', 'ice_candidate', 'hangup'}:
            return Response({'detail': 'signal_type が不正です。'}, status=400)

        participant_ids = {session.caller_id, session.callee_id}
        if not target_user_id or int(target_user_id) not in participant_ids - {request.user.id}:
            return Response({'detail': 'target_user は相手ユーザーを指定してください。'}, status=400)

        from django.contrib.auth import get_user_model
        User = get_user_model()
        target_user = get_object_or_404(User, id=target_user_id)
        signal = CallSignal.objects.create(
            session=session,
            sender=request.user,
            target_user=target_user,
            signal_type=signal_type,
            payload=payload,
        )
        serializer = CallSignalSerializer(signal)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
