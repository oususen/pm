from collections import defaultdict
from django.contrib.auth.models import User
from django.db import models as db_models
from rest_framework import serializers

from .models import (
    Department,
    UnitLineMapping,
    UserProfile,
    UserPermission,
    DepartmentPermission,
    PositionPermission,
    DepartmentPositionPermission,
    UserSmtpConfig,
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
            # 係長: role='chief' かつ group=対象部署
            profiles = UserProfile.objects.filter(
                role='chief', group=obj
            ).select_related('user')
        elif level == 'team':
            # 班長: role='supervisor' かつ (team=対象班 または supervisor_teams に含まれる)
            profiles = UserProfile.objects.filter(
                role='supervisor'
            ).filter(
                db_models.Q(team=obj) | db_models.Q(supervisor_teams=obj)
            ).distinct().select_related('user')
        elif level == 'unit':
            # リーダー: role='leader' かつ (unit=対象グループ または leader_units に含まれる)
            profiles = UserProfile.objects.filter(
                role='leader'
            ).filter(
                db_models.Q(unit=obj) | db_models.Q(leader_units=obj)
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

    def get_effective_permissions(self, instance):
        permissions = defaultdict(lambda: {'can_view': False, 'can_edit': False})

        user_perms = list(instance.permissions.all())

        # Check if user is a manager (事業部長) - they get position permissions first
        is_manager = False
        try:
            if instance.profile and instance.profile.role == 'manager':
                is_manager = True
        except:
            pass

        if is_manager:
            # For managers: Position permissions first, then department-specific permissions
            try:
                if instance.profile and instance.profile.role:
                    pos_perms = PositionPermission.objects.filter(position_name=instance.profile.role)
                    for perm in pos_perms:
                        permissions[perm.resource]['can_view'] = perm.can_view
                        permissions[perm.resource]['can_edit'] = perm.can_edit
            except:
                pass

            # Department permissions (can override position permissions if more restrictive)
            try:
                if instance.profile and instance.profile.department:
                    dept_perms = DepartmentPermission.objects.filter(department=instance.profile.department)
                    for perm in dept_perms:
                        permissions[perm.resource]['can_view'] = permissions[perm.resource]['can_view'] or perm.can_view
                        permissions[perm.resource]['can_edit'] = permissions[perm.resource]['can_edit'] or perm.can_edit
            except:
                pass
        else:
            # For regular users: Department permissions first, then position permissions
            try:
                if instance.profile and instance.profile.department:
                    dept_perms = DepartmentPermission.objects.filter(department=instance.profile.department)
                    for perm in dept_perms:
                        permissions[perm.resource]['can_view'] = perm.can_view
                        permissions[perm.resource]['can_edit'] = perm.can_edit
            except:
                pass

            # Position permissions
            try:
                if instance.profile and instance.profile.role:
                    pos_perms = PositionPermission.objects.filter(position_name=instance.profile.role)
                    for perm in pos_perms:
                        permissions[perm.resource]['can_view'] = permissions[perm.resource]['can_view'] or perm.can_view
                        permissions[perm.resource]['can_edit'] = permissions[perm.resource]['can_edit'] or perm.can_edit
            except:
                pass

        # DepartmentPosition permissions (highest priority)
        try:
            if instance.profile and instance.profile.department and instance.profile.role:
                dept_pos_perms = DepartmentPositionPermission.objects.filter(
                    department=instance.profile.department,
                    position_name=instance.profile.role
                )
                for perm in dept_pos_perms:
                    permissions[perm.resource]['can_view'] = perm.can_view
                    permissions[perm.resource]['can_edit'] = perm.can_edit
        except:
            pass

        # User permissions override templates
        for perm in user_perms:
            if not (perm.can_view or perm.can_edit):
                continue
            permissions[perm.resource]['can_view'] = perm.can_view
            permissions[perm.resource]['can_edit'] = perm.can_edit

        return [
            {'resource': resource, 'can_view': vals['can_view'], 'can_edit': vals['can_edit']}
            for resource, vals in permissions.items()
        ]


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
