from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import (
    Department,
    UserProfile,
    UserSmtpConfig,
    UserPermission,
    DepartmentPermission,
    PositionPermission,
    DepartmentPositionPermission,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'parent', 'display_id')
    list_filter = ('level',)
    search_fields = ('name',)
    ordering = ('display_id', 'id')


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name = 'プロファイル'
    verbose_name_plural = 'プロファイル'
    fk_name = 'user'
    fields = ('employee_code', 'department', 'division', 'group', 'team',
              'role', 'employment_type', 'joined_on')


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_department', 'is_staff', 'is_active')
    list_select_related = ('profile',)

    def get_department(self, obj):
        return obj.profile.department if hasattr(obj, 'profile') else '-'
    get_department.short_description = '部署'


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'employee_code', 'department', 'role', 'employment_type')
    list_filter = ('role', 'employment_type', 'department')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'employee_code')
    ordering = ('employee_code',)


@admin.register(UserSmtpConfig)
class UserSmtpConfigAdmin(admin.ModelAdmin):
    list_display = ('user', 'smtp_host', 'smtp_user', 'is_active', 'is_admin')
    list_filter = ('is_active', 'is_admin')
    search_fields = ('user__username', 'user__email', 'smtp_user')


@admin.register(UserPermission)
class UserPermissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'resource', 'can_view', 'can_edit')
    list_filter = ('resource', 'can_view', 'can_edit')
    search_fields = ('user__username', 'user__email')


@admin.register(DepartmentPermission)
class DepartmentPermissionAdmin(admin.ModelAdmin):
    list_display = ('department', 'resource', 'can_view', 'can_edit')
    list_filter = ('resource', 'can_view', 'can_edit')
    search_fields = ('department__name',)


@admin.register(PositionPermission)
class PositionPermissionAdmin(admin.ModelAdmin):
    list_display = ('position_name', 'resource', 'can_view', 'can_edit')
    list_filter = ('resource', 'can_view', 'can_edit')
    search_fields = ('position_name',)


@admin.register(DepartmentPositionPermission)
class DepartmentPositionPermissionAdmin(admin.ModelAdmin):
    list_display = ('department', 'position_name', 'resource', 'can_view', 'can_edit')
    list_filter = ('resource', 'can_view', 'can_edit', 'department')
    search_fields = ('department__name', 'position_name')
