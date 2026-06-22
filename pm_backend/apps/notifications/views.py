from datetime import datetime, timedelta

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification, NotificationRead, CallSession, CallSignal, CallRecording, PushSubscription, NativePushToken
from .serializers import (
    NotificationSerializer,
    CallSessionSerializer,
    CallSignalSerializer,
    CallRecordingSerializer,
    CallRecordingUploadSerializer,
    PushSubscriptionSerializer,
    NativePushTokenSerializer,
)
from .fcm_push import get_fcm_config, send_fcm_push
from .web_push import get_web_push_config, send_web_push


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


def _normalize_naive_datetime(value):
    if value is None:
        return None
    if getattr(value, 'tzinfo', None) is not None:
        return value.astimezone().replace(tzinfo=None)
    return value


class CallSessionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = CallSession.objects.select_related('caller', 'callee', 'recording', 'recording__recorded_by')
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

        push_payload = {
            'title': title,
            'body': 'タップして通話画面を開いてください。',
            'tag': f'call-session-{session.id}',
            'url': f'/notifications/calls?session={session.id}',
            'data': {
                'session_id': session.id,
                'call_type': call_type,
                'caller_name': _display_name(request.user),
            },
        }
        for subscription in callee.push_subscriptions.all():
            send_web_push(subscription, push_payload)
        for device in callee.native_push_tokens.filter(is_active=True, platform=NativePushToken.PLATFORM_ANDROID):
            send_fcm_push(device, push_payload)

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

    @action(
        detail=True,
        methods=['get', 'post'],
        url_path='recording',
        parser_classes=[MultiPartParser, FormParser],
    )
    def recording(self, request, pk=None):
        session = self.get_object()
        if request.user.id not in {session.caller_id, session.callee_id}:
            return Response({'detail': '参加者のみアクセスできます。'}, status=403)

        if request.method == 'GET':
            recording = getattr(session, 'recording', None)
            if not recording:
                return Response({'detail': '録音はまだ登録されていません。'}, status=404)
            serializer = CallRecordingSerializer(recording, context=self.get_serializer_context())
            return Response(serializer.data)

        serializer = CallRecordingUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data['file']
        mime_type = serializer.validated_data.get('mime_type') or getattr(uploaded_file, 'content_type', '') or 'application/octet-stream'
        file_size = serializer.validated_data.get('file_size')
        if file_size in (None, ''):
            file_size = uploaded_file.size

        recording_started_at = _normalize_naive_datetime(serializer.validated_data.get('recording_started_at'))
        recording_ended_at = _normalize_naive_datetime(serializer.validated_data.get('recording_ended_at'))
        duration_seconds = serializer.validated_data.get('duration_seconds')
        if duration_seconds is None and recording_started_at and recording_ended_at:
            duration_seconds = max((recording_ended_at - recording_started_at).total_seconds(), 0)

        existing = getattr(session, 'recording', None)
        old_file_name = existing.file.name if existing and existing.file else ''

        if existing:
            existing.file = uploaded_file
            existing.mime_type = mime_type
            existing.file_size = file_size
            existing.duration_seconds = duration_seconds
            existing.recording_started_at = recording_started_at
            existing.recording_ended_at = recording_ended_at
            existing.recorded_by = request.user
            existing.save()
            recording = existing
        else:
            recording = CallRecording.objects.create(
                session=session,
                file=uploaded_file,
                mime_type=mime_type,
                file_size=file_size,
                duration_seconds=duration_seconds,
                recording_started_at=recording_started_at,
                recording_ended_at=recording_ended_at,
                recorded_by=request.user,
            )

        if old_file_name and old_file_name != recording.file.name:
            storage = recording.file.storage
            if storage.exists(old_file_name):
                storage.delete(old_file_name)

        response_serializer = CallRecordingSerializer(recording, context=self.get_serializer_context())
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class PushSubscriptionViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = PushSubscription.objects.all()
    serializer_class = PushSubscriptionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def config(self, request):
        config = get_web_push_config()
        return Response({
            'enabled': config['enabled'],
            'public_key': config['public_key'],
        })

    def create(self, request, *args, **kwargs):
        endpoint = (request.data.get('endpoint') or '').strip()
        p256dh_key = (request.data.get('p256dh_key') or '').strip()
        auth_key = (request.data.get('auth_key') or '').strip()
        user_agent = (request.data.get('user_agent') or '')[:255]

        if not endpoint or not p256dh_key or not auth_key:
            return Response({'detail': 'endpoint / p256dh_key / auth_key は必須です。'}, status=400)

        subscription, _created = PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                'user': request.user,
                'p256dh_key': p256dh_key,
                'auth_key': auth_key,
                'user_agent': user_agent,
            },
        )
        serializer = self.get_serializer(subscription)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def unsubscribe(self, request):
        endpoint = (request.data.get('endpoint') or '').strip()
        if not endpoint:
            return Response({'detail': 'endpoint は必須です。'}, status=400)
        deleted, _detail = self.get_queryset().filter(endpoint=endpoint).delete()
        return Response({'deleted': deleted})


class NativePushTokenViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = NativePushToken.objects.all()
    serializer_class = NativePushTokenSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user, is_active=True)

    @action(detail=False, methods=['get'])
    def config(self, request):
        config = get_fcm_config()
        return Response({
            'enabled': config['enabled'],
            'project_id': config['project_id'],
        })

    def create(self, request, *args, **kwargs):
        platform = (request.data.get('platform') or '').strip().lower()
        token = (request.data.get('token') or '').strip()
        device_id = (request.data.get('device_id') or '').strip()[:255]
        device_name = (request.data.get('device_name') or '').strip()[:255]
        app_version = (request.data.get('app_version') or '').strip()[:100]

        if platform not in {NativePushToken.PLATFORM_ANDROID, NativePushToken.PLATFORM_IOS}:
            return Response({'detail': 'platform は android または ios を指定してください。'}, status=400)
        if not token:
            return Response({'detail': 'token は必須です。'}, status=400)

        push_token, _created = NativePushToken.objects.update_or_create(
            token=token,
            defaults={
                'user': request.user,
                'platform': platform,
                'device_id': device_id,
                'device_name': device_name,
                'app_version': app_version,
                'is_active': True,
            },
        )
        if device_id:
            self.get_queryset().filter(platform=platform, device_id=device_id).exclude(id=push_token.id).delete()

        serializer = self.get_serializer(push_token)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def unregister(self, request):
        token = (request.data.get('token') or '').strip()
        if not token:
            return Response({'detail': 'token は必須です。'}, status=400)
        deleted, _detail = self.get_queryset().filter(token=token).delete()
        return Response({'deleted': deleted})
