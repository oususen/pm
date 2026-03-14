from django.contrib import admin
from .models import OvertimeApplication, OvertimeApprovalLog


class OvertimeApprovalLogInline(admin.TabularInline):
    model = OvertimeApprovalLog
    extra = 0
    readonly_fields = ['created_at', 'acted_at']


@admin.register(OvertimeApplication)
class OvertimeApplicationAdmin(admin.ModelAdmin):
    list_display = ['work_date', 'applicant', 'application_type', 'start_time', 'end_time',
                    'hours', 'midnight_hours', 'status', 'submitted_at']
    list_filter = ['status', 'application_type', 'work_date']
    search_fields = ['applicant__username', 'applicant__last_name', 'reason']
    inlines = [OvertimeApprovalLogInline]
    readonly_fields = ['hours', 'midnight_hours', 'created_at', 'updated_at']


@admin.register(OvertimeApprovalLog)
class OvertimeApprovalLogAdmin(admin.ModelAdmin):
    list_display = ['application', 'approver', 'role', 'status', 'acted_at']
    list_filter = ['role', 'status']
