from collections import defaultdict
import re
from django.contrib.auth.models import User
from rest_framework import serializers

from .role_utils import build_chief_role_q, build_leader_role_q, build_supervisor_role_q
from .permission_scope import (
    collect_effective_department_ids,
    collect_managed_department_ids,
)
from .models import (
    Department,
    UnitLineMapping,
    UserProfile,
    UserPermission,
    DepartmentPermission,
    PositionPermission,
    DepartmentPositionPermission,
    UserSmtpConfig,
    UserFavorite,
    ApprovalRouteConfig,
)


class DepartmentSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    head = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ['id', 'name', 'level', 'parent', 'parent_name', 'display_id', 'head']

    def get_head(self, obj):
        """各部署の長（部長/係長/班長/リーダー）を返す"""
        level = obj.level
        if level == 'division':
            # 事業部長: role='manager' かつ division=対象部署
            profiles = UserProfile.objects.filter(
                role='manager', division=obj
            ).select_related('user')
        elif level == 'group':
            profiles = UserProfile.objects.filter(
                build_chief_role_q(obj.id, prefix='')
            ).distinct().select_related('user')
        elif level == 'team':
            profiles = UserProfile.objects.filter(
                build_supervisor_role_q(obj.id, prefix='')
            ).distinct().select_related('user')
        elif level == 'unit':
            profiles = UserProfile.objects.filter(
                build_leader_role_q(obj.id, prefix='')
            ).distinct().select_related('user')
        else:
            return []

        result = []
        for p in profiles:
            last = p.user.last_name or ''
            first = p.user.first_name or ''
            name = (last + ' ' + first).strip() or p.user.username
            result.append(name)
        return result


class UserProfileSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    division_name = serializers.CharField(source='division.name', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)
    supervisor_teams = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.filter(level='team'),
        many=True,
        required=False,
    )
    supervisor_team_names = serializers.SerializerMethodField()
    leader_units = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.filter(level='unit'),
        many=True,
        required=False,
    )
    leader_unit_names = serializers.SerializerMethodField()
    unit_name = serializers.CharField(source='unit.name', read_only=True)
    unit_lines = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            'employee_code',
            'role',
            'employment_type',
            'department',
            'department_name',
            'division',
            'division_name',
            'group',
            'group_name',
            'team',
            'team_name',
            'supervisor_teams',
            'supervisor_team_names',
            'leader_units',
            'leader_unit_names',
            'unit',
            'unit_name',
            'unit_lines',
            'joined_on',
        ]
        extra_kwargs = {
            'employee_code': {'validators': []},  # Disable default unique validator
        }

    def get_supervisor_team_names(self, obj):
        return [team.name for team in obj.supervisor_teams.all()]

    def get_leader_unit_names(self, obj):
        return [unit.name for unit in obj.leader_units.all()]

    def get_unit_lines(self, obj):
        if not obj.unit_id:
            return []
        mappings = (
            UnitLineMapping.objects.select_related('line')
            .filter(unit_id=obj.unit_id)
            .order_by('-is_default', 'sort_order', 'id')
        )
        return [
            {
                'id': mapping.id,
                'line_id': mapping.line_id,
                'line_code': mapping.line.line_code if mapping.line_id else '',
                'line_name': mapping.line.line_name if mapping.line_id else '',
                'sort_order': mapping.sort_order,
                'is_default': mapping.is_default,
            }
            for mapping in mappings
        ]


class UnitLineMappingSerializer(serializers.ModelSerializer):
    unit_name = serializers.CharField(source='unit.name', read_only=True)
    line_code = serializers.CharField(source='line.line_code', read_only=True)
    line_name = serializers.CharField(source='line.line_name', read_only=True)

    class Meta:
        model = UnitLineMapping
        fields = [
            'id',
            'unit',
            'unit_name',
            'line',
            'line_code',
            'line_name',
            'sort_order',
            'is_default',
            'created_at',
            'updated_at',
        ]


class UserFavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserFavorite
        fields = [
            'id',
            'screen_key',
            'name',
            'payload',
            'created_at',
            'updated_at',
        ]


class UserPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPermission
        fields = ['resource', 'can_view', 'can_edit']


class DepartmentPermissionSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = DepartmentPermission
        fields = ['id', 'department', 'department_name', 'resource', 'can_view', 'can_edit']


class PositionPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PositionPermission
        fields = ['id', 'position_name', 'resource', 'can_view', 'can_edit']


class DepartmentPositionPermissionSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = DepartmentPositionPermission
        fields = [
            'id',
            'department',
            'department_name',
            'position_name',
            'resource',
            'can_view',
            'can_edit',
        ]


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False, allow_null=True)
    permissions = UserPermissionSerializer(many=True, required=False)
    effective_permissions = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'is_active',
            'is_staff',
            'is_superuser',
            'password',
            'profile',
            'permissions',
            'effective_permissions',
        ]
        extra_kwargs = {
            'username': {'validators': []},  # Handle uniqueness in validate_username
        }

    def validate_username(self, value):
        # Check uniqueness excluding current instance
        qs = User.objects.filter(username=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('このユーザー名は既に使用されています。')
        return value

    def _sync_department_and_division(self, profile_data):
        if profile_data is None:
            return profile_data

        if 'division' in profile_data:
            profile_data['department'] = profile_data.get('division')
        elif 'department' in profile_data:
            profile_data['division'] = profile_data.get('department')
        return profile_data

    def create(self, validated_data):
        profile_data = validated_data.pop('profile', None)
        permissions_data = validated_data.pop('permissions', None)
        password = validated_data.pop('password', None)

        employee_code = None
        if profile_data is not None:
            employee_code = profile_data.get('employee_code')
            if employee_code == '':
                employee_code = None

        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            # 新規作成時の初期パスワードは社員コード（未設定時はユーザー名）を使用
            initial_password = employee_code or validated_data.get('username')
            if initial_password:
                user.set_password(initial_password)
            else:
                user.set_unusable_password()
        user.save()

        if profile_data is not None:
            supervisor_teams = profile_data.pop('supervisor_teams', None)
            leader_units = profile_data.pop('leader_units', None)
            profile_data = self._sync_department_and_division(profile_data)
            if profile_data.get('employee_code') == '':
                profile_data['employee_code'] = None

            # Check employee_code uniqueness before creating
            employee_code = profile_data.get('employee_code')
            if employee_code and UserProfile.objects.filter(employee_code=employee_code).exists():
                user.delete()  # Rollback user creation
                raise serializers.ValidationError({
                    'profile': {
                        'employee_code': 'この社員コードは既に使用されています。'
                    }
                })

            profile, _ = UserProfile.objects.update_or_create(user=user, defaults=profile_data)
            if supervisor_teams is not None:
                profile.supervisor_teams.set(supervisor_teams)
            if leader_units is not None:
                profile.leader_units.set(leader_units)

        if permissions_data is not None:
            self._replace_permissions(user, permissions_data)

        return user

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', None)
        permissions_data = validated_data.pop('permissions', None)
        password = validated_data.pop('password', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()

        if profile_data is not None:
            supervisor_teams = profile_data.pop('supervisor_teams', None)
            leader_units = profile_data.pop('leader_units', None)
            profile_data = self._sync_department_and_division(profile_data)
            if profile_data.get('employee_code') == '':
                profile_data['employee_code'] = None

            # Check employee_code uniqueness before saving
            employee_code = profile_data.get('employee_code')
            if employee_code:
                existing = UserProfile.objects.filter(employee_code=employee_code).exclude(user=instance).first()
                if existing:
                    raise serializers.ValidationError({
                        'profile': {
                            'employee_code': 'この社員コードは既に使用されています。'
                        }
                    })

            profile, _ = UserProfile.objects.get_or_create(user=instance)
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
            if supervisor_teams is not None:
                profile.supervisor_teams.set(supervisor_teams)
            if leader_units is not None:
                profile.leader_units.set(leader_units)

        if permissions_data is not None:
            self._replace_permissions(instance, permissions_data)

        return instance

    def _replace_permissions(self, user, permissions_data):
        UserPermission.objects.filter(user=user).delete()
        if not permissions_data:
            return
        seen = set()
        records = []
        for perm in permissions_data:
            resource = perm.get('resource')
            if not resource or resource in seen:
                continue
            seen.add(resource)
            can_edit = bool(perm.get('can_edit'))
            can_view = bool(perm.get('can_view')) or can_edit
            records.append(
                UserPermission(
                    user=user,
                    resource=resource,
                    can_view=can_view,
                    can_edit=can_edit,
                )
            )
        if records:
            UserPermission.objects.bulk_create(records)

    @staticmethod
    def _normalize_permission_flags(can_view, can_edit):
        can_edit = bool(can_edit)
        can_view = bool(can_view) or can_edit
        return can_view, can_edit

    @staticmethod
    def _get_position_label(position_name):
        if not position_name:
            return ''
        return dict(UserProfile.ROLE_CHOICES).get(position_name, position_name)

    def _append_permission_source(self, bucket, source_type, source_label, can_view, can_edit):
        can_view, can_edit = self._normalize_permission_flags(can_view, can_edit)
        if not (can_view or can_edit):
            return
        key = (source_type, source_label, can_view, can_edit)
        if key in bucket['_source_keys']:
            return
        bucket['_source_keys'].add(key)
        bucket['sources'].append({
            'source_type': source_type,
            'source_label': source_label,
            'can_view': can_view,
            'can_edit': can_edit,
        })

    def _build_effective_permission_details(self, instance):
        cache = getattr(self, '_effective_permission_details_cache', None)
        if cache is None:
            cache = {}
            self._effective_permission_details_cache = cache
        if instance.pk in cache:
            return cache[instance.pk]

        permissions = defaultdict(lambda: {
            'template_can_view': False,
            'template_can_edit': False,
            'user_can_view': False,
            'user_can_edit': False,
            'has_user_permission': False,
            'sources': [],
            '_source_keys': set(),
        })

        try:
            profile = instance.profile
        except UserProfile.DoesNotExist:
            profile = None
        position_name = getattr(profile, 'role', '') if profile else ''
        position_label = self._get_position_label(position_name)
        dept_ids = collect_effective_department_ids(profile) if profile else []
        managed_dept_ids = collect_managed_department_ids(profile) if profile else set()

        if dept_ids:
            dept_perms = (
                DepartmentPermission.objects
                .select_related('department')
                .filter(department_id__in=dept_ids)
            )
            for perm in dept_perms:
                can_view, can_edit = self._normalize_permission_flags(perm.can_view, perm.can_edit)
                bucket = permissions[perm.resource]
                bucket['template_can_view'] = bucket['template_can_view'] or can_view
                bucket['template_can_edit'] = bucket['template_can_edit'] or can_edit
                self._append_permission_source(
                    bucket,
                    'department',
                    f'部署: {perm.department.name}',
                    can_view,
                    can_edit,
                )

        if position_name:
            pos_perms = PositionPermission.objects.filter(position_name=position_name)
            for perm in pos_perms:
                can_view, can_edit = self._normalize_permission_flags(perm.can_view, perm.can_edit)
                bucket = permissions[perm.resource]
                bucket['template_can_view'] = bucket['template_can_view'] or can_view
                bucket['template_can_edit'] = bucket['template_can_edit'] or can_edit
                self._append_permission_source(
                    bucket,
                    'position',
                    f'役職: {position_label}',
                    can_view,
                    can_edit,
                )

        if dept_ids and position_name:
            dept_pos_perms = (
                DepartmentPositionPermission.objects
                .select_related('department')
                .filter(department_id__in=dept_ids, position_name=position_name)
            )
            for perm in dept_pos_perms:
                can_view, can_edit = self._normalize_permission_flags(perm.can_view, perm.can_edit)
                bucket = permissions[perm.resource]
                bucket['template_can_view'] = bucket['template_can_view'] or can_view
                bucket['template_can_edit'] = bucket['template_can_edit'] or can_edit
                self._append_permission_source(
                    bucket,
                    'department_position',
                    f'部署・役職: {perm.department.name} × {position_label}',
                    can_view,
                    can_edit,
                )

        if managed_dept_ids:
            staff_perms = (
                DepartmentPositionPermission.objects
                .select_related('department')
                .filter(department_id__in=managed_dept_ids, position_name='staff')
            )
            for perm in staff_perms:
                can_view, can_edit = self._normalize_permission_flags(perm.can_view, perm.can_edit)
                bucket = permissions[perm.resource]
                bucket['template_can_view'] = bucket['template_can_view'] or can_view
                bucket['template_can_edit'] = bucket['template_can_edit'] or can_edit
                self._append_permission_source(
                    bucket,
                    'department_position',
                    f'部署・役職: {perm.department.name} × 一般',
                    can_view,
                    can_edit,
                )

        user_perms = list(instance.permissions.all())
        for perm in user_perms:
            can_view, can_edit = self._normalize_permission_flags(perm.can_view, perm.can_edit)
            if not (can_view or can_edit):
                continue
            bucket = permissions[perm.resource]
            bucket['has_user_permission'] = True
            bucket['user_can_view'] = can_view
            bucket['user_can_edit'] = can_edit
            self._append_permission_source(
                bucket,
                'user',
                '個別権限',
                can_view,
                can_edit,
            )

        resource_order = {
            resource: index
            for index, (resource, _label) in enumerate(UserPermission.RESOURCE_CHOICES)
        }
        results = []
        for resource, values in permissions.items():
            if values['has_user_permission']:
                can_view = values['user_can_view']
                can_edit = values['user_can_edit']
            else:
                can_view = values['template_can_view']
                can_edit = values['template_can_edit']
            can_view, can_edit = self._normalize_permission_flags(can_view, can_edit)
            if not (can_view or can_edit):
                continue
            results.append({
                'resource': resource,
                'can_view': can_view,
                'can_edit': can_edit,
                'template_can_view': values['template_can_view'],
                'template_can_edit': values['template_can_edit'],
                'user_can_view': values['user_can_view'],
                'user_can_edit': values['user_can_edit'],
                'has_user_permission': values['has_user_permission'],
                'sources': values['sources'],
            })

        results.sort(key=lambda item: (resource_order.get(item['resource'], 9999), item['resource']))
        cache[instance.pk] = results
        return results

    def get_effective_permissions(self, instance):
        return [
            {
                'resource': detail['resource'],
                'can_view': detail['can_view'],
                'can_edit': detail['can_edit'],
            }
            for detail in self._build_effective_permission_details(instance)
        ]


class UserDetailSerializer(UserSerializer):
    effective_permission_details = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + [
            'effective_permission_details',
        ]

    def get_effective_permission_details(self, instance):
        return self._build_effective_permission_details(instance)


class UserSmtpConfigSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = UserSmtpConfig
        fields = [
            'id',
            'user',
            'username',
            'smtp_host',
            'smtp_port',
            'smtp_user',
            'smtp_password',
            'is_active',
            'is_admin',
        ]
        extra_kwargs = {
            'smtp_password': {'write_only': True}
        }


class ApprovalRouteConfigSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    creator_role_label = serializers.CharField(source='get_creator_role_display', read_only=True)
    reviewer1_role_label = serializers.CharField(source='get_reviewer1_role_display', read_only=True)
    reviewer2_role_label = serializers.CharField(source='get_reviewer2_role_display', read_only=True)
    approver_role_label = serializers.CharField(source='get_approver_role_display', read_only=True)
    creator_allowed_user_names = serializers.SerializerMethodField()
    creator_proxy_user_names = serializers.SerializerMethodField()
    reviewer1_allowed_user_names = serializers.SerializerMethodField()
    reviewer1_proxy_user_names = serializers.SerializerMethodField()
    reviewer2_allowed_user_names = serializers.SerializerMethodField()
    reviewer2_proxy_user_names = serializers.SerializerMethodField()
    approver_allowed_user_names = serializers.SerializerMethodField()
    approver_proxy_user_names = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalRouteConfig
        fields = [
            'id',
            'item_key',
            'item_name',
            'creator_role',
            'creator_role_label',
            'creator_task_enabled',
            'creator_app_notification_enabled',
            'creator_email_notification_enabled',
            'creator_allowed_users',
            'creator_allowed_user_names',
            'creator_proxy_users',
            'creator_proxy_user_names',
            'reviewer1_role',
            'reviewer1_role_label',
            'reviewer1_task_enabled',
            'reviewer1_app_notification_enabled',
            'reviewer1_email_notification_enabled',
            'reviewer1_allowed_users',
            'reviewer1_allowed_user_names',
            'reviewer1_proxy_users',
            'reviewer1_proxy_user_names',
            'reviewer2_role',
            'reviewer2_role_label',
            'reviewer2_enabled',
            'reviewer2_task_enabled',
            'reviewer2_app_notification_enabled',
            'reviewer2_email_notification_enabled',
            'reviewer2_allowed_users',
            'reviewer2_allowed_user_names',
            'reviewer2_proxy_users',
            'reviewer2_proxy_user_names',
            'approver_role',
            'approver_role_label',
            'approver_task_enabled',
            'approver_app_notification_enabled',
            'approver_email_notification_enabled',
            'approver_allowed_users',
            'approver_allowed_user_names',
            'approver_proxy_users',
            'approver_proxy_user_names',
            'approved_result_app_notification_enabled',
            'approved_result_email_notification_enabled',
            'rejected_result_app_notification_enabled',
            'rejected_result_email_notification_enabled',
            'is_active',
            'note',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'item_key': {'validators': []},
        }

    def validate_item_key(self, value):
        item_key = (value or '').strip()
        if not item_key:
            raise serializers.ValidationError('管理コードは必須です。')
        if not re.fullmatch(r'[a-z0-9_]+', item_key):
            raise serializers.ValidationError('管理コードは半角英数字と _ のみ使用できます。')
        return item_key

    def _get_user_names(self, users):
        names = []
        for user in users.all():
            full_name = f'{user.last_name or ""} {user.first_name or ""}'.strip()
            names.append(full_name or user.username)
        return names

    def get_creator_allowed_user_names(self, obj):
        return self._get_user_names(obj.creator_allowed_users)

    def get_creator_proxy_user_names(self, obj):
        return self._get_user_names(obj.creator_proxy_users)

    def get_reviewer1_allowed_user_names(self, obj):
        return self._get_user_names(obj.reviewer1_allowed_users)

    def get_reviewer1_proxy_user_names(self, obj):
        return self._get_user_names(obj.reviewer1_proxy_users)

    def get_reviewer2_allowed_user_names(self, obj):
        return self._get_user_names(obj.reviewer2_allowed_users)

    def get_reviewer2_proxy_user_names(self, obj):
        return self._get_user_names(obj.reviewer2_proxy_users)

    def get_approver_allowed_user_names(self, obj):
        return self._get_user_names(obj.approver_allowed_users)

    def get_approver_proxy_user_names(self, obj):
        return self._get_user_names(obj.approver_proxy_users)
