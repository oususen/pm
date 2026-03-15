from rest_framework import serializers
from .models import OvertimeApplication, OvertimeApprovalLog


class OvertimeApprovalLogSerializer(serializers.ModelSerializer):
    approver_name = serializers.SerializerMethodField()
    role_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = OvertimeApprovalLog
        fields = [
            'id', 'approver', 'approver_name', 'role', 'role_display',
            'status', 'status_display', 'comment', 'acted_at', 'created_at',
        ]

    def get_approver_name(self, obj):
        if not obj.approver:
            return None
        u = obj.approver
        name = f"{u.last_name} {u.first_name}".strip()
        return name or u.username

    def get_role_display(self, obj):
        return obj.get_role_display()

    def get_status_display(self, obj):
        return obj.get_status_display()


class OvertimeApplicationSerializer(serializers.ModelSerializer):
    applicant_name = serializers.SerializerMethodField()
    team_name = serializers.SerializerMethodField()
    group_name = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    type_display = serializers.SerializerMethodField()
    signature = serializers.SerializerMethodField()
    approval_logs = OvertimeApprovalLogSerializer(many=True, read_only=True)
    can_edit = serializers.SerializerMethodField()
    can_approve = serializers.SerializerMethodField()
    pending_role = serializers.SerializerMethodField()

    class Meta:
        model = OvertimeApplication
        fields = [
            'id', 'applicant', 'applicant_name',
            'work_date', 'application_type', 'type_display',
            'work_start_time', 'scheduled_end_time',
            'start_time', 'end_time', 'hours', 'midnight_hours',
            'reason', 'team', 'team_name', 'group_name',
            'status', 'status_display', 'rejection_reason', 'signature',
            'submitted_at', 'created_at', 'updated_at',
            'approval_logs', 'can_edit', 'can_approve', 'pending_role',
        ]
        read_only_fields = [
            'applicant', 'hours', 'midnight_hours', 'team',
            'status', 'rejection_reason', 'submitted_at', 'created_at', 'updated_at',
        ]
        extra_kwargs = {
            'signature': {'required': False},
            'work_start_time': {'format': '%H:%M'},
            'scheduled_end_time': {'format': '%H:%M'},
            'start_time': {'format': '%H:%M'},
            'end_time': {'format': '%H:%M'},
        }

    def get_applicant_name(self, obj):
        u = obj.applicant
        name = f"{u.last_name} {u.first_name}".strip()
        return name or u.username

    def get_team_name(self, obj):
        return obj.team.name if obj.team else None

    def get_group_name(self, obj):
        try:
            return obj.applicant.profile.unit.name if obj.applicant.profile.unit else None
        except Exception:
            return None

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_type_display(self, obj):
        return obj.get_application_type_display()

    def get_signature(self, obj):
        if not obj.signature:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.signature.url)
        return obj.signature.url

    def get_can_edit(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.applicant_id == request.user.id and obj.status in ('draft', 'submitted', 'rejected')

    def get_can_approve(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        user = request.user
        pending_logs = obj.approval_logs.filter(status='pending')
        if not pending_logs.exists():
            return False
        try:
            role = user.profile.role
        except Exception:
            return False
        if role not in ('supervisor', 'chief', 'manager'):
            return False
        return pending_logs.filter(approver=user).exists()

    def get_pending_role(self, obj):
        """現在どのロールが承認待ちか"""
        log = obj.approval_logs.filter(status='pending').first()
        if log:
            return log.role
        return None

    def validate_work_start_time(self, value):
        if not value:
            raise serializers.ValidationError('勤務開始時間は必須です。')
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user
        validated_data['applicant'] = user
        try:
            validated_data['team'] = user.profile.team
        except Exception:
            pass
        return super().create(validated_data)
