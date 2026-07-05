import json
import os

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import Q
from rest_framework import serializers

from accounts.models import Department, UnitLineMapping

from .models_morning_meeting import MorningMeeting, MorningMeetingAttachment, MorningMeetingParticipant


ALLOWED_ATTACHMENT_EXTENSIONS = {
    '.pdf': MorningMeetingAttachment.TYPE_PDF,
    '.png': MorningMeetingAttachment.TYPE_IMAGE,
    '.jpg': MorningMeetingAttachment.TYPE_IMAGE,
    '.jpeg': MorningMeetingAttachment.TYPE_IMAGE,
    '.gif': MorningMeetingAttachment.TYPE_IMAGE,
    '.bmp': MorningMeetingAttachment.TYPE_IMAGE,
    '.webp': MorningMeetingAttachment.TYPE_IMAGE,
    '.xlsx': MorningMeetingAttachment.TYPE_EXCEL,
    '.xls': MorningMeetingAttachment.TYPE_EXCEL,
    '.xlsm': MorningMeetingAttachment.TYPE_EXCEL,
}


def _user_display_name(user):
    full_name = f'{user.last_name or ""} {user.first_name or ""}'.strip()
    return full_name or user.username


def _build_media_url(raw_url):
    if not raw_url:
        return ''
    path = str(raw_url)
    if path.startswith(('http://', 'https://', '/')):
        return path
    return f'/media/{path.lstrip("/")}'


def _department_user_queryset(department):
    qs = User.objects.filter(is_active=True).select_related(
        'profile',
        'profile__department',
        'profile__division',
        'profile__group',
        'profile__team',
        'profile__unit',
    )
    if not department:
        return qs.none()

    if department.level == 'division':
        return qs.filter(profile__division_id=department.id)
    if department.level == 'group':
        return qs.filter(profile__group_id=department.id)
    if department.level == 'team':
        return qs.filter(Q(profile__team_id=department.id) | Q(profile__supervisor_teams=department)).distinct()
    if department.level == 'unit':
        return qs.filter(Q(profile__unit_id=department.id) | Q(profile__leader_units=department)).distinct()
    return qs.filter(profile__department_id=department.id)


def _department_user_queryset_for_departments(departments):
    queryset = User.objects.none()
    for department in departments:
        queryset = queryset | _department_user_queryset(department)
    return queryset.distinct()


def _department_children_map():
    children_map = {}
    for department in Department.objects.all().only('id', 'parent_id', 'level'):
        children_map.setdefault(department.parent_id or 0, []).append(department)
    return children_map


def _collect_descendant_unit_ids(department_ids):
    if not department_ids:
        return []

    department_map = {
        department.id: department
        for department in Department.objects.filter(id__in=department_ids).only('id', 'parent_id', 'level')
    }
    children_map = _department_children_map()
    unit_ids = set()
    queue = list(department_map.values())
    while queue:
        current = queue.pop(0)
        if current.level == 'unit':
            unit_ids.add(current.id)
            continue
        queue.extend(children_map.get(current.id, []))
    return list(unit_ids)


class MorningMeetingAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    file_type_label = serializers.CharField(source='get_attachment_type_display', read_only=True)

    class Meta:
        model = MorningMeetingAttachment
        fields = [
            'id',
            'original_name',
            'content_type',
            'file_size',
            'attachment_type',
            'file_type_label',
            'display_order',
            'file_url',
            'created_at',
        ]
        read_only_fields = fields

    def get_file_url(self, obj):
        if not obj.file:
            return ''
        request = self.context.get('request')
        url = _build_media_url(obj.file.url)
        return request.build_absolute_uri(url) if request else url


class MorningMeetingParticipantSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    employee_code = serializers.CharField(source='user.profile.employee_code', read_only=True)
    role = serializers.CharField(source='user.profile.role', read_only=True)
    department_name = serializers.CharField(source='user.profile.department.name', read_only=True)
    division_name = serializers.CharField(source='user.profile.division.name', read_only=True)
    group_name = serializers.CharField(source='user.profile.group.name', read_only=True)
    team_name = serializers.CharField(source='user.profile.team.name', read_only=True)
    unit_name = serializers.CharField(source='user.profile.unit.name', read_only=True)

    class Meta:
        model = MorningMeetingParticipant
        fields = [
            'id',
            'user',
            'user_name',
            'employee_code',
            'role',
            'department_name',
            'division_name',
            'group_name',
            'team_name',
            'unit_name',
            'attendance_status',
            'checked_at',
            'remark',
            'display_order',
        ]
        read_only_fields = ['id', 'checked_at']

    def get_user_name(self, obj):
        return _user_display_name(obj.user)


class MorningMeetingSerializer(serializers.ModelSerializer):
    target_departments = serializers.SerializerMethodField()
    target_department_names = serializers.SerializerMethodField()
    target_lines = serializers.SerializerMethodField()
    target_line_names = serializers.SerializerMethodField()
    facilitator_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    participants = MorningMeetingParticipantSerializer(many=True, read_only=True)
    attachments = MorningMeetingAttachmentSerializer(many=True, read_only=True)
    department_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        write_only=True,
        required=False,
    )
    line_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        write_only=True,
        required=False,
    )
    participant_user_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        write_only=True,
        required=False,
    )
    deleted_attachment_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        write_only=True,
        required=False,
    )
    participant_count = serializers.SerializerMethodField()
    checked_count = serializers.SerializerMethodField()
    present_count = serializers.SerializerMethodField()
    absent_count = serializers.SerializerMethodField()
    attachment_count = serializers.SerializerMethodField()
    meeting_date = serializers.DateField(required=False, allow_null=True)

    class Meta:
        model = MorningMeeting
        fields = [
            'id',
            'meeting_date',
            'title',
            'is_template',
            'target_departments',
            'target_department_names',
            'target_lines',
            'target_line_names',
            'department_ids',
            'line_ids',
            'facilitator',
            'facilitator_name',
            'agenda',
            'notices',
            'cautions',
            'execution_note',
            'status',
            'status_display',
            'started_at',
            'ended_at',
            'participants',
            'participant_user_ids',
            'attachments',
            'deleted_attachment_ids',
            'participant_count',
            'checked_count',
            'present_count',
            'absent_count',
            'attachment_count',
            'created_by',
            'created_by_name',
            'updated_by',
            'updated_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'started_at',
            'ended_at',
            'created_by',
            'updated_by',
            'created_at',
            'updated_at',
        ]

    def to_internal_value(self, data):
        if hasattr(data, 'keys') and hasattr(data, 'getlist'):
            mutable_data = {}
            for key in data.keys():
                values = data.getlist(key)
                mutable_data[key] = values if len(values) > 1 else data.get(key)
        else:
            mutable_data = data.copy() if hasattr(data, 'copy') else dict(data)
        for field_name in ('department_ids', 'line_ids', 'participant_user_ids', 'deleted_attachment_ids'):
            if field_name in mutable_data:
                mutable_data[field_name] = self._normalize_int_list(mutable_data.get(field_name))
        if 'facilitator' in mutable_data and str(mutable_data.get('facilitator') or '').strip() == '':
            mutable_data['facilitator'] = None
        return super().to_internal_value(mutable_data)

    def get_target_departments(self, obj):
        return [
            {
                'id': department.id,
                'name': department.name,
                'level': department.level,
            }
            for department in obj.target_departments.all().order_by('display_id', 'name', 'id')
        ]

    def get_target_department_names(self, obj):
        return [department.name for department in obj.target_departments.all().order_by('display_id', 'name', 'id')]

    def get_target_lines(self, obj):
        return [
            {
                'id': line.id,
                'line_code': line.line_code,
                'line_name': line.line_name,
            }
            for line in obj.target_lines.all().order_by('line_code', 'line_name', 'id')
        ]

    def get_target_line_names(self, obj):
        return [
            f'{line.line_code} {line.line_name}'.strip()
            for line in obj.target_lines.all().order_by('line_code', 'line_name', 'id')
        ]

    def get_facilitator_name(self, obj):
        if not obj.facilitator_id:
            return ''
        return _user_display_name(obj.facilitator)

    def get_created_by_name(self, obj):
        if not obj.created_by_id:
            return ''
        return _user_display_name(obj.created_by)

    def get_updated_by_name(self, obj):
        if not obj.updated_by_id:
            return ''
        return _user_display_name(obj.updated_by)

    def get_participant_count(self, obj):
        return obj.participants.count()

    def get_checked_count(self, obj):
        return obj.participants.exclude(attendance_status=MorningMeetingParticipant.STATUS_PENDING).count()

    def get_present_count(self, obj):
        return obj.participants.filter(attendance_status=MorningMeetingParticipant.STATUS_PRESENT).count()

    def get_absent_count(self, obj):
        return obj.participants.filter(
            attendance_status__in=[
                MorningMeetingParticipant.STATUS_ABSENT,
                MorningMeetingParticipant.STATUS_LATE,
            ]
        ).count()

    def get_attachment_count(self, obj):
        return obj.attachments.count()

    def validate_department_ids(self, value):
        return self._validate_id_list(value, Department.objects.all(), '部署')

    def validate_line_ids(self, value):
        from masters.models import Line

        return self._validate_id_list(
            value,
            Line.objects.filter(is_active=True, line_type='PROD'),
            'ライン',
        )

    def validate_participant_user_ids(self, value):
        return self._validate_id_list(value, User.objects.filter(is_active=True), '参加者')

    def validate_deleted_attachment_ids(self, value):
        if not self.instance:
            return []
        valid_ids = set(self.instance.attachments.filter(id__in=value).values_list('id', flat=True))
        invalid_ids = [attachment_id for attachment_id in value if attachment_id not in valid_ids]
        if invalid_ids:
            raise serializers.ValidationError(f'削除対象に存在しない添付資料が含まれています: {invalid_ids}')
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        is_template = attrs.get('is_template', getattr(self.instance, 'is_template', False))
        meeting_date = attrs.get('meeting_date', getattr(self.instance, 'meeting_date', None))
        if not is_template and not meeting_date:
            raise serializers.ValidationError({'meeting_date': '通常朝礼では朝礼日を入力してください。'})
        status_value = attrs.get('status', getattr(self.instance, 'status', MorningMeeting.STATUS_DRAFT))
        if status_value == MorningMeeting.STATUS_COMPLETED and getattr(self.instance, 'status', None) != MorningMeeting.STATUS_COMPLETED:
            raise serializers.ValidationError({'status': '完了は実行画面から更新してください。'})

        department_ids = attrs.get('department_ids')
        line_ids = attrs.get('line_ids')
        if department_ids is None and self.instance is not None:
            department_ids = list(self.instance.target_departments.values_list('id', flat=True))
        if line_ids is None and self.instance is not None:
            line_ids = list(self.instance.target_lines.values_list('id', flat=True))

        if line_ids and not department_ids:
            raise serializers.ValidationError({'line_ids': '対象ラインを設定する場合は対象部署を選択してください。'})

        if department_ids and line_ids:
            allowed_line_ids = set(
                UnitLineMapping.objects.filter(
                    unit_id__in=_collect_descendant_unit_ids(department_ids)
                ).values_list('line_id', flat=True)
            )
            invalid_line_ids = [line_id for line_id in line_ids if line_id not in allowed_line_ids]
            if invalid_line_ids:
                raise serializers.ValidationError({'line_ids': f'対象部署に紐づかないラインが含まれています: {invalid_line_ids}'})

        new_attachments = self.context.get('request').FILES.getlist('new_attachments') if self.context.get('request') else []
        self._validate_new_attachments(new_attachments)
        return attrs

    def create(self, validated_data):
        department_ids = validated_data.pop('department_ids', [])
        line_ids = validated_data.pop('line_ids', [])
        participant_user_ids = validated_data.pop('participant_user_ids', None)
        validated_data.pop('deleted_attachment_ids', None)

        meeting = MorningMeeting.objects.create(**validated_data)
        self._save_relations(meeting, department_ids, line_ids)
        self._replace_participants(meeting, participant_user_ids, department_ids=department_ids)
        self._save_attachments(meeting)
        return meeting

    def update(self, instance, validated_data):
        department_ids = validated_data.pop('department_ids', None)
        line_ids = validated_data.pop('line_ids', None)
        participant_user_ids = validated_data.pop('participant_user_ids', None)
        deleted_attachment_ids = validated_data.pop('deleted_attachment_ids', [])

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        effective_department_ids = department_ids
        if department_ids is not None or line_ids is not None:
            effective_department_ids = self._save_relations(instance, department_ids, line_ids)

        if participant_user_ids is not None or department_ids is not None:
            if effective_department_ids is None:
                effective_department_ids = list(instance.target_departments.values_list('id', flat=True))
            self._replace_participants(
                instance,
                participant_user_ids,
                department_ids=effective_department_ids,
                preserve_existing=True,
            )

        if deleted_attachment_ids:
            instance.attachments.filter(id__in=deleted_attachment_ids).delete()
        self._save_attachments(instance)
        return instance

    def _save_relations(self, meeting, department_ids=None, line_ids=None):
        effective_department_ids = None
        if department_ids is not None:
            meeting.target_departments.set(department_ids)
            effective_department_ids = department_ids
        if line_ids is not None:
            meeting.target_lines.set(line_ids)
        return effective_department_ids

    def _replace_participants(self, meeting, participant_user_ids, department_ids=None, preserve_existing=False):
        if participant_user_ids is None:
            if preserve_existing and meeting.participants.exists():
                return
            if department_ids:
                departments = list(Department.objects.filter(id__in=department_ids))
                participant_user_ids = list(
                    _department_user_queryset_for_departments(departments)
                    .order_by('last_name', 'first_name', 'username')
                    .values_list('id', flat=True)
                    .distinct()
                )
            else:
                participant_user_ids = []

        if preserve_existing:
            existing_by_user = {
                row.user_id: row
                for row in meeting.participants.all()
            }
        else:
            existing_by_user = {}

        meeting.participants.exclude(user_id__in=participant_user_ids).delete()
        for index, user_id in enumerate(participant_user_ids):
            defaults = {'display_order': index}
            row = existing_by_user.get(user_id)
            if row:
                row.display_order = index
                row.save(update_fields=['display_order', 'updated_at'])
                continue
            MorningMeetingParticipant.objects.update_or_create(
                meeting=meeting,
                user_id=user_id,
                defaults=defaults,
            )

    def _save_attachments(self, meeting):
        request = self.context.get('request')
        files = request.FILES.getlist('new_attachments') if request is not None else []
        if not files:
            return

        start_order = meeting.attachments.count()
        for index, file_obj in enumerate(files, start=1):
            _, ext = os.path.splitext(file_obj.name or '')
            MorningMeetingAttachment.objects.create(
                meeting=meeting,
                file=file_obj,
                original_name=file_obj.name or '',
                content_type=getattr(file_obj, 'content_type', '') or '',
                file_size=getattr(file_obj, 'size', 0) or 0,
                attachment_type=ALLOWED_ATTACHMENT_EXTENSIONS[ext.lower()],
                display_order=start_order + index,
            )

    def _normalize_int_list(self, value):
        if value in (None, '', []):
            return []
        if isinstance(value, (list, tuple)):
            return [int(item) for item in value if str(item).strip() != '']
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return []
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = [item.strip() for item in text.split(',') if item.strip()]
            if isinstance(parsed, list):
                return [int(item) for item in parsed if str(item).strip() != '']
        return [int(value)]

    def _validate_id_list(self, value, queryset, label):
        unique_ids = []
        seen = set()
        for item_id in value:
            if item_id in seen:
                continue
            seen.add(item_id)
            unique_ids.append(item_id)
        valid_ids = set(queryset.filter(id__in=unique_ids).values_list('id', flat=True))
        invalid_ids = [item_id for item_id in unique_ids if item_id not in valid_ids]
        if invalid_ids:
            raise serializers.ValidationError(f'存在しない{label}が含まれています: {invalid_ids}')
        return unique_ids

    def _validate_new_attachments(self, files):
        for file_obj in files:
            _, ext = os.path.splitext(file_obj.name or '')
            if ext.lower() not in ALLOWED_ATTACHMENT_EXTENSIONS:
                raise serializers.ValidationError({
                    'attachments': f'添付できるのは PDF / 画像 / Excel のみです: {file_obj.name}'
                })


class MorningMeetingParticipantUpdateSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False, min_value=1)
    user = serializers.IntegerField(required=False, min_value=1)
    attendance_status = serializers.ChoiceField(choices=MorningMeetingParticipant.ATTENDANCE_STATUS_CHOICES)
    remark = serializers.CharField(required=False, allow_blank=True, max_length=255)


class MorningMeetingExecutionSerializer(serializers.Serializer):
    execution_note = serializers.CharField(required=False, allow_blank=True)
    participants = MorningMeetingParticipantUpdateSerializer(many=True, required=False)


class MorningMeetingDuplicateSerializer(serializers.Serializer):
    meeting_date = serializers.DateField(required=False)
    title = serializers.CharField(required=False, allow_blank=True, max_length=200)
    is_template = serializers.BooleanField(required=False)

    def duplicate(self, source_meeting, user=None):
        meeting_date = self.validated_data.get('meeting_date') or source_meeting.meeting_date
        title = (self.validated_data.get('title') or '').strip() or source_meeting.title
        is_template = self.validated_data.get('is_template', False)
        duplicated = MorningMeeting.objects.create(
            meeting_date=meeting_date,
            title=title,
            is_template=is_template,
            facilitator=source_meeting.facilitator,
            agenda=source_meeting.agenda,
            notices=source_meeting.notices,
            cautions=source_meeting.cautions,
            execution_note='',
            status=MorningMeeting.STATUS_DRAFT,
            created_by=user,
            updated_by=user,
        )
        duplicated.target_departments.set(source_meeting.target_departments.all())
        duplicated.target_lines.set(source_meeting.target_lines.all())

        for index, participant in enumerate(source_meeting.participants.all()):
            MorningMeetingParticipant.objects.create(
                meeting=duplicated,
                user=participant.user,
                attendance_status=MorningMeetingParticipant.STATUS_PENDING,
                remark='',
                display_order=index,
            )

        for index, attachment in enumerate(source_meeting.attachments.all(), start=1):
            if not attachment.file:
                continue
            src_name = attachment.file.name
            if not src_name or not default_storage.exists(src_name):
                continue
            with default_storage.open(src_name, 'rb') as src_file:
                content = ContentFile(src_file.read())
                _, ext = os.path.splitext(attachment.original_name or src_name)
                file_name = f'copy_{index}{ext.lower()}'
                cloned = MorningMeetingAttachment(
                    meeting=duplicated,
                    original_name=attachment.original_name,
                    content_type=attachment.content_type,
                    file_size=attachment.file_size,
                    attachment_type=attachment.attachment_type,
                    display_order=attachment.display_order,
                )
                cloned.file.save(file_name, content, save=False)
                cloned.save()

        return duplicated
