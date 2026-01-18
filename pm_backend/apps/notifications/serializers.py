from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Notification, NotificationRead
from accounts.models import Department, UserProfile

User = get_user_model()


class NotificationSerializer(serializers.ModelSerializer):
    target_department_names = serializers.SerializerMethodField()
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

        # 対象ユーザーを取得
        target_users = self._get_target_users(target_departments, target_positions)

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

    def _get_target_users(self, target_departments, target_positions):
        """対象部署・役職に該当するユーザーを取得"""
        if not target_departments and not target_positions:
            # 対象指定なし = 全ユーザーが対象
            return list(User.objects.filter(is_active=True))

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
        users = User.objects.filter(is_active=True).select_related('profile')
        result = []

        for user in users:
            profile = getattr(user, 'profile', None)
            if not profile:
                continue

            # 部署チェック
            if target_departments:
                dept_match = False
                if team_ids:
                    # 班指定がある場合は班でマッチ
                    if profile.team_id and profile.team_id in team_ids:
                        dept_match = True
                elif group_ids:
                    # 係指定がある場合は係でマッチ
                    if profile.group_id and profile.group_id in group_ids:
                        dept_match = True
                elif division_ids:
                    # 事業部指定がある場合は事業部でマッチ
                    if profile.division_id and profile.division_id in division_ids:
                        dept_match = True

                if not dept_match:
                    continue

            # 役職チェック
            if target_positions:
                user_position = profile.position or ''
                if user_position not in target_positions:
                    continue

            result.append(user)

        return result
