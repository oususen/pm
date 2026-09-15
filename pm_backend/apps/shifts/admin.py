from django.contrib import admin
from .models import ShiftLine, ShiftWorker, ShiftLineProcess, ShiftAssignment


@admin.register(ShiftLine)
class ShiftLineAdmin(admin.ModelAdmin):
    list_display = ['name', 'sort_order']


@admin.register(ShiftWorker)
class ShiftWorkerAdmin(admin.ModelAdmin):
    list_display = ['name', 'shift_line', 'shift_type', 'work_start', 'work_end', 'sort_order']
    list_filter = ['shift_line', 'shift_type']


@admin.register(ShiftLineProcess)
class ShiftLineProcessAdmin(admin.ModelAdmin):
    list_display = ['shift_line', 'process', 'color', 'required_hours', 'sort_order']
    list_filter = ['shift_line']


@admin.register(ShiftAssignment)
class ShiftAssignmentAdmin(admin.ModelAdmin):
    list_display = ['date', 'shift_line', 'worker', 'process', 'start_time', 'work_hours', 'units']
    list_filter = ['shift_line', 'date']
    date_hierarchy = 'date'
