from datetime import datetime

from django.db import transaction
from django.db.models import Prefetch, Q
from rest_framework import parsers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models_morning_meeting import MorningMeeting, MorningMeetingAttachment, MorningMeetingParticipant
from .serializers_morning_meeting import (
    MorningMeetingDuplicateSerializer,
    MorningMeetingExecutionSerializer,
    MorningMeetingSerializer,
    _user_display_name,
)


def _build_completion_summary(meeting):
    participants = list(meeting.participants.select_related('user').all())
    total = len(participants)
    present = [p for p in participants if p.attendance_status == MorningMeetingParticipant.STATUS_PRESENT]
    absent = [p for p in participants if p.attendance_status == MorningMeetingParticipant.STATUS_ABSENT]
    late = [p for p in participants if p.attendance_status == MorningMeetingParticipant.STATUS_LATE]

    lines = ['--- 実行サマリー ---']

    if meeting.started_at and meeting.ended_at:
        delta = meeting.ended_at - meeting.started_at
        minutes = int(delta.total_seconds() // 60)
        lines.append(f'所要時間: {minutes}分')

    rate = round(len(present) / total * 100) if total else 0
    lines.append(f'出席: {len(present)}/{total}名 ({rate}%)')

    if absent:
        names = ', '.join(_user_display_name(p.user) for p in absent)
        lines.append(f'欠席: {names}')
    if late:
        names = ', '.join(_user_display_name(p.user) for p in late)
        lines.append(f'遅刻: {names}')

    return '\n'.join(lines)


class MorningMeetingViewSet(viewsets.ModelViewSet):
    serializer_class = MorningMeetingSerializer
    pagination_class = None
    parser_classes = [parsers.JSONParser, parsers.MultiPartParser, parsers.FormParser]

    def get_queryset(self):
        participant_qs = MorningMeetingParticipant.objects.select_related(
            'user',
            'user__profile',
            'user__profile__department',
            'user__profile__division',
            'user__profile__group',
            'user__profile__team',
            'user__profile__unit',
        )
        attachment_qs = MorningMeetingAttachment.objects.order_by('display_order', 'id')
        queryset = MorningMeeting.objects.select_related(
            'facilitator',
            'created_by',
            'updated_by',
        ).prefetch_related(
            'target_departments',
            'target_lines',
            Prefetch('participants', queryset=participant_qs),
            Prefetch('attachments', queryset=attachment_qs),
        )

        params = self.request.query_params
        status_value = params.get('status')
        if status_value:
            queryset = queryset.filter(status=status_value)

        meeting_date_from = params.get('meeting_date_from')
        if meeting_date_from:
            queryset = queryset.filter(meeting_date__gte=meeting_date_from)

        meeting_date_to = params.get('meeting_date_to')
        if meeting_date_to:
            queryset = queryset.filter(meeting_date__lte=meeting_date_to)

        department_id = params.get('department')
        if department_id:
            queryset = queryset.filter(target_departments__id=department_id).distinct()

        line_id = params.get('line')
        if line_id:
            queryset = queryset.filter(target_lines__id=line_id).distinct()

        participant_user = params.get('participant_user')
        if participant_user:
            queryset = queryset.filter(participants__user_id=participant_user).distinct()

        if getattr(self, 'action', None) == 'list':
            template_mode = (params.get('template_mode') or '').strip().lower()
            if template_mode == 'template':
                queryset = queryset.filter(is_template=True)
            elif template_mode == 'all':
                pass
            else:
                queryset = queryset.filter(is_template=False)

        search = (params.get('search') or '').strip()
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(agenda__icontains=search) |
                Q(notices__icontains=search) |
                Q(cautions__icontains=search)
            )

        return queryset.order_by('-meeting_date', '-id')

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(created_by=user, updated_by=user)

    def perform_update(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(updated_by=user)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        meeting = self.get_object()
        if meeting.is_template:
            return Response({'detail': 'テンプレートは開始できません。'}, status=status.HTTP_400_BAD_REQUEST)
        if meeting.status == MorningMeeting.STATUS_COMPLETED:
            return Response({'detail': '完了済みの朝礼は開始できません。'}, status=status.HTTP_400_BAD_REQUEST)

        meeting.status = MorningMeeting.STATUS_IN_PROGRESS
        if not meeting.started_at:
            meeting.started_at = datetime.now()
        meeting.updated_by = request.user if request.user.is_authenticated else None
        meeting.save(update_fields=['status', 'started_at', 'updated_by', 'updated_at'])
        return Response(self.get_serializer(meeting).data)

    @action(detail=True, methods=['post'])
    def save_execution(self, request, pk=None):
        meeting = self.get_object()
        if meeting.is_template:
            return Response({'detail': 'テンプレートは実行保存できません。'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = MorningMeetingExecutionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        with transaction.atomic():
            if 'execution_note' in payload:
                meeting.execution_note = payload.get('execution_note', '')
                meeting.updated_by = request.user if request.user.is_authenticated else None
                meeting.save(update_fields=['execution_note', 'updated_by', 'updated_at'])

            for row in payload.get('participants', []):
                participant = None
                if row.get('id'):
                    participant = meeting.participants.filter(id=row['id']).first()
                elif row.get('user'):
                    participant = meeting.participants.filter(user_id=row['user']).first()
                if not participant:
                    continue
                participant.attendance_status = row['attendance_status']
                participant.remark = row.get('remark', '')
                participant.checked_at = datetime.now()
                participant.save(update_fields=['attendance_status', 'remark', 'checked_at', 'updated_at'])

        meeting.refresh_from_db()
        return Response(self.get_serializer(meeting).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        meeting = self.get_object()
        if meeting.is_template:
            return Response({'detail': 'テンプレートは完了できません。'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = MorningMeetingExecutionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        with transaction.atomic():
            if payload.get('participants'):
                for row in payload['participants']:
                    participant = None
                    if row.get('id'):
                        participant = meeting.participants.filter(id=row['id']).first()
                    elif row.get('user'):
                        participant = meeting.participants.filter(user_id=row['user']).first()
                    if not participant:
                        continue
                    participant.attendance_status = row['attendance_status']
                    participant.remark = row.get('remark', '')
                    participant.checked_at = datetime.now()
                    participant.save(update_fields=['attendance_status', 'remark', 'checked_at', 'updated_at'])

            if 'execution_note' in payload:
                meeting.execution_note = payload.get('execution_note', '')
            if not meeting.started_at:
                meeting.started_at = datetime.now()
            meeting.ended_at = datetime.now()

            summary = _build_completion_summary(meeting)
            note = (meeting.execution_note or '').rstrip()
            meeting.execution_note = f'{note}\n\n{summary}' if note else summary

            meeting.status = MorningMeeting.STATUS_COMPLETED
            meeting.updated_by = request.user if request.user.is_authenticated else None
            meeting.save(update_fields=['execution_note', 'started_at', 'ended_at', 'status', 'updated_by', 'updated_at'])

        meeting.refresh_from_db()
        return Response(self.get_serializer(meeting).data)

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        source_meeting = self.get_object()
        serializer = MorningMeetingDuplicateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user if request.user.is_authenticated else None
        duplicated = serializer.duplicate(source_meeting, user=user)
        duplicated.refresh_from_db()
        return Response(self.get_serializer(duplicated).data, status=status.HTTP_201_CREATED)
