from collections import defaultdict
from django.contrib.auth.models import User
from rest_framework import serializers

from .models import (
    Department,
    UserProfile,
    UserPermission,
    DepartmentPermission,
    PositionPermission,
    DepartmentPositionPermission,
    UserSmtpConfig,
)


class DepartmentSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.name', read_only=True)

    class Meta:
        model = Department
        fields = ['id', 'name', 'level', 'parent', 'parent_name', 'display_id']


class UserProfileSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    division_name = serializers.CharField(source='division.name', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)
    unit_name = serializers.CharField(source='unit.name', read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'employee_code',
            'position',
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
            'unit',
            'unit_name',
            'joined_on',
        ]
        extra_kwargs = {
            'employee_code': {'validators': []},  # Disable default unique validator
        }


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

    def create(self, validated_data):
        profile_data = validated_data.pop('profile', None)
        permissions_data = validated_data.pop('permissions', None)
        password = validated_data.pop('password', None)

        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()

        if profile_data is not None:
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

            UserProfile.objects.update_or_create(user=user, defaults=profile_data)

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
                if instance.profile and instance.profile.position:
                    pos_perms = PositionPermission.objects.filter(position_name=instance.profile.position)
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
                if instance.profile and instance.profile.position:
                    pos_perms = PositionPermission.objects.filter(position_name=instance.profile.position)
                    for perm in pos_perms:
                        permissions[perm.resource]['can_view'] = permissions[perm.resource]['can_view'] or perm.can_view
                        permissions[perm.resource]['can_edit'] = permissions[perm.resource]['can_edit'] or perm.can_edit
            except:
                pass

        # DepartmentPosition permissions (highest priority)
        try:
            if instance.profile and instance.profile.department and instance.profile.position:
                dept_pos_perms = DepartmentPositionPermission.objects.filter(
                    department=instance.profile.department,
                    position_name=instance.profile.position
                )
                for perm in dept_pos_perms:
                    permissions[perm.resource]['can_view'] = perm.can_view
                    permissions[perm.resource]['can_edit'] = perm.can_edit
        except:
            pass

        # User permissions override templates
        for perm in user_perms:
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
