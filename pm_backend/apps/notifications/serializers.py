from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Notification, NotificationRead, CallSession, CallSignal
from accounts.models import Department, UserProfile

User = get_user_model()

def _safe_get_profile(user):
    try:
        return user.profile
    except UserProfile.DoesNotExist:
        return None


class NotificationSerializer(serializers.ModelSerializer):
    target_department_names = serializers.SerializerMethodField()
    target_user_names = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()
    unread_users = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id',
            'title',
            'category',
            'domain',
            'target_departments',
            'target_department_names',
            'target_positions',
            'target_users',
            'target_user_names',
            'valid_from',
            'valid_to',
            'display_order',
            'description',
            'operator_name',
            'created_at',
            'updated_at',
            'is_read',
            'unread_users',
        ]

    def get_target_department_names(self, obj):
        return [dept.name for dept in obj.target_departments.all()]

    def get_target_user_names(self, obj):
        names = []
        for user in obj.target_users.all():
            full_name = f"{user.last_name or ''}{user.first_name or ''}".strip()
            names.append(full_name or user.username)
        return names

    def get_is_read(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return NotificationRead.objects.filter(
            notification=obj,
            user=request.user
        ).exists()

    def get_unread_users(self, obj):
        """対象者のうち未閲覧のユーザー名リストを返す"""
        target_departments = list(obj.target_departments.all())
        target_positions = obj.target_positions or []
        direct_target_users = list(obj.target_users.all())

        # 対象ユーザーを取得
        target_users = self._get_target_users(target_departments, target_positions, direct_target_users)

        # 既読ユーザーIDを取得
        read_user_ids = set(
            NotificationRead.objects.filter(notification=obj)
            .values_list('user_id', flat=True)
        )

        # 未閲覧ユーザー名リストを作成
        unread_names = []
        for user in target_users:
            if user.id not in read_user_ids:
                full_name = f"{user.last_name or ''}{user.first_name or ''}".strip()
                name = full_name or user.username
                unread_names.append(name)

        return unread_names

    def _get_target_users(self, target_departments, target_positions, direct_target_users=None):
        """対象部署・役職・個別指定に該当するユーザーを取得"""
        direct_target_users = direct_target_users or []

        if not target_departments and not target_positions and not direct_target_users:
            # 対象指定なし = 全ユーザーが対象
            return list(User.objects.filter(is_active=True))

        def get_user_levels(profile):
            division_id = getattr(profile, 'division_id', None)
            group_id = getattr(profile, 'group_id', None)
            team_id = getattr(profile, 'team_id', None)
            if division_id or group_id or team_id:
                return division_id, group_id, team_id
            department = getattr(profile, 'department', None)
            if not department:
                return division_id, group_id, team_id
            if department.level == 'division':
                return department.id, group_id, team_id
            if department.level == 'group':
                return division_id, department.id, team_id
            if department.level == 'team':
                return division_id, group_id, department.id
            return division_id, group_id, team_id

        # 部署をレベル別に分類
        team_ids = []
        group_ids = []
        division_ids = []
        for dept in target_departments:
            if dept.level == 'team':
                team_ids.append(dept.id)
            elif dept.level == 'group':
                group_ids.append(dept.id)
            elif dept.level == 'division':
                division_ids.append(dept.id)

        # ユーザーをフィルタ
        if direct_target_users:
            users = [user for user in direct_target_users if user.is_active]
        else:
            users = User.objects.filter(is_active=True).select_related('profile')

        result = []
        for user in users:
            profile = _safe_get_profile(user)
            if not profile:
                continue

            # 部署チェック
            if target_departments:
                dept_match = False
                division_id, group_id, team_id = get_user_levels(profile)
                if team_ids:
                    # 班指定がある場合は班でマッチ
                    if team_id and team_id in team_ids:
                        dept_match = True
                elif group_ids:
                    # 係指定がある場合は係でマッチ
                    if group_id and group_id in group_ids:
                        dept_match = True
                elif division_ids:
                    # 事業部指定がある場合は事業部でマッチ
                    if division_id and division_id in division_ids:
                        dept_match = True

                if not dept_match:
                    continue

            # 役職チェック
            if target_positions:
                user_position = profile.role or ''
                if user_position not in target_positions:
                    continue

            result.append(user)

        return result


def _display_name(user):
    full_name = f"{user.last_name or ''}{user.first_name or ''}".strip()
    return full_name or user.username


class CallSignalSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    target_user_name = serializers.SerializerMethodField()

    class Meta:
        model = CallSignal
        fields = [
            'id',
            'session',
            'sender',
            'sender_name',
            'target_user',
            'target_user_name',
            'signal_type',
            'payload',
            'created_at',
        ]
        read_only_fields = ['id', 'session', 'sender', 'sender_name', 'target_user_name', 'created_at']

    def get_sender_name(self, obj):
        return _display_name(obj.sender)

    def get_target_user_name(self, obj):
        return _display_name(obj.target_user)


class CallSessionSerializer(serializers.ModelSerializer):
    caller_name = serializers.SerializerMethodField()
    callee_name = serializers.SerializerMethodField()

    class Meta:
        model = CallSession
        fields = [
            'id',
            'caller',
            'caller_name',
            'callee',
            'callee_name',
            'call_type',
            'status',
            'initiated_at',
            'accepted_at',
            'ended_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_caller_name(self, obj):
        return _display_name(obj.caller)

    def get_callee_name(self, obj):
        return _display_name(obj.callee)
